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

import uuid

import cv2
import numpy as np
from decimal import Decimal

from omr.scan.align import (
    crop_to_page,
    decode_qr,
    decode_qr_fast,
    decode_qr_from_canonical,
    detect_fiducials,
    warp_to_canonical,
)
from omr.scan.read import to_binary, read_roll, read_answers, page_ink_level
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

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ---- Stage 0: crop to the sheet ----
    # Everything downstream assumes the frame is paper. A photograph is not: it
    # contains a desk, and a global threshold over desk-plus-paper separates
    # those two rather than ink from paper, which dissolves every fiducial.
    page_img = crop_to_page(gray, descriptor)

    # ---- Stage 1: align ----
    # Alignment comes BEFORE the QR now. Searching a multi-megapixel frame for
    # an 80 px block fails on precisely the captures a phone produces, and
    # fails slowly. Rectifying first turns the QR into a known square that can
    # be upscaled and deblurred on its own, which is both faster and more
    # capable. Fiducials survive blur far better than a QR does, so they are
    # the more reliable thing to find first.
    src_pts = detect_fiducials(page_img, descriptor)
    if src_pts is None and page_img is not gray:
        src_pts = detect_fiducials(gray, descriptor)
        if src_pts is not None:
            page_img = gray

    canonical = None
    qr_result = None
    if src_pts is not None:
        canonical = warp_to_canonical(page_img, src_pts, descriptor)
        found = decode_qr_from_canonical(canonical, descriptor)
        if found is not None:
            qr_result, upside_down = found
            if upside_down:
                # The QR landing in the opposite corner IS the orientation
                # test. Four identical corner squares are rotationally
                # symmetric, so an upside down sheet warps perfectly and would
                # otherwise be graded against mirrored positions, which used to
                # produce a confident near-zero score.
                canonical = cv2.rotate(canonical, cv2.ROTATE_180)

    # Fall back to the raw frame ONLY when alignment failed. That covers a
    # sheet whose corners are damaged or cropped, where the page cannot be
    # squared up but the code may still be legible, so the upload can at least
    # be attributed to a student.
    #
    # If alignment succeeded and the QR still would not read from the position
    # the template puts it in, searching the whole frame cannot do better: the
    # code itself is destroyed. Running the full ladder anyway cost 8.6 s per
    # sheet on badly blurred captures and never once succeeded.
    if qr_result is None and canonical is None:
        qr_result = decode_qr_fast(page_img)
        if qr_result is None and page_img is not gray:
            qr_result = decode_qr_fast(gray)
        if qr_result is None:
            qr_result = decode_qr(page_img)

    if qr_result is None:
        return {
            "sheet_code": None, "page": None, "total": None,
            "reads": {}, "fill_ratios": {}, "roll": None,
            "flags": ["no_qr"], "canonical": None, "confidence": 0.0,
        }

    sheet_code, page_1based, total = qr_result
    page = page_1based - 1  # convert to 0-based

    if canonical is None:
        # QR readable but the page could not be squared up. Never grade off an
        # unrectified image: the bubble coordinates would be meaningless.
        return {
            "sheet_code": sheet_code, "page": page, "total": total,
            "reads": {}, "fill_ratios": {}, "roll": None,
            "flags": ["alignment"], "canonical": None, "confidence": 0.0,
        }

    # ---- Stage 4: Per-page ink reference ----
    # Calibrated from the fiducials, which are the only marks guaranteed to be
    # solid print on this page, so exposure cancels out of every measurement.
    ink_level = page_ink_level(canonical, descriptor)

    # ---- Stage 5: Read roll (page 0 only) ----
    roll: str | None = None
    if page == 0:
        roll, roll_flag = read_roll(canonical, descriptor)
        if roll_flag:
            flags.append(roll_flag)

    # ---- Stage 6: Read answers ----
    reads = read_answers(canonical, descriptor, page=page, ink_level=ink_level)

    for q_pos, entry in reads.items():
        if entry.get("flag"):
            flags.append(entry["flag"])

    # ---- Stage 7: Per-question darkness, kept as fill_ratios ----
    # Same field name and meaning as before (0 blank, 1 solidly marked), but
    # now a normalised greyness rather than a count of post-threshold pixels,
    # so a faint mark reads as a small number instead of rounding to zero.
    fill_ratios: dict[int, float] = {}
    for q_pos, entry in reads.items():
        dk = entry.get("darkness") or {}
        marked = entry.get("marked", [])
        if marked:
            fill_ratios[q_pos] = float(max(dk.get(l, 0.0) for l in marked))
        elif dk:
            fill_ratios[q_pos] = float(max(dk.values()))
        else:
            fill_ratios[q_pos] = 0.0

    # ---- Stage 8: Confidence ----
    # The smallest margin by which any single question escaped being decided
    # differently. This used to be the fraction of unflagged questions, which
    # is 1.0 exactly when nothing was flagged, so a page read entirely wrong
    # reported full confidence.
    if reads:
        confidence = float(min(e.get("margin", 0.0) for e in reads.values()))
        confidence = float(np.clip(confidence / 0.30, 0.0, 1.0))
    else:
        confidence = 0.0

    # A page where nothing at all was marked is far more often a misread than a
    # genuinely blank sheet, and it costs one click to confirm.
    if reads and all(not e.get("marked") for e in reads.values()):
        flags.append("all_blank")

    return {
        "sheet_code": sheet_code,
        "page": page,
        "total": total,
        "reads": reads,
        "fill_ratios": fill_ratios,
        "roll": roll,
        "flags": flags,
        "canonical": canonical,
        "confidence": confidence,
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
    if parsed_test_id is not None and parsed_test_id != _test_id_prefix(job.batch.test_id):
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

    # Confidence comes from process_image: the smallest margin by which any
    # question escaped a different decision. The old formula was the fraction
    # of unflagged questions, which reports 1.0 precisely when nothing was
    # flagged, including on a page that was read entirely wrong.
    job.confidence = float(result.get("confidence", 0.0))

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

    # Create ReviewItems for each flag.
    #
    # Per-question flags ("faint") must carry the q_pos they were raised for,
    # otherwise resolution cannot tell which answer the teacher is correcting.
    # `flags` is a flat list, so recover the positions from the per-question
    # reads, which is where those flags originated.
    per_question_flags: dict[str, list[int]] = {}
    for _q_pos, _entry in result.get("reads", {}).items():
        _flag = _entry.get("flag")
        if _flag:
            per_question_flags.setdefault(_flag, []).append(int(_q_pos))

    seen_per_question: dict[str, int] = {}
    for flag in flags:
        reason = _flag_to_reason(flag)
        if not reason:
            continue
        positions = per_question_flags.get(flag)
        if positions:
            # One ReviewItem per flagged question, in the order the flags were
            # appended, so N faint questions raise N distinct correctable items
            # instead of N identical ones pointing nowhere.
            idx = seen_per_question.get(flag, 0)
            seen_per_question[flag] = idx + 1
            q_pos = positions[idx] if idx < len(positions) else None
        else:
            q_pos = None  # sheet-level flag
        _create_review_item(
            job=job, omr_sheet=omr_sheet, reason=reason, q_pos=q_pos
        )

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
            # question_order holds STRING ids — key by str(q.id) to match.
            str(q.id): q.section_id
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
    review_q_positions: list[int] = []

    for pq in grading["per_question"]:
        q_pos = pq["q_pos"]
        marked = pq["marked"]
        is_correct = pq["is_correct"]
        flagged = bool(pq.get("flagged"))
        if pq.get("needs_review"):
            multi_mark_review = True
            review_q_positions.append(q_pos)

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

    # One open double_mark ReviewItem PER over-marked question when the policy
    # routes overmarks to review. It used to be a single sheet-level item for
    # any number of over-marked questions, which left the teacher no way to say
    # which question they were correcting. Idempotent across regrades.
    for _q_pos in review_q_positions:
        ReviewItem.objects.get_or_create(
            omr_sheet=omr_sheet,
            reason=ReviewItem.REASON_DOUBLE_MARK,
            q_pos=_q_pos,
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
        # Nothing at all was marked. Far more often a misread page than a
        # genuinely blank one, and it costs a teacher one click to confirm.
        "all_blank": "alignment",
        # Phase 1B
        "test_mismatch": "test_mismatch",
        "roll_mismatch": "roll_mismatch",
    }
    return mapping.get(flag)


def _parse_test_id_from_sheet_code(sheet_code: str):
    """
    Return the test-identifying prefix of a sheet_code, lowercased, or None.

    ``make_sheet_code`` builds "{first 8 hex of the test UUID}-{token}"
    (omr/codes.py), deliberately short so the printed QR stays easy to decode.

    This used to call ``uuid.UUID(hex=prefix)`` on that 8 character prefix.
    A UUID needs 32 hex characters, so the call ALWAYS raised, this ALWAYS
    returned None, and the test-identity guard that depends on it never fired
    once: a sheet printed for a different exam was accepted and graded against
    the wrong answer key, with no flag.

    Comparing prefixes is a cheap pre-check, not the authority. The OmrSheet
    lookup by full sheet_code + batch test still enforces the real match, so an
    8 hex collision costs nothing beyond a missed early exit.
    """
    try:
        prefix = sheet_code.split("-")[0].strip().lower()
    except (IndexError, AttributeError):
        return None
    if not prefix:
        return None
    # Must look like the hex prefix we emit; anything else is unparseable.
    try:
        int(prefix, 16)
    except ValueError:
        return None
    return prefix


def _test_id_prefix(test_id) -> str:
    """The sheet_code prefix a given test id would produce. Mirrors make_sheet_code."""
    return str(test_id).replace("-", "")[:8].lower()


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


def _create_review_item(*, job=None, omr_sheet=None, reason: str, q_pos=None) -> None:
    """
    Create a ReviewItem for the given scan job / sheet and reason.

    ``q_pos`` is the 1-based question this flag was raised for, or None for a
    sheet-level flag. It MUST be passed for per-question reasons: resolution
    targets the response by q_pos, and an item without one cannot be corrected.
    """
    from results.models import ReviewItem
    ReviewItem.objects.create(
        scan_job=job,
        omr_sheet=omr_sheet,
        reason=reason,
        q_pos=q_pos,
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
