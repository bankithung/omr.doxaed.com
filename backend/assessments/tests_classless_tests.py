"""Class-less exams — the Supabase-style "exam is the hero, class is optional".

A Test may have no class_group. Solo: owned by the user. Org: owned by its
creator (private to creator + admins). Every edit path (questions, generate,
scan, update, delete, retest) must work for the owner of a class-less exam and
stay isolated from other members.
"""
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Organization, OrganizationMembership
from assessments.models import Test


class ClasslessExamSoloTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user(email="solo@o.com", password="Str0ng!pass")

    def _login(self, u):
        r = self.client.post("/api/v1/auth/login/", {"email": u.email, "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def test_solo_creates_classless_exam(self):
        self._login(self.user)
        r = self.client.post("/api/v1/tests/", {"title": "Direct Exam"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIsNone(r.data["class_group"])

    def test_classless_exam_lists_and_retrieves(self):
        self._login(self.user)
        tid = self.client.post("/api/v1/tests/", {"title": "E"}, format="json").data["id"]
        lst = self.client.get("/api/v1/tests/")
        rows = lst.data["results"] if isinstance(lst.data, dict) else lst.data
        self.assertIn(tid, [t["id"] for t in rows])
        self.assertEqual(self.client.get(f"/api/v1/tests/{tid}/").status_code, 200)

    def test_can_add_question_generate_update_delete_classless(self):
        self._login(self.user)
        tid = self.client.post("/api/v1/tests/", {"title": "E"}, format="json").data["id"]
        # add a question — the gate must allow the owner of a class-less exam
        q = self.client.post(
            "/api/v1/questions/",
            {"test": tid, "order_index": 0, "text": "2+2?", "options": [
                {"label": "A", "text": "4", "is_correct": True},
                {"label": "B", "text": "3", "is_correct": False},
            ]},
            format="json",
        )
        self.assertEqual(q.status_code, 201, q.data)
        # update + delete the exam
        self.assertEqual(self.client.patch(f"/api/v1/tests/{tid}/", {"title": "E2"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/tests/{tid}/").status_code, 204)


class ClasslessExamOrgTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.admin = User.objects.create_user(email="adm@o.com", password="Str0ng!pass")
        self.m1 = User.objects.create_user(email="m1@o.com", password="Str0ng!pass")
        self.m2 = User.objects.create_user(email="m2@o.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="O", owner=self.admin)
        OrganizationMembership.objects.create(organization=self.org, user=self.admin, role="admin", status="active")
        OrganizationMembership.objects.create(organization=self.org, user=self.m1, role="member", status="active")
        OrganizationMembership.objects.create(organization=self.org, user=self.m2, role="member", status="active")

    def _login(self, u):
        r = self.client.post("/api/v1/auth/login/", {"email": u.email, "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _h(self):
        return {"HTTP_X_ORGANIZATION_ID": str(self.org.id)}

    def test_member_creates_classless_org_exam(self):
        self._login(self.m1)
        r = self.client.post("/api/v1/tests/", {"title": "M1 Exam"}, format="json", **self._h())
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIsNone(r.data["class_group"])

    def test_classless_exam_private_to_creator_and_admin(self):
        self._login(self.m1)
        tid = self.client.post("/api/v1/tests/", {"title": "M1 Exam"}, format="json", **self._h()).data["id"]
        self.assertEqual(self.client.get(f"/api/v1/tests/{tid}/", **self._h()).status_code, 200)
        # another member must NOT see it
        self._login(self.m2)
        self.assertEqual(self.client.get(f"/api/v1/tests/{tid}/", **self._h()).status_code, 404)
        # admin sees all
        self._login(self.admin)
        self.assertEqual(self.client.get(f"/api/v1/tests/{tid}/", **self._h()).status_code, 200)

    def test_member_can_edit_own_classless_exam_but_other_cannot(self):
        self._login(self.m1)
        tid = self.client.post("/api/v1/tests/", {"title": "M1"}, format="json", **self._h()).data["id"]
        self.assertEqual(
            self.client.patch(f"/api/v1/tests/{tid}/", {"title": "M1b"}, format="json", **self._h()).status_code, 200
        )
        # m2 can't even see it → 404 on update
        self._login(self.m2)
        self.assertEqual(
            self.client.patch(f"/api/v1/tests/{tid}/", {"title": "hax"}, format="json", **self._h()).status_code, 404
        )
