"""
omr.scan.pipeline — End-to-end scan processing pipeline.

process_image(image, descriptor) -> dict
    Full pipeline: decode QR → detect fiducials → warp → binary → read.

process_scan_job(job)
    Load the job's image, run process_image, persist reads/status,
    then try to grade if all pages are in.

_maybe_grade(omr_sheet)
    Gather all done ScanJobs; if all pages present, aggregate reads,
    call grade_sheet, persist StudentResult + QuestionResponses + ReviewItems.
"""

from __future__ import annotations

import cv2
import numpy as np
from decimal import Decimal

from omr.scan.align import decode_qr, detect_fiducials, warp_to_canonical
from omr.scan.read import to_binary, read_roll, read_answers
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
        roll        : str | None
        flags       : list[str]
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
            "roll": None,
            "flags": ["no_qr"],
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
            "roll": None,
            "flags": ["alignment"],
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

    return {
        "sheet_code": sheet_code,
        "page": page,
        "total": total,
        "reads": reads,
        "roll": roll,
        "flags": flags,
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

    job.save(update_fields=["omr_sheet", "page_no", "reads", "status",
                             "error_reason", "confidence"])

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
    from results.models import StudentResult, QuestionResponse, ReviewItem

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
            "needs_review": False,
        },
    )

    # Wipe existing responses and recreate
    result.responses.all().delete()

    # Track whether any question flags triggered review
    needs_review = False
    has_double_mark = False

    for pq in grading["per_question"]:
        q_pos = pq["q_pos"]
        marked = pq["marked"]
        is_correct = pq["is_correct"]
        flagged = pq["flagged"]

        # Check if this q_pos had a flag in ANY job's reads
        for job in done_jobs:
            answers = job.reads.get("answers", {})
            entry = answers.get(str(q_pos), {})
            if entry.get("flag") == "double_mark":
                flagged = True
                has_double_mark = True

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
        )

    # Set needs_review when a double-mark was detected. The ReviewItem itself is
    # already created per-flag in process_scan_job, so we do NOT create another
    # here (avoids duplicate double_mark ReviewItems).
    if has_double_mark:
        needs_review = True

    # Update needs_review
    result.needs_review = needs_review
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
        "double_mark": "double_mark",
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
    reading "042" — neither triggers a false roll_mismatch.
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
