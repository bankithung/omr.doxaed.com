"""
Phase 1B tests — Scan identity (which-test guard) + verify-only roll reconciliation.

Coverage:
  1. test_mismatch: sheet from test X uploaded to batch for test Y → flagged
     test_mismatch, NOT graded against Y. Correct same-test scan still grades.
  2. legacy_decode: existing sheet_code format (000042-TOKEN) still parses the
     test_id and resolves the sheet — no regression.
  3. roll_mismatch (tamper): prebubbled sheet whose printed roll is altered to a
     DIFFERENT valid roll → flagged roll_mismatch; identity/grading still proceed
     via QR (StudentResult is created for the correct student).
  4. no false positive on short roll: student roll "42" with sheet roll_digits=3
     (printed "042") → normalization makes them equal → NO roll_mismatch.
  5. clean Mode B: prebubbled sheet with the correct roll → no roll_mismatch,
     grades correctly.

All tests exercise process_scan_job (the pipeline) directly, using simulate_scan
to produce synthetic images.
"""

from __future__ import annotations

import cv2
import numpy as np
from decimal import Decimal

from django.test import TestCase

from omr.codes import make_sheet_code
from omr.geometry import build_template
from omr.scan.pipeline import _parse_test_id_from_sheet_code, _normalize_roll


# ---------------------------------------------------------------------------
# Unit tests for the new helper functions
# ---------------------------------------------------------------------------

class ParseTestIdTests(TestCase):
    """_parse_test_id_from_sheet_code extracts the test_id prefix correctly."""

    def test_standard_format_parses(self):
        self.assertEqual(_parse_test_id_from_sheet_code("000042-AB3DEFGH"), 42)

    def test_leading_zeros_stripped(self):
        self.assertEqual(_parse_test_id_from_sheet_code("000001-XXXXXXXX"), 1)

    def test_large_test_id(self):
        self.assertEqual(_parse_test_id_from_sheet_code("999999-XXXXXXXX"), 999999)

    def test_make_sheet_code_round_trip(self):
        """make_sheet_code produces a code whose test_id parses back correctly."""
        from omr.codes import make_sheet_code
        sheet_code, _ = make_sheet_code(123, 9999)
        self.assertEqual(_parse_test_id_from_sheet_code(sheet_code), 123)

    def test_legacy_format_without_six_digits(self):
        """If the prefix is a valid int (even without 6 chars), it parses."""
        self.assertEqual(_parse_test_id_from_sheet_code("42-TOKEN"), 42)

    def test_no_dash_returns_none(self):
        """Unparseable code (no dash) returns None — no crash."""
        result = _parse_test_id_from_sheet_code("NODASH")
        # The whole string is tried as int; "NODASH" is not a valid int
        self.assertIsNone(result)

    def test_empty_string_returns_none(self):
        self.assertIsNone(_parse_test_id_from_sheet_code(""))

    def test_none_returns_none(self):
        self.assertIsNone(_parse_test_id_from_sheet_code(None))


class NormalizeRollTests(TestCase):
    """_normalize_roll pads rolls to width and strips non-digits."""

    def test_short_roll_left_padded(self):
        """Roll "42" with width=3 → "042"."""
        self.assertEqual(_normalize_roll("42", 3), "042")

    def test_exact_width_unchanged(self):
        self.assertEqual(_normalize_roll("042", 3), "042")

    def test_blank_returns_empty(self):
        self.assertEqual(_normalize_roll("", 3), "")

    def test_question_marks_stripped(self):
        """'?' from unreadable columns → treated as non-digit → blank."""
        self.assertEqual(_normalize_roll("???", 3), "")

    def test_partial_question_marks(self):
        """Partially unreadable "04?" → digits "04" → "004" padded to 3."""
        self.assertEqual(_normalize_roll("04?", 3), "004")

    def test_zero_roll_is_not_blank(self):
        """Roll "000" (all zeros) is a valid roll, not blank."""
        result = _normalize_roll("000", 3)
        self.assertEqual(result, "000")

    def test_mixed_digits_and_chars_stripped(self):
        """Non-digit chars removed; remaining digits padded."""
        self.assertEqual(_normalize_roll("0-4-2", 3), "042")

    def test_short_roll_matches_padded_stored(self):
        """Student roll "42", scanned reading "042" with width=3 → equal."""
        self.assertEqual(
            _normalize_roll("42", 3),
            _normalize_roll("042", 3),
        )


