"""
TDD tests for Phase 5, Task 1: test-level analytics endpoint (shuffle-correct).

Tests cover:
1. QuestionResponse.question is populated by the pipeline grading tweak.
2. test_summary() computations: average, median, distribution, toppers.
3. A question everyone got wrong tops hardest_questions.
4. option_distribution maps printed→original labels correctly under an option shuffle.
5. GET /api/v1/analytics/test/{test_id}/ endpoint (auth, 200, shape, cross-tenant 404).
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
# Shared helpers
# ---------------------------------------------------------------------------

def _make_user(email="teacher@test.com", password="pass1234"):
    return User.objects.create_user(email=email, password=password)


def _make_test(user, title="Analytics Test"):
    cg = ClassGroup.objects.create(user=user, created_by=user, name="CG-Analytics")
    t = Test.objects.create(
        user=user, created_by=user, class_group=cg,
        title=title, subject="Math",
    )
    MarkingScheme.objects.create(test=t, marks_per_correct=1)
    return t


def _make_questions(test, n=3):
    """Create n questions each with 4 options (A correct)."""
    questions = []
    for i in range(n):
        q = Question.objects.create(
            test=test,
            order_index=i,
            text=f"Question {i+1}",
            topic=f"Topic {(i % 2) + 1}",
        )
        for label in ["A", "B", "C", "D"]:
            Option.objects.create(
                question=q, label=label, text=label, is_correct=(label == "A")
            )
        questions.append(q)
    return questions


def _make_student(user, roll="001", name="Student One"):
    roster, _ = Roster.objects.get_or_create(user=user, created_by=user, name="Roster-A")
    return Student.objects.create(roster=roster, roll_number=roll, full_name=name)


def _make_omr_sheet(test, questions, seed=1):
    """Build an OmrSheet with identity shuffle (question_order and option_order)."""
    q_ids = [q.id for q in questions]
    option_order = {str(q.id): ["A", "B", "C", "D"] for q in questions}
    # answer_key: printed position → [correct printed labels] (same as original, no shuffle)
    answer_key = {str(i): ["A"] for i in range(len(questions))}
    return OmrSheet.objects.create(
        test=test,
        sheet_code=f"SHEET-{seed:04d}",
        human_readable_code=f"S{seed:04d}",
        question_order=q_ids,
        option_order=option_order,
        answer_key=answer_key,
        page_count=1,
        shuffle_version=seed,
    )


def _make_omr_sheet_shuffled(test, questions, seed=99):
    """
    Build an OmrSheet with a KNOWN option shuffle on question[0]:
        question[0] original labels: A B C D
        shuffled (printed) order:    B A D C
    So printed label 'A' (printed pos 1) corresponds to original 'B'.
    And printed label 'B' (printed pos 0) corresponds to original 'A' (correct).
    """
    q_ids = [q.id for q in questions]
    q0_id = str(questions[0].id)
    # question[0]: printed order is [B, A, D, C]
    # question[1], question[2]: identity
    option_order = {str(q.id): ["A", "B", "C", "D"] for q in questions}
    option_order[q0_id] = ["B", "A", "D", "C"]
    # answer key: pos 0 → correct printed label is 'B' (maps to original 'A')
    # for positions 1 and 2: 'A' is still correct (identity shuffle)
    answer_key = {"0": ["B"], "1": ["A"], "2": ["A"]}
    return OmrSheet.objects.create(
        test=test,
        sheet_code=f"SHEET-SHF-{seed:04d}",
        human_readable_code=f"SS{seed:04d}",
        question_order=q_ids,
        option_order=option_order,
        answer_key=answer_key,
        page_count=1,
        shuffle_version=seed,
    )


def _make_result(test, student, omr_sheet, score, max_score=3,
                 correct=0, wrong=0, blank=0, needs_review=False):
    return StudentResult.objects.create(
        test=test,
        student=student,
        omr_sheet=omr_sheet,
        score=Decimal(str(score)),
        max_score=Decimal(str(max_score)),
        correct_count=correct,
        wrong_count=wrong,
        blank_count=blank,
        needs_review=needs_review,
    )


def _make_qr(result, question, q_pos, marked, is_correct, flagged=False):
    return QuestionResponse.objects.create(
        student_result=result,
        question=question,
        q_pos=q_pos,
        marked_options=marked,
        is_correct=is_correct,
        flagged=flagged,
    )


# ===========================================================================
# 1. Pipeline grading tweak: QuestionResponse.question FK is populated
# ===========================================================================

class PipelineQuestionFKTest(TestCase):
    """
    Test that _maybe_grade sets QuestionResponse.question from
    omr_sheet.question_order[q_pos].

    We build a minimal DB fixture and call _maybe_grade via the pipeline
    helper simulate_correct_marks + grade_sheet, then directly call
    _maybe_grade to avoid the full image pipeline.
    """

    def _build_fixtures(self):
        user = _make_user("pipeline@test.com")
        test = _make_test(user)
        questions = _make_questions(test, n=3)
        student = _make_student(user, "P001", "Pipeline Student")
        sheet = _make_omr_sheet(test, questions, seed=500)
        sheet.student = student
        sheet.save()
        return user, test, questions, student, sheet

    def test_question_fk_set_on_grading(self):
        """
        After _maybe_grade runs, each QuestionResponse.question_id must
        equal the underlying Question id from omr_sheet.question_order[q_pos].
        """
        from omr.models import ScanBatch, ScanJob
        from omr.scan.pipeline import _maybe_grade

        user, test, questions, student, sheet = self._build_fixtures()

        # Create a ScanBatch + ScanJob with pre-filled reads (all correct)
        batch = ScanBatch.objects.create(test=test, created_by=user, total=1)
        job = ScanJob.objects.create(
            batch=batch,
            omr_sheet=sheet,
            page_no=1,
            status=ScanJob.STATUS_DONE,
            reads={
                "answers": {
                    "0": {"marked": ["A"], "flag": None},
                    "1": {"marked": ["A"], "flag": None},
                    "2": {"marked": ["A"], "flag": None},
                },
                "roll": "P001",
                "flags": [],
            },
        )

        _maybe_grade(sheet)

        result = StudentResult.objects.get(omr_sheet=sheet)
        responses = list(result.responses.order_by("q_pos"))
        self.assertEqual(len(responses), 3)

        for resp in responses:
            q_pos = resp.q_pos
            expected_question_id = sheet.question_order[q_pos]
            self.assertIsNotNone(
                resp.question_id,
                f"QuestionResponse at q_pos={q_pos} should have question set",
            )
            self.assertEqual(
                resp.question_id,
                expected_question_id,
                f"q_pos={q_pos}: expected question_id={expected_question_id}, "
                f"got {resp.question_id}",
            )


# ===========================================================================
# 2. test_summary() pure-function tests
# ===========================================================================

class TestSummaryServiceTest(TestCase):
    """Tests for analytics.services.test_summary(test)."""

    def setUp(self):
        self.user = _make_user("summary@test.com")
        self.test = _make_test(self.user)
        self.questions = _make_questions(self.test, n=3)

    def _build_scenario(self):
        """
        Create 4 students with scores 3, 2, 1, 0 out of 3:
          - student A: score=3, all correct
          - student B: score=2, q0 wrong, q1 correct, q2 correct
          - student C: score=1, q0 wrong, q1 wrong, q2 correct
          - student D: score=0, all wrong
        """
        students = []
        sheets = []
        results = []
        for i, (score, name, roll) in enumerate([
            (3, "Alice", "001"),
            (2, "Bob", "002"),
            (1, "Carol", "003"),
            (0, "Dan", "004"),
        ]):
            s = _make_student(self.user, roll, name)
            sheet = _make_omr_sheet(self.test, self.questions, seed=i + 10)
            sheet.student = s
            sheet.save()
            correct = score
            wrong = 3 - score
            r = _make_result(
                self.test, s, sheet, score, max_score=3,
                correct=correct, wrong=wrong, blank=0,
            )
            # QuestionResponse rows — all correct up to `score` questions
            for q_idx, q in enumerate(self.questions):
                is_correct = (q_idx < score)
                marked = ["A"] if is_correct else ["B"]
                _make_qr(r, q, q_idx, marked, is_correct)
            students.append(s)
            sheets.append(sheet)
            results.append(r)
        return students, sheets, results

    def test_n_students_and_graded(self):
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        self.assertEqual(summary["n_students"], 4)
        self.assertEqual(summary["graded"], 4)

    def test_needs_review_count(self):
        from analytics.services import test_summary
        students, sheets, results = self._build_scenario()
        # Mark first result as needs_review
        results[0].needs_review = True
        results[0].save()
        summary = test_summary(self.test)
        self.assertEqual(summary["needs_review_count"], 1)

    def test_average(self):
        from analytics.services import test_summary
        self._build_scenario()
        # scores: 3, 2, 1, 0 → average = 6/4 = 1.5
        summary = test_summary(self.test)
        self.assertAlmostEqual(float(summary["average"]), 1.5, places=4)

    def test_median(self):
        from analytics.services import test_summary
        self._build_scenario()
        # sorted scores: 0, 1, 2, 3 → median = (1+2)/2 = 1.5
        summary = test_summary(self.test)
        self.assertAlmostEqual(float(summary["median"]), 1.5, places=4)

    def test_max_and_min(self):
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        self.assertEqual(float(summary["max"]), 3.0)
        self.assertEqual(float(summary["min"]), 0.0)

    def test_max_score(self):
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        self.assertEqual(float(summary["max_score"]), 3.0)

    def test_distribution_bucket_counts(self):
        """
        Scores: 3, 2, 1, 0 with max=3.
        Percentages: 100%, 66.7%, 33.3%, 0%
        Expected buckets:
          0-20%:  1 (score=0 → 0%)
          21-40%: 1 (score=1 → 33.3%)
          41-60%: 0
          61-80%: 1 (score=2 → 66.7%)
          81-100%: 1 (score=3 → 100%)
        """
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        dist = {b["bucket"]: b["count"] for b in summary["distribution"]}
        self.assertEqual(dist["0-20%"], 1)
        self.assertEqual(dist["21-40%"], 1)
        self.assertEqual(dist["41-60%"], 0)
        self.assertEqual(dist["61-80%"], 1)
        self.assertEqual(dist["81-100%"], 1)

    def test_toppers_top5_by_score(self):
        """toppers should be sorted descending by score, max 5 entries."""
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        toppers = summary["toppers"]
        self.assertLessEqual(len(toppers), 5)
        # First topper should have score=3
        self.assertEqual(float(toppers[0]["score"]), 3.0)
        # Ensure descending order
        scores = [float(t["score"]) for t in toppers]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_toppers_include_roll_and_name(self):
        """Each topper entry must include student roll and name."""
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        for t in summary["toppers"]:
            self.assertIn("student", t)
            self.assertIn("roll", t["student"])
            self.assertIn("name", t["student"])

    def test_hardest_questions_most_missed_is_first(self):
        """
        The question everyone got wrong (Dan got all wrong, Carol got 2 wrong,
        Bob got 1 wrong) is question[0].
        wrong_rate for q[0]: wrong=3 (Alice+Carol+Dan); n=4 → 3/4=0.75
        wrong_rate for q[1]: wrong=2 (Carol+Dan);       n=4 → 2/4=0.50
        wrong_rate for q[2]: wrong=1 (Dan);              n=4 → 1/4=0.25
        """
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        hq = summary["hardest_questions"]
        self.assertGreater(len(hq), 0)
        # Top entry should be the most-missed question
        self.assertAlmostEqual(float(hq[0]["wrong_rate"]), 0.75, places=4)
        # Ensure descending order
        rates = [float(h["wrong_rate"]) for h in hq]
        self.assertEqual(rates, sorted(rates, reverse=True))

    def test_hardest_questions_include_text_and_order_index(self):
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        for h in summary["hardest_questions"]:
            self.assertIn("question_id", h)
            self.assertIn("text", h)
            self.assertIn("order_index", h)
            self.assertIn("wrong_rate", h)
            self.assertIn("n", h)

    def test_empty_test_no_results(self):
        """test_summary on a test with no StudentResults returns sane defaults."""
        from analytics.services import test_summary
        summary = test_summary(self.test)
        self.assertEqual(summary["n_students"], 0)
        self.assertEqual(summary["graded"], 0)
        self.assertIsNone(summary["average"])
        self.assertIsNone(summary["median"])
        self.assertIsNone(summary["max"])
        self.assertIsNone(summary["min"])
        self.assertEqual(summary["toppers"], [])
        self.assertEqual(summary["hardest_questions"], [])

    def test_distribution_has_five_buckets(self):
        from analytics.services import test_summary
        self._build_scenario()
        summary = test_summary(self.test)
        self.assertEqual(len(summary["distribution"]), 5)
        bucket_names = [b["bucket"] for b in summary["distribution"]]
        self.assertEqual(
            bucket_names,
            ["0-20%", "21-40%", "41-60%", "61-80%", "81-100%"],
        )


# ===========================================================================
# 3. option_distribution: printed→original mapping under option shuffle
# ===========================================================================

class OptionDistributionTest(TestCase):
    """
    Verifies that option_distribution correctly maps printed marked labels
    to original labels via option_order, even when options are shuffled.

    Sheet layout for student 1 (SHUFFLED):
        question[0]: option_order = ["B", "A", "D", "C"]
            → printed 'A' == original 'B', printed 'B' == original 'A' (correct)
        question[1], [2]: identity (no shuffle)

    Student marks printed 'A' on question[0] — which maps to original 'B' (wrong).
    option_distribution['A'] for q[0] should be 0 (no one marked original 'A'),
    option_distribution['B'] for q[0] should be 1 (one person's 'printed A' = original 'B').
    """

    def setUp(self):
        self.user = _make_user("optdist@test.com")
        self.test = _make_test(self.user)
        self.questions = _make_questions(self.test, n=3)

    def _build_shuffled_scenario(self):
        student = _make_student(self.user, "S01", "Shuffled Student")
        sheet = _make_omr_sheet_shuffled(self.test, self.questions, seed=200)
        sheet.student = student
        sheet.save()
        result = _make_result(
            self.test, student, sheet,
            score=0, max_score=3, correct=0, wrong=3,
        )
        # Student marks PRINTED 'A' on q[0] (which is original 'B' — wrong)
        # Student marks PRINTED 'A' on q[1] (which is original 'A' — correct, identity)
        # Student marks PRINTED 'A' on q[2] (which is original 'A' — correct, identity)
        _make_qr(result, self.questions[0], 0, ["A"], is_correct=False)  # printed A → original B
        _make_qr(result, self.questions[1], 1, ["A"], is_correct=True)   # identity
        _make_qr(result, self.questions[2], 2, ["A"], is_correct=True)   # identity
        return student, sheet, result

    def test_option_distribution_maps_printed_to_original(self):
        from analytics.services import test_summary
        self._build_shuffled_scenario()
        summary = test_summary(self.test)
        opt_dist = summary["option_distribution"]

        # Find entry for question[0]
        q0_id = self.questions[0].id
        q0_entry = next((e for e in opt_dist if e["question_id"] == q0_id), None)
        self.assertIsNotNone(q0_entry, "option_distribution should have entry for question[0]")

        counts_by_label = {o["label"]: o["count"] for o in q0_entry["options"]}
        # Printed 'A' on q[0] in shuffled sheet → original 'B'
        self.assertEqual(
            counts_by_label.get("B", 0), 1,
            f"Original 'B' should have count=1 (one student's printed 'A' maps to it). "
            f"counts: {counts_by_label}",
        )
        # Original 'A' (correct) should have count=0 (nobody marked printed 'B')
        self.assertEqual(
            counts_by_label.get("A", 0), 0,
            f"Original 'A' (correct) should have count=0. counts: {counts_by_label}",
        )

    def test_option_distribution_includes_correct_labels(self):
        """Each option_distribution entry must have the correct original labels."""
        from analytics.services import test_summary
        self._build_shuffled_scenario()
        summary = test_summary(self.test)
        opt_dist = summary["option_distribution"]

        q0_id = self.questions[0].id
        q0_entry = next(e for e in opt_dist if e["question_id"] == q0_id)
        # Correct original label for q[0] is 'A'
        self.assertIn("A", q0_entry["correct"], f"correct labels should include 'A', got {q0_entry['correct']}")

    def test_option_distribution_identity_shuffle(self):
        """With identity shuffle, printed 'A' correctly counts as original 'A'."""
        from analytics.services import test_summary
        student = _make_student(self.user, "I01", "Identity Student")
        sheet = _make_omr_sheet(self.test, self.questions, seed=300)
        sheet.student = student
        sheet.save()
        result = _make_result(self.test, student, sheet, score=3, max_score=3, correct=3)
        for q_idx, q in enumerate(self.questions):
            _make_qr(result, q, q_idx, ["A"], is_correct=True)

        summary = test_summary(self.test)
        opt_dist = summary["option_distribution"]
        for q in self.questions:
            entry = next(e for e in opt_dist if e["question_id"] == q.id)
            counts = {o["label"]: o["count"] for o in entry["options"]}
            self.assertEqual(counts.get("A", 0), 1, f"q={q.id}: original 'A' count should be 1")


# ===========================================================================
# 4. API endpoint tests
# ===========================================================================

class AnalyticsEndpointTest(TestCase):
    """GET /api/v1/analytics/test/{test_id}/ endpoint tests."""

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user("api@test.com")
        self.test = _make_test(self.user)
        self.questions = _make_questions(self.test, n=3)

    def _auth(self, user=None):
        if user is None:
            user = self.user
        self.client.force_authenticate(user=user)

    def _url(self, test_id=None):
        if test_id is None:
            test_id = self.test.id
        return f"/api/v1/analytics/test/{test_id}/"

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cross_tenant_returns_404(self):
        """A test belonging to another user must return 404."""
        other_user = _make_user("other@test.com")
        other_test = _make_test(other_user)
        self._auth()
        response = self.client.get(self._url(other_test.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_test_returns_404(self):
        self._auth()
        response = self.client.get(self._url(99999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_owner_returns_200(self):
        self._auth()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_has_required_top_level_keys(self):
        self._auth()
        response = self.client.get(self._url())
        data = response.json()
        for key in ("test", "n_students", "graded", "needs_review_count",
                    "average", "median", "max", "min", "max_score",
                    "distribution", "toppers", "hardest_questions",
                    "option_distribution"):
            self.assertIn(key, data, f"Top-level key {key!r} missing from response")

    def test_response_test_block(self):
        """The 'test' block should contain id, title, subject, attempt_number."""
        self._auth()
        response = self.client.get(self._url())
        data = response.json()
        t_block = data["test"]
        for key in ("id", "title", "subject", "attempt_number"):
            self.assertIn(key, t_block, f"test block missing key {key!r}")
        self.assertEqual(t_block["id"], self.test.id)
        self.assertEqual(t_block["title"], self.test.title)

    def test_response_with_results(self):
        """End-to-end: populated test returns correct average."""
        # Create two students with scores 3 and 1
        for i, (score, roll, name) in enumerate([(3, "T01", "Top"), (1, "T02", "Low")]):
            s = _make_student(self.user, roll, name)
            sheet = _make_omr_sheet(self.test, self.questions, seed=i + 100)
            sheet.student = s
            sheet.save()
            r = _make_result(self.test, s, sheet, score, max_score=3)
            for q_idx, q in enumerate(self.questions):
                is_correct = q_idx < score
                _make_qr(r, q, q_idx, ["A"] if is_correct else ["B"], is_correct)

        self._auth()
        response = self.client.get(self._url())
        data = response.json()
        self.assertEqual(data["n_students"], 2)
        # average = (3+1)/2 = 2.0
        self.assertAlmostEqual(float(data["average"]), 2.0, places=2)
        self.assertEqual(len(data["distribution"]), 5)
        self.assertLessEqual(len(data["toppers"]), 5)

    def test_distribution_is_list_of_dicts_with_bucket_count(self):
        self._auth()
        response = self.client.get(self._url())
        data = response.json()
        for item in data["distribution"]:
            self.assertIn("bucket", item)
            self.assertIn("count", item)

    def test_toppers_max_5(self):
        """Even with 10 students, toppers list is capped at 5."""
        for i in range(10):
            s = _make_student(self.user, f"{i+10:03d}", f"S{i}")
            sheet = _make_omr_sheet(self.test, self.questions, seed=i + 200)
            sheet.student = s
            sheet.save()
            r = _make_result(self.test, s, sheet, i % 4, max_score=3)
            for q_idx, q in enumerate(self.questions):
                _make_qr(r, q, q_idx, ["A"], is_correct=True)

        self._auth()
        response = self.client.get(self._url())
        data = response.json()
        self.assertLessEqual(len(data["toppers"]), 5)
