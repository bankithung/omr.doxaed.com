"""
omr.scan.pipeline — End-to-end scan processing pipeline.

process_image(image, descriptor) -> dict
    Full pipeline: decode QR -> detect fiducials -> warp -> binary -> read.

process_scan_job(job)
    Load the job's image, run process_image, persist reads/status,
    then try to grade if all pages are in.

_persist_grading_result(omr_sheet, grading, done_jobs)
    Write StudentResult + QuestionResponses + ReviewItems; mark sheet complete.
    Extracted so that the regrade endpoint can reuse it without a new ScanEvent.

_maybe_grade(omr_sheet)
    Gather all done ScanJobs; if all pages present, aggregate reads,
    call grade_sheet, call _persist_grading_result.
"""

from __future__ import annotations

import cv2
import numpy as np
from decimal import Decimal

from omr.scan.align import decode_qr, detect_fiducials, warp_to_canonical
from omr.scan.read import to_binary, read_roll, read_answers, bubble_fill_ratio
from omr.scan.grade import grade_sheet


# ---------------------------------------------------------------------------
# Stage: process a single image (ndarray) through the full pipeline
# ---------------------------------------------------------------------------

def process_image(image: np.ndarray, descriptor: dict) -> dict:
    """
    Run the full scan pipeline on a single image ndarray.

    Parameters
    ----------
    image : np.ndarray
        uint8 grayscale or BGR scan image.
    descriptor : dict
        Canonical descriptor from omr.geometry.build_template().

    Returns
    -------
    dict with keys:
        sheet_code  : str | None
        page        : int  (0-based; None if no QR)
        total       : int  (total pages; None if no QR)
        reads       : dict {q_pos (int): {"marked": [labels], "flag": str|None}}
        fill_ratios : dict {q_pos (int): float}  per-question confidence proxy
        roll        : str | None
        flags       : list[str]
        canonical   : np.ndarray | None  warped canonical image
    """
    flags: list[str] = []

    # ---- Stage 1: QR decode ----
    qr_result = decode_qr(image)
    if qr_result is None:
        return {
            "sheet_code": None,
            "page": None,
            "total": None,
            "reads": {},
            "fill_ratios": {},
            "roll": None,
            "flags": ["no_qr"],
            "canonical": None,
        }

    sheet_code, page_1based, total = qr_result
    page = page_1based - 1  # convert to 0-based

    # ---- Stage 2: Fiducial detection ----
    src_pts = detect_fiducials(image, descriptor)
    if src_pts is None:
        return {
            "sheet_code": sheet_code,
            "page": page,
            "total": total,
            "reads": {},
            "fill_ratios": {},
            "roll": None,
            "flags": ["alignment"],
            "canonical": None,
        }

    # ---- Stage 3: Warp to canonical space ----
    canonical = warp_to_canonical(image, src_pts, descriptor)

    # ---- Stage 4: Binarise ----
    binary = to_binary(canonical)

    # ---- Stage 5: Read roll (page 0 only) ----
    roll: str | None = None
    if page == 0:
        roll, roll_flag = read_roll(binary, descriptor)
        if roll_flag:
            flags.append(roll_flag)

    # ---- Stage 6: Read answers ----
    reads = read_answers(binary, descriptor, page=page)

    # Collect per-question flags
    for q_pos, entry in reads.items():
        if entry.get("flag"):
            flags.append(entry["flag"])

    # ---- Stage 7: Derive per-question fill_ratio (confidence proxy) ----
    # Measure the actual pixel fill of the most-filled marked option.
    # Using bubble_fill_ratio on the warped canonical binary image gives an
    # accurate, scale-independent measurement: a solidly filled bubble reads
    # near 1.0 regardless of image scale or per-question flag.
    #
    # For blank questions (no marked options), the ratio is 0.0.
    #
    # Build a lookup: q_pos -> {label -> (cx, cy, r)} for bubbles on this page.
    _bubble_coords: dict[int, dict[str, tuple]] = {}
    for _entry in descriptor["answer_bubbles"]:
        if _entry["page"] != page:
            continue
        _q_pos = _entry["q_pos"]
        _bubble_coords[_q_pos] = {
            opt["label"]: (opt["cx"], opt["cy"], opt["r"])
            for opt in _entry["options"]
        }

    fill_ratios: dict[int, float] = {}
    for q_pos, entry in reads.items():
        marked = entry.get("marked", [])
        if not marked:
            fill_ratios[q_pos] = 0.0
        else:
            # Take the maximum fill ratio across all marked options.
            max_ratio = 0.0
            coords_for_q = _bubble_coords.get(q_pos, {})
            for label in marked:
                if label in coords_for_q:
                    cx, cy, r = coords_for_q[label]
                    ratio = bubble_fill_ratio(binary, cx, cy, r)
                    if ratio > max_ratio:
                        max_ratio = ratio
            fill_ratios[q_pos] = float(max_ratio)

    return {
        "sheet_code": sheet_code,
        "page": page,
        "total": total,
        "reads": reads,
        "fill_ratios": fill_ratios,
        "roll": roll,
        "flags": flags,
        "canonical": canonical,
    }


