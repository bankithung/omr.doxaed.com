from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from assessments.models import ClassGroup, Test, MarkingScheme, Question, Option

User = get_user_model()


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
