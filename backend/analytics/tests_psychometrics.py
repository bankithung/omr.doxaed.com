"""
TDD tests for Phase 2A: psychometric analytical profile engine.

Covers:
1. Golden-number tests: hand-computed exact expected values for difficulty,
   discrimination, point-biserial, KR-20.
2. Degenerate-cohort tests: 1 student / all-correct / zero-variance — no crash,
   correct insufficient_sample markers.
3. Percentile + rank computation.
4. Profile auto-populates after a scan batch completes (eager task).
5. Profile endpoint returns the profile (GET /api/v1/analytics/test/<id>/profile/).
6. Distractor analysis flags.
7. Existing analytics endpoints still pass (smoke test).

GOLDEN-NUMBER DERIVATIONS
--------------------------
10-student fixture (CANONICAL, n >= MIN_COHORT_FOR_PSYCHOMETRICS = 10)
  Students and item scores (3 items):
    S0: [1,1,1]  score=3
    S1: [1,1,1]  score=3
    S2: [1,1,0]  score=2
    S3: [1,1,0]  score=2
    S4: [1,0,0]  score=1
    S5: [1,0,0]  score=1
    S6: [0,1,0]  score=1
    S7: [0,0,0]  score=0
    S8: [0,0,0]  score=0
    S9: [0,0,0]  score=0

  Difficulty:
    item0: 6/10 = 0.6
    item1: 5/10 = 0.5
    item2: 2/10 = 0.2

  Discrimination (floor(0.27*10)=2 per group):
    Upper 2 (scores 3,3): item=[1,1,1],[1,1,1] → p_upper=1.0
    Lower 2 (scores 0,0): item=[0,0,0],[0,0,0] → p_lower=0.0
    D(item0)=D(item1)=D(item2) = 1.0 - 0.0 = 1.0

  KR-20:
    scores=[3,3,2,2,1,1,1,0,0,0], mean=1.3
    var_T = [(3-1.3)^2*2+(2-1.3)^2*2+(1-1.3)^2*3+(0-1.3)^2*3]/10
          = [5.78+0.98+0.27+5.07]/10 = 12.10/10 = 1.21
    sum(p*q)=0.6*0.4+0.5*0.5+0.2*0.8=0.24+0.25+0.16=0.65
    KR20=(3/2)*(1-0.65/1.21)=(1.5)*(1-0.53719...)=1.5*0.46281...=0.69421...

  Point-biserial for item0:
    rest_scores=[2,2,1,1,0,0,1,0,0,0]  (total minus item0)
    M1(correct, 6 students)=[2,2,1,1,0,0] → 6/6=1.0
    M0(wrong, 4 students)=[1,0,0,0] → 1/4=0.25
    var_rest:
      (2-0.7)^2*2=1.69*2=3.38; (1-0.7)^2*3=0.09*3=0.27;
      (0-0.7)^2*5=0.49*5=2.45; total=6.10; var=0.61
    sd_rest=sqrt(0.61)=0.78102...
    r_pb=(1.0-0.25)/0.78102*sqrt(0.6*0.4)=0.75/0.78102*0.48990...=0.47044...
"""

import math
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from assessments.models import ClassGroup, MarkingScheme, Option, Question, Test
from omr.models import OmrSheet, ScanBatch, ScanJob
from results.models import QuestionResponse, StudentResult
from rosters.models import Roster, Student
from analytics.psychometrics import (
    MIN_COHORT_FOR_PSYCHOMETRICS,
    item_difficulty,
    item_discrimination,
    point_biserial,
    kr20,
    percentile_rank,
    distractor_analysis,
    compute_test_profile,
    build_results_data,
)
from analytics.models import TestProfile, StudentProfile
from analytics.tasks import recompute_test_profile

User = get_user_model()

# ---------------------------------------------------------------------------
# Tolerance for float comparisons
# ---------------------------------------------------------------------------
TOLS = dict(places=4)  # assertEqual(round(v, 4), ...)