# ---------------------------------------------------------------------------
# Stage: process a ScanJob model instance
# ---------------------------------------------------------------------------

def process_scan_job(job) -> None:
    """
    Load the ScanJob's image, run process_image, update the job, then
    attempt grading if all pages for the sheet are complete.

    Parameters
    ----------
    job : omr.models.ScanJob
    """
    from omr.models import OmrSheet

    # Load image from the job's image_file
    image = _load_image(job)
    if image is None:
        job.status = job.STATUS_FAILED
        job.error_reason = "image_not_found"
        job.save(update_fields=["status", "error_reason"])
        return

    # We need the descriptor — find the OmrSheet first by a preliminary QR decode
    # to determine sheet_code, then look up the sheet in the batch's test.
    qr_result = decode_qr(image)
    if qr_result is None:
        job.status = job.STATUS_NEEDS_REVIEW
        job.error_reason = "no_qr"
        job.reads = {}
        job.save(update_fields=["status", "error_reason", "reads"])
        _create_review_item(job=job, omr_sheet=None, reason="no_qr")
        return

    sheet_code, page_1based, total = qr_result
    page = page_1based - 1

    # ---- Test-identity guard (Phase 1B) ----
    # The sheet_code format is "{test_id:06d}-{token}".  Parse the test_id from
    # the code and verify it matches the batch's test BEFORE resolving any sheet.
    # A mismatch means a sheet from a different test was uploaded into this batch —
    # flag it and stop (do NOT grade against the wrong key).
    parsed_test_id = _parse_test_id_from_sheet_code(sheet_code)
    if parsed_test_id is not None and parsed_test_id != job.batch.test_id:
        job.status = job.STATUS_NEEDS_REVIEW
        job.error_reason = "test_mismatch"
        job.reads = {}
        job.save(update_fields=["status", "error_reason", "reads"])
        _create_review_item(job=job, omr_sheet=None, reason="test_mismatch")
        return

    # Look up the OmrSheet — must belong to the same test as the batch
    try:
        omr_sheet = OmrSheet.objects.get(
            sheet_code=sheet_code,
            test=job.batch.test,
        )
    except OmrSheet.DoesNotExist:
        job.status = job.STATUS_FAILED
        job.error_reason = f"sheet_not_found:{sheet_code}"
        job.save(update_fields=["status", "error_reason"])
        return

    descriptor = omr_sheet.template_descriptor

    # Run full pipeline
    result = process_image(image, descriptor)

    # ---- Verify-only roll reconciliation (Phase 1B, Mode B / prebubbled only) ----
    # Identity still comes from the QR; this is tamper-evidence only.
    # A mismatch never changes which student is graded — it only raises a flag.
    flags = list(result.get("flags", []))
    if omr_sheet.roll_kind == OmrSheet.ROLL_KIND_PREBUBBLED and page == 0:
        roll_read = result.get("roll")
        # Only compare when the roll was read without the roll_unreadable flag
        if roll_read and "roll_unreadable" not in flags:
            student_roll = omr_sheet.student.roll_number if omr_sheet.student else ""
            roll_digits = descriptor.get("roll_grid", {}).get("cols", len(student_roll))
            normalized_read = _normalize_roll(roll_read, roll_digits)
            normalized_stored = _normalize_roll(student_roll, roll_digits)
            if normalized_read and normalized_stored and normalized_read != normalized_stored:
                flags.append("roll_mismatch")

    # Persist reads + status
    job.omr_sheet = omr_sheet
    job.page_no = page + 1  # store 1-based for consistency with existing field
    job.reads = {
        "answers": {str(k): v for k, v in result["reads"].items()},
        "fill_ratios": {str(k): v for k, v in result.get("fill_ratios", {}).items()},
        "roll": result.get("roll"),
        "flags": flags,
    }

    if flags:
        job.status = job.STATUS_NEEDS_REVIEW
        job.error_reason = ",".join(flags)
    else:
        job.status = job.STATUS_DONE

    # Confidence: fraction of unflagged questions
    n_questions = len(result["reads"])
    n_flagged = sum(1 for f in flags if f in ("double_mark", "faint"))
    if n_questions:
        job.confidence = max(0.0, (n_questions - n_flagged) / n_questions)
    else:
        job.confidence = 1.0

    update_fields = ["omr_sheet", "page_no", "reads", "status", "error_reason", "confidence"]

    # Save warped canonical image to job.warped_file
    canonical = result.get("canonical")
    if canonical is not None:
        try:
            from django.core.files.base import ContentFile
            ok, buf = cv2.imencode(".png", canonical)
            if ok:
                warped_bytes = buf.tobytes()
                fname = f"warped_{job.id}_p{page + 1}.png"
                job.warped_file.save(fname, ContentFile(warped_bytes), save=False)
                update_fields.append("warped_file")
        except Exception:
            # Never let warped image failure break the pipeline
            pass

    job.save(update_fields=update_fields)

    # Create ReviewItems for each flag
    for flag in flags:
        reason = _flag_to_reason(flag)
        if reason:
            _create_review_item(job=job, omr_sheet=omr_sheet, reason=reason)

    # Attempt grading if all pages are now done
    _maybe_grade(omr_sheet)


