"""
Tests for Phase 2B: per-student report card PDF generation + endpoints.

Covers:
1. student_report_card() returns valid PDF bytes (starts %PDF) for a graded cohort.
2. bulk_report_cards() returns a multi-student PDF for a graded cohort.
3. GET /api/v1/analytics/test/<id>/student/<id>/report-card/ — auth, 200, valid PDF,
   scope-security (different user gets 404).
4. GET /api/v1/analytics/test/<id>/report-cards/ — same security checks + valid PDF.
5. Graceful handling when cohort is too small for percentile/rank (no StudentProfile).
6. Empty cohort: bulk PDF is still valid (no crash).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from assessments.models import ClassGroup, MarkingScheme, Option, Question, Test
from omr.models import OmrSheet
from results.models import QuestionResponse, StudentResult
from rosters.models import Roster, Student

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixture helpers (mirrors tests_analytics.py style)
# ---------------------------------------------------------------------------

def _make_user(email="rc_teacher@test.com", password="pass1234"):
    return User.objects.create_user(email=email, password=password)


def _make_test(user, title="RC Test"):
    cg = ClassGroup.objects.create(user=user, created_by=user, name=f"CG-{title}")
    t = Test.objects.create(
        user=user, created_by=user, class_group=cg,
        title=title, subject="Science",
    )
    MarkingScheme.objects.create(test=t, marks_per_correct=1)
    return t


def _make_questions(test, n=4):
    """Create n questions each with 4 options (A correct). Topics alternate Topic1/Topic2."""
    questions = []
    for i in range(n):
        q = Question.objects.create(
            test=test,
            order_index=i,
            text=f"Question {i + 1} text",
            topic=f"Topic {(i % 2) + 1}",
        )
        for label in ["A", "B", "C", "D"]:
            Option.objects.create(question=q, label=label, text=label, is_correct=(label == "A"))
        questions.append(q)
    return questions


def _make_student(user, roll="RC001", name="RC Student"):
    roster, _ = Roster.objects.get_or_create(user=user, created_by=user, name="RC-Roster")
    return Student.objects.create(roster=roster, roll_number=roll, full_name=name)


def _make_omr_sheet(test, questions, seed=1, prefix="RC"):
    q_ids = [q.id for q in questions]
    option_order = {str(q.id): ["A", "B", "C", "D"] for q in questions}
    answer_key = {str(i): ["A"] for i in range(len(questions))}
    return OmrSheet.objects.create(
        test=test,
        sheet_code=f"{prefix}-SHEET-{seed:04d}",
        human_readable_code=f"{prefix}{seed:04d}",
        question_order=q_ids,
        option_order=option_order,
        answer_key=answer_key,
        page_count=1,
        shuffle_version=seed,
    )


def _make_result(test, student, omr_sheet, score, max_score=4,
                 correct=0, wrong=0, blank=0):
    return StudentResult.objects.create(
        test=test, student=student, omr_sheet=omr_sheet,
        score=Decimal(str(score)), max_score=Decimal(str(max_score)),
        correct_count=correct, wrong_count=wrong, blank_count=blank,
    )


def _make_qr(result, question, q_pos, marked, is_correct, flagged=False):
    return QuestionResponse.objects.create(
        student_result=result, question=question, q_pos=q_pos,
        marked_options=marked, is_correct=is_correct, flagged=flagged,
    )


def _build_graded_cohort(user, test, questions, n_students=4, seed_offset=100):
    """
    Build n_students each with a full set of QuestionResponses.
    Student 0 gets all correct; others get progressively more wrong.
    Returns list of (student, result).
    seed_offset avoids sheet_code collisions across multiple calls.
    """
    pairs = []
    for i in range(n_students):
        roll = f"RC{seed_offset+i:04d}"
        name = f"Student {seed_offset + i}"
        student = _make_student(user, roll=roll, name=name)
        sheet = _make_omr_sheet(test, questions, seed=seed_offset + i, prefix=f"RC{seed_offset}")
        score = max(0, len(questions) - i)
        result = _make_result(
            test, student, sheet,
            score=score, max_score=len(questions),
            correct=score, wrong=len(questions) - score,
        )
        for q_idx, q in enumerate(questions):
            is_correct = (q_idx < score)
            _make_qr(result, q, q_idx, ["A"] if is_correct else ["B"], is_correct)
        pairs.append((student, result))
    return pairs


# ===========================================================================
# 1. Unit tests for report_card module functions
# ===========================================================================

class StudentReportCardBytesTest(TestCase):
    """student_report_card() returns valid PDF bytes."""

    def setUp(self):
        self.user = User.objects.create_user(email="rc1@test.com", password="pass1234")
        self.test = _make_test(self.user, "RC Unit Test")
        self.questions = _make_questions(self.test, n=4)
        pairs = _build_graded_cohort(self.user, self.test, self.questions, n_students=4)
        self.student, self.result = pairs[0]

    def test_returns_pdf_bytes(self):
        from analytics.report_card import student_report_card
        pdf = student_report_card(self.test, self.result)
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 100)
        self.assertTrue(pdf.startswith(b"%PDF"), "Output must start with %PDF")

    def test_valid_for_student_with_wrong_answers(self):
        """Student with both correct and wrong answers — still produces valid PDF."""
        from analytics.report_card import student_report_card
        # Build a new test+cohort for this sub-test to avoid roll-number/sheet collision.
        user2 = User.objects.create_user(email="rc1b@test.com", password="pass1234")
        test2 = _make_test(user2, "RC Unit Test 2")
        qs2 = _make_questions(test2, n=4)
        pairs = _build_graded_cohort(user2, test2, qs2, n_students=2, seed_offset=900)
        _, result2 = pairs[1]
        pdf = student_report_card(test2, result2)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_no_student_profile_small_cohort(self):
        """When StudentProfile is absent (small cohort), PDF still generates without crash."""
        from analytics.report_card import student_report_card
        # No StudentProfile rows exist — the function should degrade gracefully.
        from analytics.models import StudentProfile
        StudentProfile.objects.filter(test=self.test).delete()
        pdf = student_report_card(self.test, self.result)
        self.assertTrue(pdf.startswith(b"%PDF"))


class BulkReportCardsBytesTest(TestCase):
    """bulk_report_cards() returns valid combined PDF bytes."""

    def setUp(self):
        self.user = User.objects.create_user(email="rc2@test.com", password="pass1234")
        self.test = _make_test(self.user, "RC Bulk Test")
        self.questions = _make_questions(self.test, n=4)

    def test_bulk_pdf_valid(self):
        from analytics.report_card import bulk_report_cards
        _build_graded_cohort(self.user, self.test, self.questions, n_students=3)
        pdf = bulk_report_cards(self.test)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"), "Bulk PDF must start with %PDF")
        self.assertGreater(len(pdf), 100)

    def test_empty_cohort_does_not_crash(self):
        """Empty cohort (no results) should return a valid PDF, not crash."""
        from analytics.report_card import bulk_report_cards
        pdf = bulk_report_cards(self.test)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"))


# ===========================================================================
# 2. Endpoint — individual report card
# ===========================================================================

class StudentReportCardEndpointTest(TestCase):
    """GET /api/v1/analytics/test/<id>/student/<id>/report-card/"""

    def setUp(self):
        self.user = User.objects.create_user(email="rc3@test.com", password="pass1234")
        self.other_user = User.objects.create_user(email="rc3other@test.com", password="pass1234")
        self.test = _make_test(self.user, "RC Endpoint Test")
        self.questions = _make_questions(self.test, n=4)
        pairs = _build_graded_cohort(self.user, self.test, self.questions, n_students=2)
        self.student, self.result = pairs[0]
        self.client = APIClient()

    def _url(self, test_id=None, student_id=None):
        test_id = test_id or self.test.id
        student_id = student_id or self.student.id
        return reverse(
            "analytics-student-report-card",
            kwargs={"test_id": test_id, "student_id": student_id},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self._url())
        self.assertIn(resp.status_code, [401, 403])

    def test_authenticated_owner_gets_200_valid_pdf(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        pdf_bytes = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Response must be a valid PDF")
        self.assertIn("attachment", resp.get("Content-Disposition", ""))

    def test_wrong_user_gets_404(self):
        """A different user cannot access this test's report card."""
        self.client.force_authenticate(self.other_user)
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_student_gets_404(self):
        """A student that has no result for this test returns 404."""
        self.client.force_authenticate(self.user)
        resp = self.client.get(self._url(student_id=99999))
        self.assertEqual(resp.status_code, 404)


