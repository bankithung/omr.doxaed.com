"""
TDD tests for Task 1 scan + result models:
  ScanBatch / ScanJob (omr app)
  StudentResult / QuestionResponse / ReviewItem (results app)

Tests create the full model chain and assert FK relations and field defaults.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from assessments.models import ClassGroup, Question, Test
from omr.models import OmrSheet, ScanBatch, ScanJob
from results.models import QuestionResponse, ReviewItem, StudentResult
from rosters.models import Roster, Student

User = get_user_model()


def make_user(email="teacher@test.com"):
    return User.objects.create_user(email=email, password="testpass123")


def make_test(user):
    cg = ClassGroup.objects.create(user=user, created_by=user, name="CG1")
    return Test.objects.create(user=user, class_group=cg, created_by=user, title="T1")


def make_omr_sheet(test):
    return OmrSheet.objects.create(
        test=test,
        sheet_code="SHEET001",
        human_readable_code="S001",
    )


def make_question(test):
    return Question.objects.create(test=test, order_index=1, text="Q1?")


def make_student(user):
    roster = Roster.objects.create(user=user, created_by=user, name="R1")
    return Student.objects.create(roster=roster, roll_number="001")


class ScanBatchModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.test = make_test(self.user)

    def test_create_scan_batch_defaults(self):
        batch = ScanBatch.objects.create(
            test=self.test,
            created_by=self.user,
        )
        self.assertEqual(batch.status, ScanBatch.STATUS_QUEUED)
        self.assertEqual(batch.total, 0)
        self.assertEqual(batch.processed, 0)
        self.assertIsNotNone(batch.created_at)

    def test_scan_batch_status_choices(self):
        batch = ScanBatch.objects.create(
            test=self.test,
            created_by=self.user,
            status=ScanBatch.STATUS_PROCESSING,
            total=5,
            processed=2,
        )
        self.assertEqual(batch.status, "processing")
        self.assertEqual(batch.total, 5)
        self.assertEqual(batch.processed, 2)

    def test_scan_batch_str(self):
        batch = ScanBatch.objects.create(test=self.test, created_by=self.user)
        s = str(batch)
        self.assertIn("ScanBatch", s)
        self.assertIn("queued", s)


class ScanJobModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.test = make_test(self.user)
        self.omr_sheet = make_omr_sheet(self.test)
        self.batch = ScanBatch.objects.create(test=self.test, created_by=self.user, total=1)

    def test_create_scan_job_defaults(self):
        job = ScanJob.objects.create(batch=self.batch)
        self.assertEqual(job.status, ScanJob.STATUS_QUEUED)
        self.assertEqual(job.page_no, 1)
        self.assertIsNone(job.omr_sheet)
        self.assertIsNone(job.confidence)
        self.assertEqual(job.error_reason, "")

    def test_scan_job_with_omr_sheet(self):
        job = ScanJob.objects.create(
            batch=self.batch,
            omr_sheet=self.omr_sheet,
            page_no=2,
            status=ScanJob.STATUS_NEEDS_REVIEW,
            confidence=0.72,
            error_reason="double_mark on q3",
        )
        self.assertEqual(job.omr_sheet, self.omr_sheet)
        self.assertEqual(job.page_no, 2)
        self.assertEqual(job.status, "needs_review")
        self.assertAlmostEqual(job.confidence, 0.72)
        self.assertEqual(job.error_reason, "double_mark on q3")

    def test_batch_jobs_reverse_relation(self):
        ScanJob.objects.create(batch=self.batch)
        ScanJob.objects.create(batch=self.batch, page_no=2)
        self.assertEqual(self.batch.jobs.count(), 2)

    def test_scan_job_str(self):
        job = ScanJob.objects.create(batch=self.batch)
        s = str(job)
        self.assertIn("ScanJob", s)
        self.assertIn("queued", s)

    def test_scan_job_omr_sheet_null_on_delete(self):
        """Deleting the OmrSheet sets ScanJob.omr_sheet to NULL (SET_NULL)."""
        job = ScanJob.objects.create(batch=self.batch, omr_sheet=self.omr_sheet)
        self.omr_sheet.delete()
        job.refresh_from_db()
        self.assertIsNone(job.omr_sheet)


class StudentResultModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.test = make_test(self.user)
        self.omr_sheet = make_omr_sheet(self.test)
        self.student = make_student(self.user)

    def test_create_student_result_defaults(self):
        result = StudentResult.objects.create(
            test=self.test,
            omr_sheet=self.omr_sheet,
        )
        self.assertEqual(result.score, 0)
        self.assertEqual(result.max_score, 0)
        self.assertEqual(result.correct_count, 0)
        self.assertEqual(result.wrong_count, 0)
        self.assertEqual(result.blank_count, 0)
        self.assertFalse(result.needs_review)
        self.assertIsNone(result.student)
        self.assertIsNotNone(result.graded_at)

    def test_create_student_result_with_scores(self):
        result = StudentResult.objects.create(
            test=self.test,
            student=self.student,
            omr_sheet=self.omr_sheet,
            score="8.50",
            max_score="10.00",
            correct_count=8,
            wrong_count=1,
            blank_count=1,
            needs_review=True,
        )
        self.assertEqual(str(result.score), "8.50")
        self.assertEqual(result.correct_count, 8)
        self.assertTrue(result.needs_review)
        self.assertEqual(result.student, self.student)

    def test_student_result_str(self):
        result = StudentResult.objects.create(test=self.test, omr_sheet=self.omr_sheet)
        s = str(result)
        self.assertIn("StudentResult", s)


class QuestionResponseModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.test = make_test(self.user)
        self.omr_sheet = make_omr_sheet(self.test)
        self.question = make_question(self.test)
        self.result = StudentResult.objects.create(test=self.test, omr_sheet=self.omr_sheet)

    def test_create_question_response_defaults(self):
        qr = QuestionResponse.objects.create(
            student_result=self.result,
            q_pos=1,
        )
        self.assertEqual(qr.marked_options, [])
        self.assertFalse(qr.is_correct)
        self.assertFalse(qr.flagged)
        self.assertIsNone(qr.question)

    def test_create_question_response_with_data(self):
        qr = QuestionResponse.objects.create(
            student_result=self.result,
            question=self.question,
            q_pos=1,
            marked_options=["A"],
            is_correct=True,
            flagged=False,
        )
        self.assertEqual(qr.marked_options, ["A"])
        self.assertTrue(qr.is_correct)
        self.assertEqual(qr.question, self.question)

    def test_responses_reverse_relation(self):
        QuestionResponse.objects.create(student_result=self.result, q_pos=1)
        QuestionResponse.objects.create(student_result=self.result, q_pos=2)
        self.assertEqual(self.result.responses.count(), 2)

    def test_question_response_str(self):
        qr = QuestionResponse.objects.create(student_result=self.result, q_pos=3)
        s = str(qr)
        self.assertIn("QuestionResponse", s)
        self.assertIn("3", s)


class ReviewItemModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.test = make_test(self.user)
        self.omr_sheet = make_omr_sheet(self.test)
        self.question = make_question(self.test)
        self.batch = ScanBatch.objects.create(test=self.test, created_by=self.user, total=1)
        self.scan_job = ScanJob.objects.create(batch=self.batch, omr_sheet=self.omr_sheet)

    def test_create_review_item_defaults(self):
        item = ReviewItem.objects.create(reason=ReviewItem.REASON_NO_QR)
        self.assertFalse(item.resolved)
        self.assertIsNone(item.scan_job)
        self.assertIsNone(item.omr_sheet)
        self.assertIsNone(item.question)
        self.assertIsNone(item.resolved_by)
        self.assertIsNone(item.resolution)
        self.assertIsNotNone(item.created_at)

    def test_create_review_item_full(self):
        item = ReviewItem.objects.create(
            scan_job=self.scan_job,
            omr_sheet=self.omr_sheet,
            question=self.question,
            reason=ReviewItem.REASON_DOUBLE_MARK,
            resolved=True,
            resolved_by=self.user,
            resolution={"marked_options": ["A"]},
        )
        self.assertEqual(item.reason, "double_mark")
        self.assertTrue(item.resolved)
        self.assertEqual(item.resolved_by, self.user)
        self.assertEqual(item.resolution, {"marked_options": ["A"]})

    def test_all_reason_choices(self):
        reasons = [
            ReviewItem.REASON_NO_QR,
            ReviewItem.REASON_ALIGNMENT,
            ReviewItem.REASON_ROLL_UNREADABLE,
            ReviewItem.REASON_DOUBLE_MARK,
            ReviewItem.REASON_FAINT,
            ReviewItem.REASON_MISSING_PAGE,
        ]
        for reason in reasons:
            item = ReviewItem.objects.create(reason=reason)
            self.assertEqual(item.reason, reason)

    def test_review_item_str(self):
        item = ReviewItem.objects.create(reason=ReviewItem.REASON_FAINT)
        s = str(item)
        self.assertIn("ReviewItem", s)
        self.assertIn("faint", s)


class FullChainTest(TestCase):
    """
    Integration test: create the complete model chain and assert all FK relations.
    Test → OmrSheet → ScanBatch → ScanJob
    Test → StudentResult → QuestionResponse
    ScanJob + OmrSheet + Question → ReviewItem
    """

    def test_full_chain(self):
        # Setup core entities
        user = make_user()
        test = make_test(user)
        question = make_question(test)
        student = make_student(user)

        # OMR sheet (child of test + student)
        sheet = make_omr_sheet(test)
        sheet.student = student
        sheet.save()

        # ScanBatch → ScanJob
        batch = ScanBatch.objects.create(
            test=test,
            created_by=user,
            status=ScanBatch.STATUS_PROCESSING,
            total=1,
        )
        job = ScanJob.objects.create(
            batch=batch,
            omr_sheet=sheet,
            page_no=1,
            status=ScanJob.STATUS_DONE,
            confidence=0.95,
        )

        # StudentResult → QuestionResponse
        result = StudentResult.objects.create(
            test=test,
            student=student,
            omr_sheet=sheet,
            score="9.00",
            max_score="10.00",
            correct_count=9,
            wrong_count=1,
            blank_count=0,
        )
        qr = QuestionResponse.objects.create(
            student_result=result,
            question=question,
            q_pos=1,
            marked_options=["B"],
            is_correct=False,
            flagged=True,
        )

        # ReviewItem links all
        review = ReviewItem.objects.create(
            scan_job=job,
            omr_sheet=sheet,
            question=question,
            reason=ReviewItem.REASON_DOUBLE_MARK,
        )

        # --- Assertions ---
        # ScanBatch
        self.assertEqual(batch.test, test)
        self.assertEqual(batch.created_by, user)
        self.assertEqual(test.scan_batches.count(), 1)

        # ScanJob via reverse relation
        self.assertEqual(batch.jobs.count(), 1)
        self.assertEqual(batch.jobs.first(), job)
        self.assertEqual(job.omr_sheet, sheet)
        self.assertEqual(sheet.scan_jobs.count(), 1)

        # StudentResult
        self.assertEqual(result.test, test)
        self.assertEqual(result.student, student)
        self.assertEqual(result.omr_sheet, sheet)
        self.assertEqual(sheet.student_results.count(), 1)

        # QuestionResponse
        self.assertEqual(qr.student_result, result)
        self.assertEqual(result.responses.count(), 1)
        self.assertEqual(qr.question, question)
        self.assertTrue(qr.flagged)

        # ReviewItem
        self.assertEqual(review.scan_job, job)
        self.assertEqual(review.omr_sheet, sheet)
        self.assertEqual(review.question, question)
        self.assertEqual(job.review_items.count(), 1)
        self.assertEqual(sheet.review_items.count(), 1)
        self.assertFalse(review.resolved)