# ---------------------------------------------------------------------------
# Stage: aggregate + grade when all pages arrive
# ---------------------------------------------------------------------------

def _maybe_grade(omr_sheet) -> None:
    """
    Check whether all pages for omr_sheet have been successfully scanned.
    If so, aggregate reads, call grade_sheet, and persist the result.
    """
    from omr.models import ScanJob
    from results.models import ReviewItem

    page_count = omr_sheet.page_count
    expected_pages = set(range(page_count))  # 0-based

    # Include both STATUS_DONE and STATUS_NEEDS_REVIEW jobs — the latter have
    # valid reads but were flagged (e.g. double_mark, faint, roll_unreadable).
    # Jobs with STATUS_FAILED or STATUS_QUEUED have no useful reads.
    processable_jobs = list(
        ScanJob.objects.filter(
            omr_sheet=omr_sheet,
            status__in=[ScanJob.STATUS_DONE, ScanJob.STATUS_NEEDS_REVIEW],
        )
    )

    # Only count jobs that actually have reads (alignment failures have none)
    done_jobs = [
        j for j in processable_jobs
        if j.reads and "answers" in j.reads
    ]

    done_pages = set(j.page_no - 1 for j in done_jobs)  # back to 0-based

    if done_pages < expected_pages:
        # Some pages still missing — leave a missing_page review item
        missing = expected_pages - done_pages
        for pg in missing:
            # Only create once
            already = ReviewItem.objects.filter(
                omr_sheet=omr_sheet,
                reason=ReviewItem.REASON_MISSING_PAGE,
                resolved=False,
            ).exists()
            if not already:
                ReviewItem.objects.create(
                    omr_sheet=omr_sheet,
                    reason=ReviewItem.REASON_MISSING_PAGE,
                )
        return

    # All pages done — aggregate reads
    aggregated_reads: dict[int, list] = {}
    for job in done_jobs:
        answers = job.reads.get("answers", {})
        for q_pos_str, entry in answers.items():
            q_pos = int(q_pos_str)
            marked = entry.get("marked", [])
            if q_pos not in aggregated_reads:
                aggregated_reads[q_pos] = list(marked)
            else:
                # Merge (shouldn't happen across pages but be safe)
                aggregated_reads[q_pos].extend(
                    lbl for lbl in marked if lbl not in aggregated_reads[q_pos]
                )

    # Grade the sheet
    grading = grade_sheet(omr_sheet, aggregated_reads)

    # Persist result
    _persist_grading_result(omr_sheet, grading, done_jobs)


