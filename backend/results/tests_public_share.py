"""
Tests for Phase 2D: PublicResultShare — public shareable result portal.

Coverage
--------
- Model: slug auto-generated, unique, unguessable length; access_code hashing.
- Teacher publish API (auth required, owner-scoped):
  - GET returns defaults when no share exists.
  - PUT creates share with correct fields.
  - Non-owner gets 403/404.
- Public endpoints (no auth):
  - Meta 404 when unpublished.
  - Meta 200 when published.
  - Lookup returns correct student only.
  - Wrong roll → generic 404 "No result found".
  - access_mode="code" blocks without code, allows with correct code.
  - Wrong access code → 403 generic (not revealing roll existence).
  - show_names=False masks names.
  - Leaderboard 404 when show_leaderboard=False.
  - Leaderboard 200 when published + show_leaderboard=True.
  - Unpublishing makes link 404 immediately.
  - Isolation: lookup on slug-A never returns slug-B's data.
- Throttle scope "public_lookup" is present in DEFAULT_THROTTLE_RATES.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from analytics.models import StudentProfile
from assessments.models import ClassGroup, Test
from omr.models import OmrSheet
from results.models import PublicResultShare, StudentResult
from rosters.models import Roster, Student

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email="teacher@example.com"):
    return User.objects.create_user(email=email, password="Str0ngPass!")


def _make_test(user, title="Math Test"):
    cg = ClassGroup.objects.create(user=user, created_by=user, name="CG")
    return Test.objects.create(user=user, class_group=cg, created_by=user, title=title)


def _make_sheet(test, sheet_code="SHEET-001"):
    return OmrSheet.objects.create(
        test=test,
        sheet_code=sheet_code,
        human_readable_code=sheet_code,
    )


def _make_student(user, roll="R001", name="Alice Smith"):
    roster = Roster.objects.create(user=user, created_by=user, name="Roster1")
    s = Student.objects.create(roster=roster, roll_number=roll)
    s.full_name = name
    s.save()
    return s


def _make_result(test, student, sheet, score=80, max_score=100):
    return StudentResult.objects.create(
        test=test,
        student=student,
        omr_sheet=sheet,
        score=score,
        max_score=max_score,
    )


def _make_share(test, is_published=True, access_mode="open",
                access_code=None, show_names=True, show_leaderboard=False):
    share = PublicResultShare(test=test, is_published=is_published,
                              access_mode=access_mode, show_names=show_names,
                              show_leaderboard=show_leaderboard)
    if access_code:
        share.set_access_code(access_code)
    share.save()
    return share


def _make_profile(test, student, result, rank=1, percentile=90.0):
    return StudentProfile.objects.create(
        test=test, student=student, result=result,
        score=float(result.score), rank=rank, percentile=percentile,
        cohort_size=10,
    )


def _auth_client(user):
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "Str0ngPass!"},
        format="json",
    )
    token = resp.data.get("access", "")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------

class PublicResultShareModelTest(TestCase):

    def setUp(self):
        self.user = _make_user()
        self.test = _make_test(self.user)

    def test_slug_auto_generated_on_save(self):
        share = PublicResultShare(test=self.test)
        share.save()
        self.assertIsNotNone(share.slug)
        self.assertGreater(len(share.slug), 8)

    def test_slug_is_unguessable_length(self):
        """secrets.token_urlsafe(12) yields 16-char base64url strings."""
        share = PublicResultShare(test=self.test)
        share.save()
        # base64url of 12 bytes = 16 chars; at least 12 chars always
        self.assertGreaterEqual(len(share.slug), 12)

    def test_slug_is_unique(self):
        user2 = _make_user("t2@example.com")
        test2 = _make_test(user2, title="Test B")
        s1 = PublicResultShare(test=self.test)
        s1.save()
        s2 = PublicResultShare(test=test2)
        s2.save()
        self.assertNotEqual(s1.slug, s2.slug)

    def test_slug_not_regenerated_on_update(self):
        share = PublicResultShare(test=self.test)
        share.save()
        original_slug = share.slug
        share.is_published = True
        share.save()
        self.assertEqual(share.slug, original_slug)

    def test_access_code_hashed_never_plaintext(self):
        share = PublicResultShare(test=self.test)
        share.set_access_code("secret123")
        share.save()
        self.assertIsNotNone(share.access_code_hash)
        self.assertNotEqual(share.access_code_hash, "secret123")
        self.assertIn("$", share.access_code_hash)  # Django hash marker

    def test_access_code_check_password(self):
        from django.contrib.auth.hashers import check_password
        share = PublicResultShare(test=self.test)
        share.set_access_code("secret123")
        share.save()
        self.assertTrue(check_password("secret123", share.access_code_hash))
        self.assertFalse(check_password("wrongcode", share.access_code_hash))

    def test_default_values(self):
        share = PublicResultShare(test=self.test)
        share.save()
        self.assertFalse(share.is_published)
        self.assertEqual(share.access_mode, PublicResultShare.ACCESS_OPEN)
        self.assertTrue(share.show_names)
        self.assertFalse(share.show_leaderboard)
        self.assertIsNone(share.access_code_hash)


# ---------------------------------------------------------------------------
# Teacher publish API tests (authenticated, owner-scoped)
# ---------------------------------------------------------------------------

class TeacherPublishAPITest(TestCase):

    def setUp(self):
        self.teacher = _make_user("teach@example.com")
        self.other = _make_user("other@example.com")
        self.test = _make_test(self.teacher)
        self.client = _auth_client(self.teacher)
        self.other_client = _auth_client(self.other)
        self.url = f"/api/v1/analytics/test/{self.test.id}/publish/"

    def test_get_returns_defaults_when_no_share(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        self.assertIsNone(data["slug"])
        self.assertFalse(data["is_published"])
        self.assertEqual(data["access_mode"], "open")

    def test_put_creates_share(self):
        resp = self.client.put(self.url, {
            "is_published": True,
            "access_mode": "open",
            "show_names": True,
            "show_leaderboard": False,
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        self.assertIsNotNone(data["slug"])
        self.assertTrue(data["is_published"])
        self.assertIn("/r/", data["public_url"])

    def test_put_creates_share_with_code_mode(self):
        resp = self.client.put(self.url, {
            "is_published": True,
            "access_mode": "code",
            "access_code": "mysecret",
            "show_names": True,
            "show_leaderboard": False,
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        share = PublicResultShare.objects.get(test=self.test)
        self.assertEqual(share.access_mode, "code")
        self.assertIsNotNone(share.access_code_hash)
        self.assertNotEqual(share.access_code_hash, "mysecret")

    def test_put_code_mode_without_code_returns_400(self):
        resp = self.client.put(self.url, {
            "is_published": True,
            "access_mode": "code",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_put_invalid_access_mode_returns_400(self):
        resp = self.client.put(self.url, {
            "is_published": True,
            "access_mode": "invalid",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_non_owner_cannot_get_publish_settings(self):
        resp = self.other_client.get(self.url)
        self.assertIn(resp.status_code, [403, 404])

    def test_non_owner_cannot_put_publish_settings(self):
        resp = self.other_client.put(self.url, {
            "is_published": True,
        }, format="json")
        self.assertIn(resp.status_code, [403, 404])

    def test_slug_stable_across_updates(self):
        self.client.put(self.url, {"is_published": True, "access_mode": "open"}, format="json")
        share1 = PublicResultShare.objects.get(test=self.test)
        slug1 = share1.slug
        self.client.put(self.url, {"is_published": False, "access_mode": "open"}, format="json")
        share1.refresh_from_db()
        self.assertEqual(share1.slug, slug1)

    def test_public_url_uses_frontend_url(self):
        resp = self.client.put(self.url, {"is_published": True, "access_mode": "open"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(settings.FRONTEND_URL, resp.data["public_url"])


# ---------------------------------------------------------------------------
# Public portal meta tests
# ---------------------------------------------------------------------------

class PublicPortalMetaTest(TestCase):

    def setUp(self):
        self.teacher = _make_user("teach2@example.com")
        self.test = _make_test(self.teacher)
        self.client = APIClient()  # unauthenticated

    def test_meta_404_when_no_share(self):
        resp = self.client.get("/api/v1/public/r/nonexistentslug123/")
        self.assertEqual(resp.status_code, 404)

    def test_meta_404_when_unpublished(self):
        share = _make_share(self.test, is_published=False)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/")
        self.assertEqual(resp.status_code, 404)

    def test_meta_200_when_published(self):
        share = _make_share(self.test, is_published=True)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["test_title"], self.test.title)
        self.assertEqual(resp.data["access_mode"], "open")

    def test_meta_does_not_include_student_data(self):
        share = _make_share(self.test, is_published=True)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("score", resp.data)
        self.assertNotIn("results", resp.data)
        self.assertNotIn("students", resp.data)


# ---------------------------------------------------------------------------
# Public lookup tests
# ---------------------------------------------------------------------------

class PublicLookupTest(TestCase):

    def setUp(self):
        self.teacher = _make_user("teach3@example.com")
        self.test = _make_test(self.teacher)
        self.student = _make_student(self.teacher, roll="R001", name="Alice Smith")
        self.sheet = _make_sheet(self.test, sheet_code="SHEET-A1")
        self.result = _make_result(self.test, self.student, self.sheet, score=75, max_score=100)
        self.share = _make_share(self.test, is_published=True)
        self.url = f"/api/v1/public/r/{self.share.slug}/lookup/"
        self.client = APIClient()

    def test_lookup_returns_correct_student(self):
        resp = self.client.post(self.url, {"roll_number": "R001"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["roll_number"], "R001")
        self.assertEqual(float(resp.data["score"]), 75.0)
        self.assertEqual(float(resp.data["max_score"]), 100.0)

    def test_lookup_wrong_roll_returns_generic_404(self):
        resp = self.client.post(self.url, {"roll_number": "NOTEXIST"}, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("No result found", resp.data["detail"])

    def test_lookup_missing_roll_returns_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_lookup_404_when_unpublished(self):
        self.share.is_published = False
        self.share.save()
        resp = self.client.post(self.url, {"roll_number": "R001"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_lookup_returns_percentile_and_rank_when_profile_exists(self):
        _make_profile(self.test, self.student, self.result, rank=2, percentile=85.0)
        resp = self.client.post(self.url, {"roll_number": "R001"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["rank"], 2)
        self.assertAlmostEqual(resp.data["percentile"], 85.0, places=1)

    def test_lookup_percentile_none_when_no_profile(self):
        resp = self.client.post(self.url, {"roll_number": "R001"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["percentile"])
        self.assertIsNone(resp.data["rank"])

    def test_lookup_never_returns_other_students(self):
        """The response must contain exactly one student's data."""
        student2 = _make_student(self.teacher, roll="R002", name="Bob Jones")
        sheet2 = _make_sheet(self.test, sheet_code="SHEET-A2")
        _make_result(self.test, student2, sheet2, score=55)
        resp = self.client.post(self.url, {"roll_number": "R001"}, format="json")
        self.assertEqual(resp.status_code, 200)
        # Should be a single dict, not a list
        self.assertIsInstance(resp.data, dict)
        self.assertEqual(resp.data["roll_number"], "R001")