# ---------------------------------------------------------------------------
# Integration test helpers
# ---------------------------------------------------------------------------

def _build_user_and_test(email, mode="standard", n_questions=5):
    """Create User → ClassGroup → Test → Questions + MarkingScheme."""
    from django.contrib.auth import get_user_model
    from assessments.models import ClassGroup, MarkingScheme, Option, Question, Test

    User = get_user_model()
    user = User.objects.create_user(email=email, password="p1bpass")
    cg = ClassGroup.objects.create(user=user, created_by=user, name=f"CG-{email[:8]}")
    test = Test.objects.create(
        user=user, class_group=cg, created_by=user,
        title="P1B Test", mode=mode,
    )
    MarkingScheme.objects.create(test=test, marks_per_correct=1, negative_marks_per_wrong=0)
    for i in range(n_questions):
        q = Question.objects.create(test=test, order_index=i, text=f"Q{i}?")
        for j, label in enumerate(["A", "B", "C", "D"]):
            Option.objects.create(question=q, label=label, text=label,
                                  is_correct=(j == 0))
    return user, test


def _build_omr_sheet(
    test,
    user,
    roll_number="001",
    roll_kind="writein",
    roll_digits=3,
    n_questions=5,
    seed=None,
):
    """Build OmrSheet + Roster + Student; return (omr_sheet, sheet_meta, descriptor, student)."""
    from assessments.models import Question
    from omr.models import OmrSheet
    from omr.shuffle import build_sheet_plan
    from rosters.models import Roster, Student

    roster = Roster.objects.create(user=user, created_by=user, name=f"Roster-{roll_number}")
    student = Student.objects.create(roster=roster, roll_number=roll_number,
                                     full_name=f"Student {roll_number}")

    questions_data = [
        {
            "id": q.id,
            "options": [{"label": o.label, "is_correct": o.is_correct}
                        for o in q.options.all()],
        }
        for q in Question.objects.filter(test=test).order_by("order_index")
    ]
    if seed is None:
        seed = test.id * 1000 + int(roll_number.lstrip("0") or "0")

    plan = build_sheet_plan(questions_data, seed=seed,
                            shuffle_questions=False, shuffle_options=False)
    descriptor = build_template(
        num_questions=n_questions,
        num_options=4,
        roll_digits=roll_digits,
        roll_kind=roll_kind,
    )
    sheet_code, human_code = make_sheet_code(test.id, seed)
    roll_value = roll_number if roll_kind == "prebubbled" else ""
    omr_sheet = OmrSheet.objects.create(
        test=test,
        student=student,
        sheet_code=sheet_code,
        human_readable_code=human_code,
        shuffle_version=seed,
        question_order=plan["question_order"],
        option_order=plan["option_order"],
        answer_key=plan["answer_key"],
        template_descriptor=descriptor,
        page_count=descriptor["page_count"],
        page_map=descriptor["page_map"],
        roll_kind=roll_kind,
        roll_value=roll_value,
    )
    sheet_meta = {
        "sheet_code": sheet_code,
        "human_readable_code": human_code,
        "institution": "Phase 1B School",
        "test_title": "P1B Test",
        "subject": "P1B",
        "student_name": f"Student {roll_number}",
        "roll_label": "Roll No.",
        "roll_digits": roll_digits,
        "roll_value": roll_value,
    }
    return omr_sheet, sheet_meta, descriptor, student


def _make_and_run_scan_job(test, user, omr_sheet, sheet_meta, descriptor,
                            marked, roll, scale=2.0):
    """
    Simulate a scan image, create ScanBatch + ScanJob, run process_scan_job,
    and return (batch, job) after refreshing from db.
    """
    from django.core.files.base import ContentFile
    from omr.models import ScanBatch, ScanJob
    from omr.scan.pipeline import process_scan_job
    from omr.simulate import simulate_scan

    img = simulate_scan(descriptor, sheet_meta, marked=marked, roll=roll, page=0, scale=scale)
    ok, buf = cv2.imencode(".png", img)
    assert ok, "cv2.imencode failed"

    batch = ScanBatch.objects.create(test=test, created_by=user, total=1)
    job = ScanJob(batch=batch, page_no=1)
    job.image_file.save("p1b_scan.png", ContentFile(buf.tobytes()), save=True)

    process_scan_job(job)

    job.refresh_from_db()
    batch.refresh_from_db()
    return batch, job