def _persist_grading_result(omr_sheet, grading: dict, done_jobs: list) -> None:
    """
    Write StudentResult + QuestionResponses + ReviewItems; mark sheet complete.

    Extracted from _maybe_grade so the regrade endpoint can reuse it without
    creating a new ScanEvent (no double-charge).

    Parameters
    ----------
    omr_sheet : omr.models.OmrSheet
    grading   : dict returned by grade_sheet()
    done_jobs : list of ScanJob instances that contributed reads
    """
    from results.models import StudentResult, QuestionResponse, ReviewItem

    # Build section_breakdown for persistence
    section_breakdown = {
        str(s["section_id"]): {
            "subtotal": float(s["subtotal"]),
            "correct": s["correct"],
            "wrong": s["wrong"],
            "blank": s["blank"],
            "q_count": s["q_count"],
            "max_subtotal": float(s["max_subtotal"]),
            "counts": s["counts"],
            "qualify_pct": s["qualify_pct"],
            "qualified": s["qualified"],
        }
        for s in grading.get("sections", [])
    }

    # Build q_pos -> section_id map for QuestionResponse stamping
    qpos_to_section_id: dict = {}
    if omr_sheet.question_order:
        from assessments.models import Question as _Q
        q_section_map = {
            q.id: q.section_id
            for q in _Q.objects.filter(id__in=omr_sheet.question_order).only("id", "section_id")
        }
        for idx, q_id in enumerate(omr_sheet.question_order):
            qpos_to_section_id[idx] = q_section_map.get(q_id)

    # Create/update StudentResult
    result, _ = StudentResult.objects.update_or_create(
        omr_sheet=omr_sheet,
        defaults={
            "test": omr_sheet.test,
            "student": omr_sheet.student,
            "score": grading["score"],
            "max_score": grading["max_score"],
            "correct_count": grading["correct_count"],
            "wrong_count": grading["wrong_count"],
            "blank_count": grading["blank_count"],
            "disqualified_count": grading.get("disqualified_count", 0),
            "needs_review": False,
            "section_breakdown": section_breakdown,
            "qualified_all": grading.get("qualified_all", True),
        },
    )

    # Wipe existing responses and recreate
    result.responses.all().delete()

    # The multi-mark (overmark) review decision is owned by grading and is
    # policy-aware: a question routes to review ONLY when the teacher's
    # multi_mark_policy is "review". Other policies (disqualify / wrong /
    # correct_if_all) resolve the question automatically — no review item.
    multi_mark_review = False

    for pq in grading["per_question"]:
        q_pos = pq["q_pos"]
        marked = pq["marked"]
        is_correct = pq["is_correct"]
        flagged = bool(pq.get("flagged"))
        if pq.get("needs_review"):
            multi_mark_review = True

        # Resolve the underlying Question FK from the sheet's question_order.
        # question_order[q_pos] is the Question id in the original (underlying) order.
        underlying_question_id = None
        if omr_sheet.question_order and q_pos < len(omr_sheet.question_order):
            underlying_question_id = omr_sheet.question_order[q_pos]

        QuestionResponse.objects.create(
            student_result=result,
            question_id=underlying_question_id,
            q_pos=q_pos,
            marked_options=marked,
            is_correct=is_correct,
            flagged=flagged,
            section_id=qpos_to_section_id.get(q_pos),
        )

    # Create exactly one open double_mark ReviewItem for the sheet when the
    # policy routes overmark(s) to review. Idempotent across regrades.
    if multi_mark_review:
        ReviewItem.objects.get_or_create(
            omr_sheet=omr_sheet,
            reason=ReviewItem.REASON_DOUBLE_MARK,
            resolved=False,
        )

    # Update needs_review (policy-driven)
    result.needs_review = multi_mark_review
    result.save(update_fields=["needs_review"])

    # Mark sheet as complete
    omr_sheet.assembly_status = omr_sheet.ASSEMBLY_COMPLETE
    omr_sheet.save(update_fields=["assembly_status"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_image(job) -> np.ndarray | None:
    """
    Load the ScanJob's image from its image_file FileField.
    Returns a uint8 grayscale or BGR ndarray, or None on failure.
    """
    try:
        if not job.image_file:
            return None
        img_file = job.image_file
        img_file.seek(0)
        raw = np.frombuffer(img_file.read(), dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
        return image
    except Exception:
        return None


def _flag_to_reason(flag: str) -> str | None:
    """Map a pipeline flag string to a ReviewItem.REASON_* constant."""
    mapping = {
        "no_qr": "no_qr",
        "alignment": "alignment",
        "roll_unreadable": "roll_unreadable",
        # "double_mark" is intentionally NOT mapped: the multi-mark review
        # decision is policy-aware and owned by _persist_grading_result, which
        # creates the ReviewItem only when multi_mark_policy == "review".
        "faint": "faint",
        "missing_page": "missing_page",
        # Phase 1B
        "test_mismatch": "test_mismatch",
        "roll_mismatch": "roll_mismatch",
    }
    return mapping.get(flag)


def _parse_test_id_from_sheet_code(sheet_code: str) -> int | None:
    """
    Parse the test_id from a sheet_code of the form "{test_id:06d}-{token}".

    Returns the integer test_id if the format is recognised, or None if the
    code is not in a parseable format (legacy tolerance: never crash).

    The format is defined by omr.codes.make_sheet_code:
        sheet_code = f"{test_id:06d}-{token}"

    The leading zero-padded 6-digit decimal before the first '-' is the test_id.
    """
    try:
        prefix = sheet_code.split("-")[0]
        return int(prefix)
    except (ValueError, IndexError, AttributeError):
        return None


def _normalize_roll(roll: str, width: int) -> str:
    """
    Normalize a roll number for comparison.

    Rules:
    - Strip to digits only (digits-only charset; alphanumeric deferred per spec note).
    - Left-pad (or truncate) to ``width`` digits.
    - A fully-blank or empty string returns "" (sentinel for unreadable).

    This ensures that a student whose roll_number is "42" and whose sheet was
    printed with roll_digits=3 (stored as "042") compares equal to the scanner
    reading "042" -- neither triggers a false roll_mismatch.
    """
    digits_only = "".join(c for c in roll if c.isdigit())
    if not digits_only:
        return ""  # blank / unreadable
    # Left-pad to width so "42" == "042" when width=3
    return digits_only.zfill(width)


def _create_review_item(*, job=None, omr_sheet=None, reason: str) -> None:
    """Create a ReviewItem for the given scan job / sheet and reason."""
    from results.models import ReviewItem
    ReviewItem.objects.create(
        scan_job=job,
        omr_sheet=omr_sheet,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Helper for tests: produce correct-answer marks for an OmrSheet
# ---------------------------------------------------------------------------

def simulate_correct_marks(omr_sheet) -> dict:
    """
    Return a marked dict that represents filling in the correct answers.

    Returns
    -------
    dict {int(q_pos): list[correct_printed_labels]}
    """
    return {
        int(pos): list(labels)
        for pos, labels in omr_sheet.answer_key.items()
    }