# ---------------------------------------------------------------------------
# show_names masking tests
# ---------------------------------------------------------------------------

class ShowNamesMaskingTest(TestCase):

    def setUp(self):
        self.teacher = _make_user("teach4@example.com")
        self.test = _make_test(self.teacher)
        self.student = _make_student(self.teacher, roll="R001", name="Alice Smith")
        self.sheet = _make_sheet(self.test, sheet_code="SHEET-B1")
        self.result = _make_result(self.test, self.student, self.sheet)
        self.client = APIClient()

    def test_show_names_true_returns_full_name(self):
        share = _make_share(self.test, is_published=True, show_names=True)
        resp = self.client.post(
            f"/api/v1/public/r/{share.slug}/lookup/",
            {"roll_number": "R001"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Alice Smith")

    def test_show_names_false_masks_name(self):
        share = _make_share(self.test, is_published=True, show_names=False)
        resp = self.client.post(
            f"/api/v1/public/r/{share.slug}/lookup/",
            {"roll_number": "R001"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        name = resp.data["name"]
        self.assertNotEqual(name, "Alice Smith")
        self.assertTrue(name.startswith("A"))
        self.assertIn("*", name)


# ---------------------------------------------------------------------------
# Access code mode tests
# ---------------------------------------------------------------------------

class AccessCodeModeTest(TestCase):

    def setUp(self):
        self.teacher = _make_user("teach5@example.com")
        self.test = _make_test(self.teacher)
        self.student = _make_student(self.teacher, roll="R001", name="Charlie D")
        self.sheet = _make_sheet(self.test, sheet_code="SHEET-C1")
        self.result = _make_result(self.test, self.student, self.sheet)
        self.share = _make_share(
            self.test, is_published=True, access_mode="code", access_code="s3cr3t"
        )
        self.url = f"/api/v1/public/r/{self.share.slug}/lookup/"
        self.client = APIClient()

    def test_lookup_without_code_returns_403(self):
        resp = self.client.post(self.url, {"roll_number": "R001"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Invalid access code", resp.data["detail"])

    def test_lookup_with_wrong_code_returns_403(self):
        resp = self.client.post(
            self.url, {"roll_number": "R001", "access_code": "wrongcode"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Invalid access code", resp.data["detail"])

    def test_wrong_code_does_not_reveal_roll_existence(self):
        """A wrong code with a non-existent roll must still return 403, not 404."""
        resp = self.client.post(
            self.url, {"roll_number": "NOTEXIST", "access_code": "wrongcode"}, format="json"
        )
        # Must be 403 (code checked first), not 404 (which would reveal the roll doesn't exist)
        self.assertEqual(resp.status_code, 403)

    def test_lookup_with_correct_code_succeeds(self):
        resp = self.client.post(
            self.url, {"roll_number": "R001", "access_code": "s3cr3t"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["roll_number"], "R001")

    def test_empty_code_is_rejected(self):
        resp = self.client.post(
            self.url, {"roll_number": "R001", "access_code": ""}, format="json"
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Leaderboard tests
# ---------------------------------------------------------------------------

class LeaderboardTest(TestCase):

    def setUp(self):
        self.teacher = _make_user("teach6@example.com")
        self.test = _make_test(self.teacher)
        self.client = APIClient()

    def _setup_students(self, share):
        students_data = [
            ("R001", "Alice A", 95, 1, 99.0),
            ("R002", "Bob B", 80, 2, 75.0),
            ("R003", "Carol C", 60, 3, 40.0),
        ]
        results = []
        for roll, name, score, rank, pct in students_data:
            st = _make_student(self.teacher, roll=roll, name=name)
            # Each student needs own roster; override to re-use teacher user
            sheet = _make_sheet(self.test, sheet_code=f"SHEET-{roll}")
            result = _make_result(self.test, st, sheet, score=score, max_score=100)
            _make_profile(self.test, st, result, rank=rank, percentile=pct)
            results.append(result)
        return results

    def test_leaderboard_404_when_show_leaderboard_false(self):
        share = _make_share(self.test, is_published=True, show_leaderboard=False)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/leaderboard/")
        self.assertEqual(resp.status_code, 404)

    def test_leaderboard_404_when_unpublished(self):
        share = _make_share(self.test, is_published=False, show_leaderboard=True)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/leaderboard/")
        self.assertEqual(resp.status_code, 404)

    def test_leaderboard_returns_ranked_list_when_enabled(self):
        share = _make_share(self.test, is_published=True, show_leaderboard=True)
        self._setup_students(share)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/leaderboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        self.assertEqual(len(data), 3)
        # Ordered by rank
        ranks = [item["rank"] for item in data]
        self.assertEqual(ranks, sorted(ranks))

    def test_leaderboard_masks_names_when_show_names_false(self):
        share = _make_share(
            self.test, is_published=True, show_leaderboard=True, show_names=False
        )
        self._setup_students(share)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/leaderboard/")
        self.assertEqual(resp.status_code, 200)
        for item in resp.data:
            self.assertIn("*", item["name"])

    def test_leaderboard_shows_names_when_show_names_true(self):
        share = _make_share(
            self.test, is_published=True, show_leaderboard=True, show_names=True
        )
        self._setup_students(share)
        resp = self.client.get(f"/api/v1/public/r/{share.slug}/leaderboard/")
        self.assertEqual(resp.status_code, 200)
        for item in resp.data:
            self.assertNotEqual(item["name"], "***")


# ---------------------------------------------------------------------------
# Unpublish immediate-effect tests
# ---------------------------------------------------------------------------

class UnpublishTest(TestCase):

    def setUp(self):
        self.teacher = _make_user("teach7@example.com")
        self.test = _make_test(self.teacher)
        self.student = _make_student(self.teacher, roll="R001")
        self.sheet = _make_sheet(self.test, sheet_code="SHEET-D1")
        self.result = _make_result(self.test, self.student, self.sheet)
        self.share = _make_share(self.test, is_published=True)
        self.client = APIClient()
        self.auth_client = _auth_client(self.teacher)

    def test_unpublish_makes_meta_404(self):
        from django.core.cache import cache
        meta_url = f"/api/v1/public/r/{self.share.slug}/"
        # Published → 200
        cache.clear()
        self.assertEqual(self.client.get(meta_url).status_code, 200)
        # Unpublish
        self.auth_client.put(
            f"/api/v1/analytics/test/{self.test.id}/publish/",
            {"is_published": False, "access_mode": "open"}, format="json"
        )
        # Now → 404 (clear throttle cache so the anon rate counter resets)
        cache.clear()
        self.assertEqual(self.client.get(meta_url).status_code, 404)

    def test_unpublish_makes_lookup_404(self):
        lookup_url = f"/api/v1/public/r/{self.share.slug}/lookup/"
        self.assertEqual(
            self.client.post(lookup_url, {"roll_number": "R001"}, format="json").status_code, 200
        )
        self.auth_client.put(
            f"/api/v1/analytics/test/{self.test.id}/publish/",
            {"is_published": False, "access_mode": "open"}, format="json"
        )
        self.assertEqual(
            self.client.post(lookup_url, {"roll_number": "R001"}, format="json").status_code, 404
        )


# ---------------------------------------------------------------------------
# Cross-test isolation tests
# ---------------------------------------------------------------------------

class IsolationTest(TestCase):
    """
    Lookup on slug-A must NEVER return slug-B's or another test's data.
    """

    def setUp(self):
        self.teacher_a = _make_user("teachA@example.com")
        self.teacher_b = _make_user("teachB@example.com")

        self.test_a = _make_test(self.teacher_a, title="Test A")
        self.test_b = _make_test(self.teacher_b, title="Test B")

        # Student in test A with roll R001
        self.student_a = _make_student(self.teacher_a, roll="R001", name="Alice A")
        self.sheet_a = _make_sheet(self.test_a, sheet_code="SHEET-ISO-A")
        self.result_a = _make_result(self.test_a, self.student_a, self.sheet_a, score=90)

        # Student in test B ALSO with roll R001 (different test/org)
        self.student_b = _make_student(self.teacher_b, roll="R001", name="Bob B")
        self.sheet_b = _make_sheet(self.test_b, sheet_code="SHEET-ISO-B")
        self.result_b = _make_result(self.test_b, self.student_b, self.sheet_b, score=55)

        self.share_a = _make_share(self.test_a, is_published=True)
        self.share_b = _make_share(self.test_b, is_published=True)

        self.client = APIClient()

    def test_slug_a_returns_only_test_a_result(self):
        resp = self.client.post(
            f"/api/v1/public/r/{self.share_a.slug}/lookup/",
            {"roll_number": "R001"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        # Must be Alice A's score (90), not Bob B's (55)
        self.assertEqual(float(resp.data["score"]), 90.0)

    def test_slug_b_returns_only_test_b_result(self):
        resp = self.client.post(
            f"/api/v1/public/r/{self.share_b.slug}/lookup/",
            {"roll_number": "R001"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(float(resp.data["score"]), 55.0)

    def test_slug_a_does_not_expose_test_b_data(self):
        """Verify explicitly that the score returned for slug_a is not test_b's score."""
        resp_a = self.client.post(
            f"/api/v1/public/r/{self.share_a.slug}/lookup/",
            {"roll_number": "R001"}, format="json"
        )
        resp_b = self.client.post(
            f"/api/v1/public/r/{self.share_b.slug}/lookup/",
            {"roll_number": "R001"}, format="json"
        )
        self.assertNotEqual(
            float(resp_a.data["score"]),
            float(resp_b.data["score"]),
            "Isolation failure: slug-A returned the same score as slug-B."
        )

    def test_slug_b_lookup_not_found_when_roll_only_in_test_a(self):
        """R999 exists in test A but not B; slug B lookup should return 404."""
        student_a2 = _make_student(self.teacher_a, roll="R999", name="Extra A")
        sheet_a2 = _make_sheet(self.test_a, sheet_code="SHEET-ISO-A2")
        _make_result(self.test_a, student_a2, sheet_a2, score=70)

        resp = self.client.post(
            f"/api/v1/public/r/{self.share_b.slug}/lookup/",
            {"roll_number": "R999"}, format="json"
        )
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Throttle config test
# ---------------------------------------------------------------------------

class ThrottleConfigTest(TestCase):

    def test_public_lookup_scope_configured(self):
        throttle_rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.assertIn("public_lookup", throttle_rates)
        rate = throttle_rates["public_lookup"]
        self.assertIsNotNone(rate)
        # Should be a non-empty string like "30/min"
        self.assertIsInstance(rate, str)
        self.assertGreater(len(rate), 0)