# ---------------------------------------------------------------------------
# Test 1 — test_mismatch guard
# ---------------------------------------------------------------------------

class TestMismatchTests(TestCase):
    """
    A sheet generated for test X, uploaded into a batch for test Y,
    must be flagged test_mismatch and NOT graded.
    """

    N_QUESTIONS = 5
    SCALE = 2.0

    def setUp(self):
        # Two separate tests owned by the same user
        self.user, self.test_x = _build_user_and_test(
            email="mismatch_x@p1b.test", n_questions=self.N_QUESTIONS
        )
        from assessments.models import ClassGroup, MarkingScheme, Option, Question, Test
        cg = self.test_x.class_group
        self.test_y = Test.objects.create(
            user=self.user, class_group=cg, created_by=self.user,
            title="Test Y",
        )
        MarkingScheme.objects.create(self.test_y, marks_per_correct=1,
                                     negative_marks_per_wrong=0) if False else None
        MarkingScheme.objects.create(
            test=self.test_y, marks_per_correct=1, negative_marks_per_wrong=0
        )
        for i in range(self.N_QUESTIONS):
            q = Question.objects.create(test=self.test_y, order_index=i, text=f"QY{i}")
            for j, label in enumerate(["A", "B", "C", "D"]):
                Option.objects.create(question=q, label=label, text=label,
                                      is_correct=(j == 0))

        # Build a sheet for test X
        self.sheet_x, self.meta_x, self.desc_x, self.student_x = _build_omr_sheet(
            self.test_x, self.user, roll_number="007", seed=111111
        )

    def test_cross_test_scan_flagged_test_mismatch(self):
        """Sheet belonging to test X uploaded into a batch for test Y → test_mismatch."""
        from django.core.files.base import ContentFile
        from omr.models import ScanBatch, ScanJob
        from omr.scan.pipeline import process_scan_job
        from omr.simulate import simulate_scan
        from results.models import ReviewItem, StudentResult

        img = simulate_scan(self.desc_x, self.meta_x, marked={0: ["A"]},
                            roll="007", page=0, scale=self.SCALE)
        ok, buf = cv2.imencode(".png", img)
        self.assertTrue(ok)

        # Batch is for test_Y (the WRONG test)
        batch = ScanBatch.objects.create(test=self.test_y, created_by=self.user, total=1)
        job = ScanJob(batch=batch, page_no=1)
        job.image_file.save("mismatch.png", ContentFile(buf.tobytes()), save=True)

        process_scan_job(job)
        job.refresh_from_db()

        self.assertEqual(job.status, ScanJob.STATUS_NEEDS_REVIEW,
                         f"Expected needs_review, got {job.status!r}")
        self.assertEqual(job.error_reason, "test_mismatch")

        # A ReviewItem with reason=test_mismatch must exist
        self.assertTrue(
            ReviewItem.objects.filter(scan_job=job, reason="test_mismatch").exists(),
            "Expected a ReviewItem with reason=test_mismatch"
        )

        # No StudentResult should have been created for test Y
        self.assertFalse(
            StudentResult.objects.filter(test=self.test_y).exists(),
            "No StudentResult should be created when test_mismatch is raised"
        )

    def test_correct_test_scan_grades_normally(self):
        """Same sheet uploaded into a batch for the CORRECT test X → grades normally."""
        from omr.scan.pipeline import simulate_correct_marks
        from results.models import StudentResult

        correct_marks = simulate_correct_marks(self.sheet_x)
        _, job = _make_and_run_scan_job(
            self.test_x, self.user, self.sheet_x, self.meta_x, self.desc_x,
            marked=correct_marks, roll="007",
        )

        from omr.models import ScanJob
        self.assertEqual(job.status, ScanJob.STATUS_DONE,
                         f"Correct-test scan should be done, got {job.status!r} "
                         f"(err={job.error_reason})")

        self.assertTrue(
            StudentResult.objects.filter(omr_sheet=self.sheet_x).exists(),
            "StudentResult must exist after a successful same-test scan"
        )