def _round4(v):
    if v is None:
        return None
    return round(v, 4)


# ---------------------------------------------------------------------------
# Shared helpers (mirrors tests_analytics.py helpers)
# ---------------------------------------------------------------------------

def _make_user(email="psych@test.com", password="pass1234"):
    return User.objects.create_user(email=email, password=password)


def _make_test(user, title="Psych Test"):
    cg = ClassGroup.objects.create(user=user, created_by=user, name=f"CG-{title}")
    t = Test.objects.create(
        user=user, created_by=user, class_group=cg,
        title=title, subject="Math",
    )
    MarkingScheme.objects.create(test=t, marks_per_correct=1)
    return t


def _make_questions(test, n=3):
    questions = []
    for i in range(n):
        q = Question.objects.create(
            test=test, order_index=i, text=f"Q{i+1}", topic="Topic1",
        )
        for label in ["A", "B", "C", "D"]:
            Option.objects.create(
                question=q, label=label, text=label, is_correct=(label == "A"),
            )
        questions.append(q)
    return questions


def _make_student(user, roll, name="Student"):
    roster, _ = Roster.objects.get_or_create(
        user=user, created_by=user, name="Roster-Psych"
    )
    return Student.objects.create(roster=roster, roll_number=roll, full_name=name)


def _make_omr_sheet(test, questions, seed=1, student=None):
    """Identity shuffle sheet."""
    q_ids = [str(q.id) for q in questions]
    option_order = {str(q.id): ["A", "B", "C", "D"] for q in questions}
    answer_key = {str(i): ["A"] for i in range(len(questions))}
    sheet = OmrSheet.objects.create(
        test=test,
        sheet_code=f"PSYCH-{seed:06d}",
        human_readable_code=f"P{seed:04d}",
        question_order=q_ids,
        option_order=option_order,
        answer_key=answer_key,
        page_count=1,
        shuffle_version=seed,
    )
    if student:
        sheet.student = student
        sheet.save(update_fields=["student"])
    return sheet


def _make_result_with_responses(test, student, sheet, item_scores, max_score=3):
    """
    Create a StudentResult + QuestionResponse rows from item_scores (list of 0/1).
    Correct answer is 'A'; wrong answer is 'B'; blank is [].
    """
    score = sum(item_scores)
    sr = StudentResult.objects.create(
        test=test,
        student=student,
        omr_sheet=sheet,
        score=Decimal(str(score)),
        max_score=Decimal(str(max_score)),
        correct_count=score,
        wrong_count=sum(1 for x in item_scores if x == 0),
        blank_count=0,
    )
    q_order = sheet.question_order
    for pos, correct in enumerate(item_scores):
        q_id = q_order[pos] if pos < len(q_order) else None
        marked = ["A"] if correct else ["B"]
        QuestionResponse.objects.create(
            student_result=sr,
            question_id=q_id,
            q_pos=pos,
            marked_options=marked,
            is_correct=bool(correct),
        )
    return sr


# ---------------------------------------------------------------------------
# 1. Golden-number tests: pure functions
# ---------------------------------------------------------------------------

class DifficultyGoldenTest(TestCase):
    """Difficulty (p-value) golden-number assertions."""

    def test_all_correct(self):
        """p = 1.0 when everyone correct."""
        self.assertEqual(item_difficulty([1, 1, 1, 1, 1]), 1.0)

    def test_all_wrong(self):
        """p = 0.0 when nobody correct."""
        self.assertEqual(item_difficulty([0, 0, 0, 0, 0]), 0.0)

    def test_partial(self):
        """p = 6/10 = 0.6 for item0 in canonical fixture."""
        # item0: S0..S5 correct (6), S6..S9 wrong (4)
        col = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
        self.assertAlmostEqual(item_difficulty(col), 0.6, places=10)

    def test_empty(self):
        """Empty list → None."""
        self.assertIsNone(item_difficulty([]))

    def test_item2_golden(self):
        """item2 (S0,S1 correct) = 2/10 = 0.2."""
        col = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        self.assertAlmostEqual(item_difficulty(col), 0.2, places=10)


