import io
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from assessments.models import ClassGroup, Test, MarkingScheme, Question, Option

User = get_user_model()


def _tiny_png() -> bytes:
    """Return a minimal valid 1×1 red PNG (67 bytes)."""
    import struct, zlib
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))  # filter=0, R=255,G=0,B=0
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="t@example.com", password="Str0ng!pass")

    def test_scope_constraint_rejects_no_scope(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClassGroup.objects.create(created_by=self.user, name="C")  # no user/org → violates XOR

    def test_scope_constraint_rejects_both_scopes(self):
        from organizations.models import Organization
        org = Organization.objects.create(name="O", owner=self.user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClassGroup.objects.create(created_by=self.user, name="C", user=self.user, organization=org)

    def test_create_class_test_question_option(self):
        c = ClassGroup.objects.create(created_by=self.user, name="Class 8", user=self.user)
        t = Test.objects.create(class_group=c, created_by=self.user, title="Test 1", subject="Math", user=self.user)
        MarkingScheme.objects.create(test=t, marks_per_correct=Decimal("2"))
        q = Question.objects.create(test=t, order_index=0, text="2+2?")
        Option.objects.create(question=q, label="A", text="3")
        Option.objects.create(question=q, label="B", text="4", is_correct=True)
        self.assertEqual(t.class_group, c)
        self.assertEqual(t.attempt_number, 1)
        self.assertEqual(q.options.count(), 2)
        self.assertEqual(t.marking_scheme.marks_per_correct, Decimal("2"))


class ClassApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.a = User.objects.create_user(email="a@example.com", password="Str0ng!pass")
        self.b = User.objects.create_user(email="b@example.com", password="Str0ng!pass")
        self._auth(self.a)

    def _auth(self, user):
        r = self.client.post("/api/v1/auth/login/", {"email": user.email, "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def test_create_and_list_own_classes(self):
        r = self.client.post("/api/v1/classes/", {"name": "Class 8"}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)

    def test_scope_isolation(self):
        cache.clear()
        self.client.post("/api/v1/classes/", {"name": "A-class"}, format="json")
        self._auth(self.b)  # switch to user B
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(len(r.data["results"]), 0)  # B sees none of A's

    def test_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/classes/").status_code, 401)


class TestApiTests(ClassApiTests):  # reuse _auth/setUp (cache.clear included)
    def _make_class(self):
        return self.client.post("/api/v1/classes/", {"name": "C"}, format="json").data["id"]

    def test_create_test_with_marking(self):
        cid = self._make_class()
        r = self.client.post("/api/v1/tests/", {
            "class_group": cid, "title": "T1", "subject": "Math",
            "marking_scheme": {"marks_per_correct": "2", "negative_marks_per_wrong": "0.5"},
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["marking_scheme"]["marks_per_correct"], "2.00")

    def test_cannot_use_others_class(self):
        cid = self._make_class()
        self._auth(self.b)
        r = self.client.post("/api/v1/tests/", {"class_group": cid, "title": "X"}, format="json")
        self.assertIn(r.status_code, (400, 404))

    def test_retest_links_and_increments(self):
        cid = self._make_class()
        tid = self.client.post("/api/v1/tests/", {"class_group": cid, "title": "T1"}, format="json").data["id"]
        r = self.client.post(f"/api/v1/tests/{tid}/retest/")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["parent_test"], tid)
        self.assertEqual(r.data["attempt_number"], 2)

    def test_create_test_with_mode_roster_prebubbled(self):
        """mode=roster_prebubbled is accepted and round-trips."""
        cid = self._make_class()
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": cid, "title": "Roster Test", "mode": "roster_prebubbled"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["mode"], "roster_prebubbled")
        # verify it persists via GET
        tid = r.data["id"]
        r2 = self.client.get(f"/api/v1/tests/{tid}/")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["mode"], "roster_prebubbled")

    def test_create_test_default_mode_is_standard(self):
        """Omitting mode defaults to standard."""
        cid = self._make_class()
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": cid, "title": "Standard Test"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["mode"], "standard")

    def test_create_test_invalid_mode_rejected(self):
        """An unknown mode value must be rejected with 400."""
        cid = self._make_class()
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": cid, "title": "Bad Mode Test", "mode": "invalid_mode"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)


class QuestionApiTests(ClassApiTests):
    def _make_test(self):
        cid = self.client.post("/api/v1/classes/", {"name": "C"}, format="json").data["id"]
        return self.client.post("/api/v1/tests/", {"class_group": cid, "title": "T"}, format="json").data["id"]

    def test_create_question_with_options(self):
        tid = self._make_test()
        r = self.client.post("/api/v1/questions/", {
            "test": tid, "order_index": 0, "text": "2+2?",
            "options": [{"label": "A", "text": "3"}, {"label": "B", "text": "4", "is_correct": True}],
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["options"]), 2)

    def test_cannot_add_to_others_test(self):
        tid = self._make_test()
        self._auth(self.b)
        r = self.client.post("/api/v1/questions/", {"test": tid, "text": "x", "options": []}, format="json")
        self.assertIn(r.status_code, (400, 404))

    def test_owner_can_retrieve_update_delete_own_question(self):
        tid = self._make_test()
        qid = self.client.post("/api/v1/questions/", {"test": tid, "text": "Q", "options": [{"label": "A", "text": "1"}]}, format="json").data["id"]
        self.assertEqual(self.client.get(f"/api/v1/questions/{qid}/").status_code, 200)
        self.assertEqual(self.client.patch(f"/api/v1/questions/{qid}/", {"text": "Q2", "options": [{"label": "A", "text": "1"}]}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/questions/{qid}/").status_code, 204)

    def test_cross_tenant_question_detail_404(self):
        tid = self._make_test()
        qid = self.client.post("/api/v1/questions/", {"test": tid, "text": "Q", "options": []}, format="json").data["id"]
        self._auth(self.b)
        self.assertEqual(self.client.get(f"/api/v1/questions/{qid}/").status_code, 404)


class QuestionImageUploadTests(ClassApiTests):
    """TDD: question-level image upload via multipart PATCH."""

    def _make_test(self):
        cid = self.client.post("/api/v1/classes/", {"name": "C"}, format="json").data["id"]
        return self.client.post("/api/v1/tests/", {"class_group": cid, "title": "T"}, format="json").data["id"]

    def _make_question(self, tid):
        r = self.client.post(
            "/api/v1/questions/",
            {
                "test": tid,
                "order_index": 0,
                "text": "What is 2+2?",
                "options": [{"label": "A", "text": "3"}, {"label": "B", "text": "4", "is_correct": True}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def test_patch_question_with_image_saves_and_returns_url(self):
        """PATCH /api/v1/questions/{id}/ with multipart image → 200, image saved, GET returns URL."""
        tid = self._make_test()
        qid = self._make_question(tid)

        # Build multipart form data — only supply the image field (no options required for PATCH)
        png_bytes = _tiny_png()
        upload = SimpleUploadedFile("test_q.png", png_bytes, content_type="image/png")

        # PATCH with multipart; omit 'options' to avoid nested-options multipart complexity
        r = self.client.patch(
            f"/api/v1/questions/{qid}/",
            {"image": upload},
            format="multipart",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn("image", r.data)
        # The image field in the response must be a non-empty URL
        self.assertTrue(r.data["image"], "Expected a non-empty image URL in the response")
        self.assertIn("/media/", r.data["image"])

        # GET the question and verify image URL is present
        r_get = self.client.get(f"/api/v1/questions/{qid}/")
        self.assertEqual(r_get.status_code, 200)
        self.assertTrue(r_get.data["image"], "GET should return the image URL")
        self.assertIn("/media/", r_get.data["image"])

    def test_question_image_field_absent_by_default(self):
        """Creating a question without an image should return image=null or absent."""
        tid = self._make_test()
        qid = self._make_question(tid)
        r = self.client.get(f"/api/v1/questions/{qid}/")
        self.assertEqual(r.status_code, 200)
        # image field should be present in response (null if no image)
        self.assertIn("image", r.data)
        self.assertIsNone(r.data["image"])

    def test_patch_question_image_clears_with_null(self):
        """PATCH with image='' or JSON null clears the image."""
        tid = self._make_test()
        qid = self._make_question(tid)

        # First, upload an image
        png_bytes = _tiny_png()
        upload = SimpleUploadedFile("test_q2.png", png_bytes, content_type="image/png")
        r = self.client.patch(f"/api/v1/questions/{qid}/", {"image": upload}, format="multipart")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["image"])

        # Now clear via JSON PATCH with null
        r2 = self.client.patch(f"/api/v1/questions/{qid}/", {"image": None}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertIsNone(r2.data["image"])