# ---------------------------------------------------------------------------
# Test 2 — legacy decode (test_id is always parseable from existing format)
# ---------------------------------------------------------------------------

class LegacyDecodeTests(TestCase):
    """
    Existing-format sheet codes (produced by make_sheet_code before Phase 1B)
    must still be parsed correctly — no regression.
    """

    def test_make_sheet_code_format_parses_test_id(self):
        """
        make_sheet_code embeds test_id as the first 6-digit zero-padded prefix.
        _parse_test_id_from_sheet_code must recover the original test_id.
        """
        for test_id in [1, 42, 999, 123456]:
            sheet_code, _ = make_sheet_code(test_id, seed=42)
            parsed = _parse_test_id_from_sheet_code(sheet_code)
            self.assertEqual(
                parsed, test_id,
                f"test_id={test_id}: expected {test_id} but got {parsed!r} "
                f"from sheet_code={sheet_code!r}"
            )

    def test_pipeline_resolves_existing_sheet_on_correct_batch(self):
        """
        End-to-end: a sheet generated with the current make_sheet_code format
        resolves correctly (no test_mismatch) when uploaded to the matching batch.
        """
        user, test = _build_user_and_test(email="legacy@p1b.test", n_questions=5)
        omr_sheet, sheet_meta, descriptor, _ = _build_omr_sheet(
            test, user, roll_number="099"
        )
        from omr.scan.pipeline import simulate_correct_marks
        from omr.models import ScanJob

        correct_marks = simulate_correct_marks(omr_sheet)
        _, job = _make_and_run_scan_job(
            test, user, omr_sheet, sheet_meta, descriptor,
            marked=correct_marks, roll="099",
        )
        self.assertNotEqual(job.status, ScanJob.STATUS_FAILED,
                            f"Job failed — legacy decode broke: {job.error_reason}")
        self.assertNotIn("test_mismatch", job.error_reason,
                         "Unexpected test_mismatch on a correctly-matching sheet")


# ---------------------------------------------------------------------------
# Test 3 — roll_mismatch (tamper-evidence)
# ---------------------------------------------------------------------------