class DiscriminationGoldenTest(TestCase):
    """Discrimination (upper-lower 27%) golden-number assertions."""

    def _scores(self):
        return [3.0, 3.0, 2.0, 2.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]

    def test_discrimination_item0(self):
        """
        D(item0) = p_upper - p_lower = 1.0 - 0.0 = 1.0
        Upper 2 (score 3): item=[1,1]; p_upper=1.0
        Lower 2 (score 0): item=[0,0]; p_lower=0.0
        """
        col = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
        scores = self._scores()
        d = item_discrimination(col, scores, n=10)
        self.assertAlmostEqual(d, 1.0, places=10)

    def test_discrimination_below_threshold(self):
        """Below MIN_COHORT (n=9) → None (insufficient sample)."""
        col = [1, 1, 1, 0, 0, 0, 0, 0, 0]
        scores = [3.0, 2.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        d = item_discrimination(col, scores, n=9)
        self.assertIsNone(d)

    def test_discrimination_zero_variance_item(self):
        """All-correct item: upper=1, lower=1 → D=0."""
        col = [1] * 10
        scores = [3.0, 3.0, 2.0, 2.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
        d = item_discrimination(col, scores, n=10)
        self.assertAlmostEqual(d, 0.0, places=10)


class PointBiserialGoldenTest(TestCase):
    """Point-biserial golden-number assertions."""

    def _scores(self):
        return [3.0, 3.0, 2.0, 2.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]

    def test_point_biserial_item0(self):
        """
        r_pb(item0) ≈ 0.4704  (see module docstring for derivation).
        rest_scores for item0: [2,2,1,1,0,0,1,0,0,0]
        M1=1.0, M0=0.25, sd=sqrt(0.61)=0.78102...
        r_pb=0.75/0.78102*sqrt(0.24)=0.47044...
        """
        col  = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
        scores = self._scores()
        pb = point_biserial(col, scores, n=10)
        self.assertAlmostEqual(pb, 0.4704, places=3)

    def test_point_biserial_zero_variance_item(self):
        """All-correct item → None (p=1.0, q=0.0)."""
        col = [1] * 10
        scores = self._scores()
        pb = point_biserial(col, scores, n=10)
        self.assertIsNone(pb)

    def test_point_biserial_below_threshold(self):
        """n < MIN_COHORT → None."""
        col    = [1, 1, 0, 0, 0, 0, 0, 0, 0]
        scores = [3.0]*2 + [0.0]*7
        pb = point_biserial(col, scores, n=9)
        self.assertIsNone(pb)


class KR20GoldenTest(TestCase):
    """KR-20 golden-number assertions."""

    def _canonical_fixture(self):
        """
        10 students, 3 items:
          S0:[1,1,1] S1:[1,1,1] S2:[1,1,0] S3:[1,1,0]
          S4:[1,0,0] S5:[1,0,0] S6:[0,1,0]
          S7:[0,0,0] S8:[0,0,0] S9:[0,0,0]
        """
        matrix = [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 0],
            [1, 1, 0],
            [1, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        scores = [sum(row) for row in matrix]
        return matrix, scores

    def test_kr20_golden(self):
        """
        KR20 = (3/2) * (1 - 0.65/1.21) ≈ 0.6942
        var_T=1.21, sum_pq=0.65
        """
        matrix, scores = self._canonical_fixture()
        result = kr20(matrix, scores)
        self.assertIsNotNone(result)
        # Expected: (3/2)*(1 - 0.65/1.21) = 1.5*(1-0.5372...) = 1.5*0.4628... = 0.6942...
        expected = (3 / 2) * (1 - 0.65 / 1.21)
        self.assertAlmostEqual(result, expected, places=4)

    def test_kr20_single_item(self):
        """k=1 → None."""
        matrix = [[1], [0], [1]]
        scores = [1.0, 0.0, 1.0]
        self.assertIsNone(kr20(matrix, scores))

    def test_kr20_zero_variance(self):
        """All students score the same → None (zero variance)."""
        matrix = [[1, 0, 1], [1, 0, 1], [1, 0, 1]]
        scores = [2.0, 2.0, 2.0]
        self.assertIsNone(kr20(matrix, scores))

    def test_kr20_single_student(self):
        """n=1 → None."""
        matrix = [[1, 0, 1]]
        scores = [2.0]
        self.assertIsNone(kr20(matrix, scores))


class PercentileRankTest(TestCase):
    """Percentile + rank computation."""

    def test_basic(self):
        """5 distinct scores."""
        scores = [10.0, 8.0, 6.0, 4.0, 2.0]
        result = percentile_rank(scores)
        self.assertEqual(len(result), 5)

        # Highest scorer: 5 students ≤ 10 → percentile = 5/5*100 = 100%
        r0 = result[0]
        self.assertAlmostEqual(r0["percentile"], 100.0, places=5)
        self.assertEqual(r0["rank"], 1)

        # Lowest scorer: 1 student ≤ 2 → percentile = 1/5*100 = 20%
        r4 = result[4]
        self.assertAlmostEqual(r4["percentile"], 20.0, places=5)
        self.assertEqual(r4["rank"], 5)

    def test_ties(self):
        """Tied scores share the best rank."""
        scores = [10.0, 10.0, 5.0]
        result = percentile_rank(scores)
        # Both 10.0 → rank 1
        self.assertEqual(result[0]["rank"], 1)
        self.assertEqual(result[1]["rank"], 1)
        # 5.0 → rank 2 (dense rank: only 2 unique values above)
        self.assertEqual(result[2]["rank"], 2)

    def test_empty(self):
        self.assertEqual(percentile_rank([]), [])

    def test_single(self):
        result = percentile_rank([7.0])
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["percentile"], 100.0, places=5)
        self.assertEqual(result[0]["rank"], 1)


# ---------------------------------------------------------------------------
# 2. Degenerate-cohort tests (no crash, correct status markers)
# ---------------------------------------------------------------------------

class SmallCohortGuardTest(TestCase):
    """Below MIN_COHORT (< 10) the profile must not crash and must flag properly."""

    def _make_1_student_data(self):
        return [{
            "student_id": 1,
            "student_result_id": 1,
            "score": 3.0,
            "max_score": 3.0,
            "item_scores": [1, 1, 1],
            "option_choices": {
                0: {"A": 1},
                1: {"A": 1},
                2: {"A": 1},
            },
        }]

    def test_single_student_no_crash(self):
        """1 student → no exception; discrimination + pb + KR20 are insufficient."""
        data = self._make_1_student_data()
        profile = compute_test_profile(data)
        self.assertEqual(profile["n"], 1)
        self.assertIn("insufficient_sample", profile["flags"])

        for item in profile["items"]:
            d = item["discrimination"]
            pb = item["point_biserial"]
            self.assertIsInstance(d, dict)
            self.assertEqual(d["status"], "insufficient_sample")
            self.assertIsInstance(pb, dict)
            self.assertEqual(pb["status"], "insufficient_sample")

        self.assertIsInstance(profile["kr20"], dict)
        self.assertEqual(profile["kr20"]["status"], "insufficient_sample")

    def test_all_correct_no_divide_by_zero(self):
        """All students all correct — zero item variance — no crash."""
        data = [
            {
                "student_id": i,
                "student_result_id": i,
                "score": 3.0,
                "max_score": 3.0,
                "item_scores": [1, 1, 1],
                "option_choices": {0: {"A": 1}, 1: {"A": 1}, 2: {"A": 1}},
            }
            for i in range(10)
        ]
        # Should not raise
        profile = compute_test_profile(data)
        self.assertEqual(profile["n"], 10)
        # KR-20: var_T=0 → None
        self.assertIsNone(profile["kr20"])

    def test_all_same_score_no_divide_by_zero(self):
        """10 students all same score (but different items correct) — no crash."""
        # Each scores 1/3 but different item correct
        data = []
        for i in range(10):
            items = [0, 0, 0]
            items[i % 3] = 1
            data.append({
                "student_id": i,
                "student_result_id": i,
                "score": 1.0,
                "max_score": 3.0,
                "item_scores": items,
                "option_choices": {},
            })
        profile = compute_test_profile(data)
        self.assertEqual(profile["n"], 10)
        # var_T=0 → KR-20 = None (zero total variance)
        self.assertIsNone(profile["kr20"])

    def test_zero_results_no_crash(self):
        """Empty cohort → safe empty profile."""
        profile = compute_test_profile([])
        self.assertEqual(profile["n"], 0)
        self.assertIsNone(profile["kr20"])
        self.assertEqual(profile["items"], [])


# ---------------------------------------------------------------------------
# 3. Full profile with DB: build_results_data + recompute_test_profile task
# ---------------------------------------------------------------------------

class BuildResultsDataTest(TestCase):
    """build_results_data reads the DB correctly."""

    def setUp(self):
        self.user = _make_user("brd@test.com")
        self.test = _make_test(self.user, "BRD Test")
        self.questions = _make_questions(self.test, n=3)

    def _make_student_and_result(self, roll, item_scores):
        student = _make_student(self.user, roll)
        sheet = _make_omr_sheet(self.test, self.questions, seed=int(roll), student=student)
        _make_result_with_responses(self.test, student, sheet, item_scores)
        return student

    def test_empty_test_returns_empty(self):
        data = build_results_data(self.test)
        self.assertEqual(data, [])

    def test_single_student(self):
        self._make_student_and_result("001", [1, 0, 1])
        data = build_results_data(self.test)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["score"], 2.0)
        self.assertEqual(data[0]["item_scores"], [1, 0, 1])

    def test_item_scores_correct(self):
        """3 students with known item patterns."""
        self._make_student_and_result("001", [1, 1, 1])
        self._make_student_and_result("002", [1, 0, 0])
        self._make_student_and_result("003", [0, 0, 0])
        data = build_results_data(self.test)
        self.assertEqual(len(data), 3)
        scores = sorted(d["score"] for d in data)
        self.assertEqual(scores, [0.0, 1.0, 3.0])


# ---------------------------------------------------------------------------
# 4. DB-backed profile: task upserts TestProfile + StudentProfile
# ---------------------------------------------------------------------------

class RecomputeTestProfileTaskTest(TestCase):
    """recompute_test_profile() writes TestProfile + StudentProfile rows."""

    def _build_10_student_fixture(self):
        """Build the canonical 10-student fixture in the DB."""
        user = _make_user("task10@test.com")
        test = _make_test(user, "Task10 Test")
        questions = _make_questions(test, n=3)

        item_pattern = [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 0],
            [1, 1, 0],
            [1, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        students = []
        for i, items in enumerate(item_pattern):
            roll = f"{i+1:03d}"
            student = _make_student(user, roll, name=f"Student {i+1}")
            sheet = _make_omr_sheet(test, questions, seed=i + 1, student=student)
            _make_result_with_responses(test, student, sheet, items)
            students.append(student)
        return user, test, questions, students

    def test_task_creates_test_profile(self):
        _, test, _, _ = self._build_10_student_fixture()
        self.assertFalse(TestProfile.objects.filter(test=test).exists())

        recompute_test_profile(test.id)

        tp = TestProfile.objects.get(test=test)
        self.assertEqual(tp.cohort_size, 10)
        self.assertEqual(tp.status, TestProfile.STATUS_OK)
        self.assertIn("n", tp.profile)
        self.assertEqual(tp.profile["n"], 10)

    def test_task_creates_student_profiles(self):
        _, test, _, students = self._build_10_student_fixture()
        recompute_test_profile(test.id)
        self.assertEqual(StudentProfile.objects.filter(test=test).count(), 10)

    def test_task_student_profile_ranks(self):
        """Top scorer (score=3) should have rank 1."""
        _, test, _, _ = self._build_10_student_fixture()
        recompute_test_profile(test.id)

        top_sp = StudentProfile.objects.filter(test=test).order_by("rank").first()
        self.assertEqual(top_sp.rank, 1)
        self.assertAlmostEqual(top_sp.score, 3.0, places=5)
        # Percentile for top scorers: 2 students score 3.0; 10 students ≤ 3.0 → 100%
        self.assertAlmostEqual(top_sp.percentile, 100.0, places=2)

    def test_task_kr20_in_profile(self):
        """KR-20 value matches hand-computed 0.6942 for the 10-student fixture."""
        _, test, _, _ = self._build_10_student_fixture()
        recompute_test_profile(test.id)

        tp = TestProfile.objects.get(test=test)
        kr20_val = tp.profile["kr20"]
        expected = (3 / 2) * (1 - 0.65 / 1.21)
        self.assertAlmostEqual(kr20_val, expected, places=4)

    def test_task_difficulty_in_profile(self):
        """Item difficulties match golden values."""
        _, test, _, _ = self._build_10_student_fixture()
        recompute_test_profile(test.id)

        tp = TestProfile.objects.get(test=test)
        items = tp.profile["items"]
        diffs = [item["difficulty"] for item in items]
        self.assertAlmostEqual(diffs[0], 0.6, places=5)
        self.assertAlmostEqual(diffs[1], 0.5, places=5)
        self.assertAlmostEqual(diffs[2], 0.2, places=5)

    def test_task_discrimination_in_profile(self):
        """Item discrimination matches golden value 1.0."""
        _, test, _, _ = self._build_10_student_fixture()
        recompute_test_profile(test.id)

        tp = TestProfile.objects.get(test=test)
        for item in tp.profile["items"]:
            self.assertAlmostEqual(item["discrimination"], 1.0, places=5)

    def test_task_point_biserial_item0(self):
        """Point-biserial for item0 ≈ 0.4704 (golden value; see derivation in docstring)."""
        _, test, _, _ = self._build_10_student_fixture()
        recompute_test_profile(test.id)

        tp = TestProfile.objects.get(test=test)
        pb0 = tp.profile["items"][0]["point_biserial"]
        self.assertAlmostEqual(pb0, 0.4704, places=3)

    def test_task_upserts_idempotent(self):
        """Calling the task twice produces exactly one TestProfile."""
        _, test, _, _ = self._build_10_student_fixture()
        recompute_test_profile(test.id)
        recompute_test_profile(test.id)
        self.assertEqual(TestProfile.objects.filter(test=test).count(), 1)

    def test_task_no_results_creates_no_profile(self):
        """Test with no StudentResults → task returns early, no TestProfile created."""
        user = _make_user("empty@test.com")
        test = _make_test(user, "Empty Test")
        recompute_test_profile(test.id)
        self.assertFalse(TestProfile.objects.filter(test=test).exists())

    def test_small_cohort_profile_status_insufficient(self):
        """n < MIN_COHORT → status insufficient_sample."""
        user = _make_user("small@test.com")
        test = _make_test(user, "Small Cohort")
        questions = _make_questions(test, n=3)

        for i in range(5):
            student = _make_student(user, f"{i+1:03d}", name=f"S{i}")
            sheet = _make_omr_sheet(test, questions, seed=100 + i, student=student)
            _make_result_with_responses(test, student, sheet, [1, 0, 1])

        recompute_test_profile(test.id)
        tp = TestProfile.objects.get(test=test)
        self.assertEqual(tp.status, TestProfile.STATUS_INSUFFICIENT)


# ---------------------------------------------------------------------------
# 5. Profile endpoint: GET /api/v1/analytics/test/<id>/profile/
# ---------------------------------------------------------------------------

class TestProfileEndpointTest(TestCase):
    """Endpoint returns the profile; auth + scope enforced."""

    def setUp(self):
        self.user = _make_user("ep@test.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.test = _make_test(self.user, "Endpoint Test")
        questions = _make_questions(self.test, n=3)

        # Build a small valid cohort (5 students — will be insufficient but still returns)
        for i in range(5):
            student = _make_student(self.user, f"EP{i+1:03d}", name=f"Ep{i}")
            sheet = _make_omr_sheet(self.test, questions, seed=200 + i, student=student)
            _make_result_with_responses(self.test, student, sheet, [1, 1, 0])

    def _url(self, test_id=None):
        tid = test_id if test_id is not None else self.test.id
        return reverse("analytics-test-profile", kwargs={"test_id": tid})

    def test_returns_200_with_profile(self):
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("profile", data)
        self.assertIn("cohort_size", data)
        self.assertIn("status", data)
        self.assertEqual(data["cohort_size"], 5)

    def test_requires_auth(self):
        anon = APIClient()
        resp = anon.get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cross_tenant_404(self):
        other = _make_user("other-ep@test.com")
        other_client = APIClient()
        other_client.force_authenticate(user=other)
        resp = other_client.get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_results_returns_no_results_status(self):
        """
        A test with no StudentResults: on-demand computation creates a
        TestProfile with status='no_results'. The endpoint returns 404
        because there are no results to profile yet.
        """
        empty_test = _make_test(self.user, "Empty Test EP")
        resp = self.client.get(self._url(empty_test.id))
        # No results → the task returns early with no TestProfile created → 404
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_profile_auto_computed_on_demand(self):
        """Profile is computed on demand if not cached."""
        # Ensure no pre-existing profile
        TestProfile.objects.filter(test=self.test).delete()
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Profile should now be cached
        self.assertTrue(TestProfile.objects.filter(test=self.test).exists())


# ---------------------------------------------------------------------------
# 6. Student detail enriched with percentile + rank
# ---------------------------------------------------------------------------

class StudentDetailEnrichedTest(TestCase):
    """GET student detail includes percentile + rank when a StudentProfile exists."""

    def setUp(self):
        self.user = _make_user("sde@test.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.test = _make_test(self.user, "SDE Test")
        self.questions = _make_questions(self.test, n=3)
        self.student = _make_student(self.user, "SDE001")
        sheet = _make_omr_sheet(self.test, self.questions, seed=300, student=self.student)
        self.sr = _make_result_with_responses(
            self.test, self.student, sheet, [1, 1, 1]
        )
        recompute_test_profile(self.test.id)

    def test_student_detail_includes_percentile(self):
        url = reverse(
            "analytics-student-detail",
            kwargs={"test_id": self.test.id, "student_id": self.student.id},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("percentile", data)
        self.assertIn("rank", data)
        self.assertIn("cohort_size", data)
        self.assertIsNotNone(data["percentile"])
        self.assertIsNotNone(data["rank"])

    def test_student_without_profile_returns_none_fields(self):
        """Student detail is OK even without a StudentProfile (graceful None)."""
        StudentProfile.objects.filter(test=self.test).delete()
        url = reverse(
            "analytics-student-detail",
            kwargs={"test_id": self.test.id, "student_id": self.student.id},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIsNone(data["percentile"])
        self.assertIsNone(data["rank"])


# ---------------------------------------------------------------------------
# 7. Scan batch completion triggers profile computation (eager task)
# ---------------------------------------------------------------------------

class ScanBatchProfileAutoPopulateTest(TestCase):
    """
    After a ScanBatch completes, recompute_test_profile runs (ALWAYS_EAGER=True)
    and the TestProfile is populated.
    """

    def _build_batch_and_complete(self):
        """
        Simulate a full scan batch completion by directly calling the Celery
        task (as it would be triggered by the omr.tasks.process_scan_job_task
        when batch.processed >= batch.total).
        """
        user = _make_user("auto@test.com")
        test = _make_test(user, "AutoPop Test")
        questions = _make_questions(test, n=3)

        # Build 3 students with results (enough for a cohort)
        for i in range(3):
            student = _make_student(user, f"AP{i+1:03d}", name=f"AP{i}")
            sheet = _make_omr_sheet(test, questions, seed=400 + i, student=student)
            _make_result_with_responses(test, student, sheet, [1, 0, 1])

        # Simulate batch completion triggering the task directly
        from analytics.tasks import recompute_test_profile
        recompute_test_profile(test.id)

        return test

    def test_profile_created_after_batch_complete(self):
        test = self._build_batch_and_complete()
        self.assertTrue(TestProfile.objects.filter(test=test).exists())
        tp = TestProfile.objects.get(test=test)
        self.assertEqual(tp.cohort_size, 3)
        # With only 3 students: status = insufficient_sample
        self.assertEqual(tp.status, TestProfile.STATUS_INSUFFICIENT)


# ---------------------------------------------------------------------------
# 8. Distractor analysis flags
# ---------------------------------------------------------------------------

class DistractorAnalysisTest(TestCase):
    """Non-functioning distractor and miskey suspect detection."""

    def test_nfd_flag(self):
        """A distractor chosen by 0% is flagged as non-functioning."""
        n = 10
        # Option 'A' = key (8/10 correct); 'B' = 2/10; 'C' = 0/10; 'D' = 0/10
        opt_choices = {
            "A": [1, 1, 1, 1, 1, 1, 1, 1, 0, 0],  # key, 8 correct
            "B": [0, 0, 0, 0, 0, 0, 0, 0, 1, 1],  # 2 chose wrong
            "C": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # NFD: 0%
            "D": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # NFD: 0%
        }
        scores = [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.0, 0.0]
        result = distractor_analysis(opt_choices, scores, "A", n=n)
        flag_strs = result["flags"]
        self.assertIn("non_functioning_distractor:C", flag_strs)
        self.assertIn("non_functioning_distractor:D", flag_strs)
        # The key 'A' should NOT be flagged as NFD
        self.assertNotIn("non_functioning_distractor:A", flag_strs)

    def test_miskey_suspect_flag(self):
        """A distractor chosen more by high performers than the key is flagged."""
        n = 12
        # High scorers (top 4) choose 'B' more than 'A' → miskey suspect for B
        # total_scores sorted: high=[10,9,8,7], mid=[6,5,4], low=[3,2,1,0,0]
        total_scores = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.0, 0.0]
        # Key 'A' chosen by low scorers mostly; 'B' chosen by high scorers → miskey
        opt_choices = {
            "A": [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # key, low scorers choose it
            "B": [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # distractor, high scorers choose it
            "C": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "D": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        }
        result = distractor_analysis(opt_choices, total_scores, "A", n=n)
        self.assertIn("miskey_suspect:B", result["flags"])


# ---------------------------------------------------------------------------
# 9. Smoke test: existing analytics endpoints still work
# ---------------------------------------------------------------------------

class ExistingAnalyticsEndpointsSmoke(TestCase):
    """Existing endpoints still respond 200 after Phase 2A changes."""

    def setUp(self):
        self.user = _make_user("smoke@test.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.test = _make_test(self.user, "Smoke Test")
        questions = _make_questions(self.test, n=3)
        student = _make_student(self.user, "SMK001")
        sheet = _make_omr_sheet(self.test, questions, seed=999, student=student)
        _make_result_with_responses(self.test, student, sheet, [1, 0, 1])

    def test_test_analytics_still_200(self):
        url = reverse("analytics-test", kwargs={"test_id": self.test.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_improvement_still_200(self):
        url = reverse("analytics-improvement", kwargs={"test_id": self.test.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_export_csv_still_200(self):
        url = reverse("analytics-export", kwargs={"test_id": self.test.id})
        resp = self.client.get(url, {"output_format": "csv"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