# ===========================================================================
# 3. Endpoint — bulk report cards
# ===========================================================================

class BulkReportCardsEndpointTest(TestCase):
    """GET /api/v1/analytics/test/<id>/report-cards/"""

    def setUp(self):
        self.user = User.objects.create_user(email="rc4@test.com", password="pass1234")
        self.other_user = User.objects.create_user(email="rc4other@test.com", password="pass1234")
        self.test = _make_test(self.user, "RC Bulk Endpoint Test")
        self.questions = _make_questions(self.test, n=4)
        _build_graded_cohort(self.user, self.test, self.questions, n_students=3)
        self.client = APIClient()

    def _url(self, test_id=None):
        return reverse(
            "analytics-bulk-report-cards",
            kwargs={"test_id": test_id or self.test.id},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self._url())
        self.assertIn(resp.status_code, [401, 403])

    def test_authenticated_owner_gets_200_valid_pdf(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        pdf_bytes = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Bulk response must be a valid PDF")
        self.assertIn("attachment", resp.get("Content-Disposition", ""))

    def test_wrong_user_gets_404(self):
        self.client.force_authenticate(self.other_user)
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 404)


# ===========================================================================
# 4. Graceful handling for small cohort (no StudentProfile)
# ===========================================================================

class SmallCohortGracefulTest(TestCase):
    """
    When there is only 1 student (too small for psychometrics), StudentProfile
    will not exist. PDF must still generate without crashing and start with %PDF.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="rc5@test.com", password="pass1234")
        self.test = _make_test(self.user, "RC Small Cohort")
        self.questions = _make_questions(self.test, n=3)
        pairs = _build_graded_cohort(self.user, self.test, self.questions, n_students=1)
        self.student, self.result = pairs[0]

    def test_pdf_generated_without_profile(self):
        from analytics.report_card import student_report_card
        from analytics.models import StudentProfile
        # Ensure no profile exists
        StudentProfile.objects.filter(test=self.test).delete()
        pdf = student_report_card(self.test, self.result)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_endpoint_200_without_profile(self):
        from analytics.models import StudentProfile
        StudentProfile.objects.filter(test=self.test).delete()
        client = APIClient()
        client.force_authenticate(self.user)
        url = reverse(
            "analytics-student-report-card",
            kwargs={"test_id": self.test.id, "student_id": self.student.id},
        )
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        pdf_bytes = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