class RollMismatchTests(TestCase):
    """
    A prebubbled sheet whose printed roll is altered to a DIFFERENT valid roll
    must be flagged roll_mismatch; identity/grading still proceed via the QR.

    Simulation strategy: we store the OmrSheet with roll_kind="prebubbled" and
    roll_value="042", but we use a write-in descriptor for image generation so
    the PDF does NOT pre-fill any discs.  We then call simulate_scan with a
    DIFFERENT roll ("999").  The scanner reads a clean "999" and compares it to
    the stored "042" — this is the tamper scenario without the multi-fill
    ambiguity that would occur if we drew on top of a pre-printed disc.
    """

    N_QUESTIONS = 5
    SCALE = 2.0
    STORED_ROLL = "042"
    TAMPERED_ROLL = "999"

    def setUp(self):
        self.user, self.test = _build_user_and_test(
            email="rollmismatch@p1b.test", mode="roster_prebubbled",
            n_questions=self.N_QUESTIONS,
        )
        # Build using a write-in descriptor so simulate_scan can cleanly fill
        # a single digit per column (no pre-print conflict).
        # The OmrSheet model is stored with roll_kind="prebubbled" and
        # roll_value="042" so the reconciliation logic runs.
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(
                self.test, self.user,
                roll_number=self.STORED_ROLL,
                roll_kind="prebubbled",      # model says prebubbled → reconcile
                roll_digits=3,
                seed=777777,
            )
        # Override the descriptor to write-in so the PDF has no pre-filled discs,
        # letting simulate_scan fill a single clean digit per column.
        from omr.geometry import build_template
        self._writein_descriptor = build_template(
            num_questions=self.N_QUESTIONS, num_options=4, roll_digits=3,
            roll_kind="writein",
        )
        # Update the stored descriptor on the OmrSheet so the pipeline reads
        # roll grid geometry correctly (same geometry, just kind differs).
        # We keep the sheet_code / answer_key / QR as-is.
        self.omr_sheet.template_descriptor = self._writein_descriptor
        self.omr_sheet.save(update_fields=["template_descriptor"])

    def _make_scan_with_roll(self, roll: str):
        """Helper: simulate a scan with the given roll string."""
        from django.core.files.base import ContentFile
        from omr.models import ScanBatch, ScanJob
        from omr.scan.pipeline import process_scan_job, simulate_correct_marks
        from omr.simulate import simulate_scan

        correct_marks = simulate_correct_marks(self.omr_sheet)
        img = simulate_scan(
            self._writein_descriptor, self.sheet_meta,
            marked=correct_marks, roll=roll, page=0, scale=self.SCALE,
        )
        ok, buf = cv2.imencode(".png", img)
        self.assertTrue(ok, "cv2.imencode failed")

        batch = ScanBatch.objects.create(test=self.test, created_by=self.user, total=1)
        job = ScanJob(batch=batch, page_no=1)
        job.image_file.save("p1b_tamper.png", ContentFile(buf.tobytes()), save=True)
        process_scan_job(job)
        job.refresh_from_db()
        return job

    def test_tampered_roll_flags_roll_mismatch(self):
        """
        A cleanly-read roll that differs from the stored student roll on a
        prebubbled sheet → roll_mismatch flagged, job goes to needs_review.
        """
        from omr.models import ScanJob
        from results.models import ReviewItem

        job = self._make_scan_with_roll(self.TAMPERED_ROLL)

        self.assertEqual(job.status, ScanJob.STATUS_NEEDS_REVIEW,
                         f"Expected needs_review after roll tamper, got {job.status!r} "
                         f"(err={job.error_reason!r})")
        self.assertIn("roll_mismatch", job.error_reason,
                      f"error_reason should contain 'roll_mismatch', got {job.error_reason!r}")

        self.assertTrue(
            ReviewItem.objects.filter(scan_job=job, reason="roll_mismatch").exists(),
            "Expected ReviewItem with reason=roll_mismatch"
        )

    def test_tampered_roll_identity_still_graded_via_qr(self):
        """
        Despite a tampered roll, the QR still identifies the correct student
        and the sheet is graded (a StudentResult is created for the right student).
        """
        from results.models import StudentResult

        job = self._make_scan_with_roll(self.TAMPERED_ROLL)

        # Grading still proceeds because identity comes from the QR
        self.assertTrue(
            StudentResult.objects.filter(omr_sheet=self.omr_sheet).exists(),
            "StudentResult must be created even when roll_mismatch is flagged — "
            "identity comes from QR, not the roll"
        )
        sr = StudentResult.objects.get(omr_sheet=self.omr_sheet)
        self.assertEqual(sr.student, self.student,
                         "StudentResult.student must be the QR-identified student")


# ---------------------------------------------------------------------------
# Test 4 — no false positive on short roll (zero-padding normalization)
# ---------------------------------------------------------------------------

class ShortRollNormalizationTests(TestCase):
    """
    A prebubbled sheet where student.roll_number="42" and roll_digits=3
    (stored/printed as "042") must NOT trigger roll_mismatch.
    """

    N_QUESTIONS = 5
    SCALE = 2.0

    def setUp(self):
        self.user, self.test = _build_user_and_test(
            email="shorroll@p1b.test", mode="roster_prebubbled",
            n_questions=self.N_QUESTIONS,
        )
        # Student roll "42" (short; will be stored as-is, printed as "042")
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(
                self.test, self.user,
                roll_number="42",   # short roll
                roll_kind="prebubbled",
                roll_digits=3,
                seed=555555,
            )

    def test_short_roll_does_not_false_flag(self):
        """
        Student roll "42", printed as "042" on a 3-digit sheet:
        normalize both → equal → no roll_mismatch.
        """
        from omr.models import ScanJob
        from results.models import ReviewItem
        from omr.scan.pipeline import simulate_correct_marks

        correct_marks = simulate_correct_marks(self.omr_sheet)

        # The scanner will read "042" from the prebubbled grid; the student roll
        # is "42"; _normalize_roll should make them equal (both → "042").
        _, job = _make_and_run_scan_job(
            self.test, self.user, self.omr_sheet, self.sheet_meta, self.descriptor,
            marked=correct_marks,
            roll="042",  # what the scanner reads from the 3-column prebubbled grid
        )

        self.assertNotIn("roll_mismatch", job.error_reason or "",
                         f"Short roll '42' == padded '042': should not trigger roll_mismatch. "
                         f"error_reason={job.error_reason!r}")
        self.assertFalse(
            ReviewItem.objects.filter(scan_job=job, reason="roll_mismatch").exists(),
            "No roll_mismatch ReviewItem should be created for a short-roll match"
        )

    def test_normalization_unit(self):
        """Direct normalization check: "42" and "042" normalize equal at width=3."""
        self.assertEqual(_normalize_roll("42", 3), _normalize_roll("042", 3))
        self.assertEqual(_normalize_roll("42", 3), "042")


# ---------------------------------------------------------------------------
# Test 5 — clean Mode B (prebubbled, correct roll, no mismatch)
# ---------------------------------------------------------------------------

class CleanModeBTests(TestCase):
    """
    A prebubbled sheet with the correct roll filled in → no roll_mismatch,
    grades correctly.
    """

    N_QUESTIONS = 5
    SCALE = 2.0

    def setUp(self):
        self.user, self.test = _build_user_and_test(
            email="cleanb@p1b.test", mode="roster_prebubbled",
            n_questions=self.N_QUESTIONS,
        )
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(
                self.test, self.user,
                roll_number="042",
                roll_kind="prebubbled",
                roll_digits=3,
                seed=333333,
            )

    def test_clean_mode_b_no_roll_mismatch(self):
        """Correct prebubbled roll → no roll_mismatch review item."""
        from omr.models import ScanJob
        from results.models import ReviewItem
        from omr.scan.pipeline import simulate_correct_marks

        correct_marks = simulate_correct_marks(self.omr_sheet)
        _, job = _make_and_run_scan_job(
            self.test, self.user, self.omr_sheet, self.sheet_meta, self.descriptor,
            marked=correct_marks,
            roll="042",  # correct roll
        )

        self.assertFalse(
            ReviewItem.objects.filter(scan_job=job, reason="roll_mismatch").exists(),
            f"No roll_mismatch should be raised for a correct prebubbled roll. "
            f"error_reason={job.error_reason!r}"
        )

    def test_clean_mode_b_grades_correctly(self):
        """Clean Mode B scan produces a StudentResult with full marks."""
        from results.models import StudentResult
        from omr.scan.pipeline import simulate_correct_marks

        correct_marks = simulate_correct_marks(self.omr_sheet)
        _, job = _make_and_run_scan_job(
            self.test, self.user, self.omr_sheet, self.sheet_meta, self.descriptor,
            marked=correct_marks,
            roll="042",
        )

        self.assertTrue(
            StudentResult.objects.filter(omr_sheet=self.omr_sheet).exists(),
            "StudentResult must be created for a clean Mode B scan"
        )
        sr = StudentResult.objects.get(omr_sheet=self.omr_sheet)
        self.assertEqual(sr.score, Decimal(str(self.N_QUESTIONS)),
                         f"Expected perfect score={self.N_QUESTIONS}, got {sr.score}")
        self.assertEqual(sr.student, self.student)

    def test_writein_mode_does_not_roll_check(self):
        """
        Standard (write-in) sheets do NOT trigger roll reconciliation even if
        the filled roll differs from the student's stored roll.
        """
        from omr.models import ScanJob
        from results.models import ReviewItem

        user, test = _build_user_and_test(
            email="writein_nocheck@p1b.test", n_questions=self.N_QUESTIONS,
        )
        # Standard (writein) sheet
        omr_sheet, sheet_meta, descriptor, _ = _build_omr_sheet(
            test, user, roll_number="042", roll_kind="writein", roll_digits=3,
            seed=222222,
        )
        from omr.scan.pipeline import simulate_correct_marks
        correct_marks = simulate_correct_marks(omr_sheet)

        # Fill "999" as roll — for a writein sheet this is fine (student writes in)
        _, job = _make_and_run_scan_job(
            test, user, omr_sheet, sheet_meta, descriptor,
            marked=correct_marks,
            roll="999",  # different from stored roll, but writein → no check
        )

        self.assertFalse(
            ReviewItem.objects.filter(scan_job=job, reason="roll_mismatch").exists(),
            "roll_mismatch must NOT be raised for a write-in sheet"
        )
