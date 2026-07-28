"""Nested-group tree — a ClassGroup can contain sub-groups to any depth."""
from rest_framework.test import APITestCase

from accounts.models import User
from assessments.models import ClassGroup


class GroupTreeTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user(email="tree@o.com", password="Str0ng!pass")

    def _login(self):
        r = self.client.post(
            "/api/v1/auth/login/", {"email": self.user.email, "password": "Str0ng!pass"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _rows(self, resp):
        return resp.data["results"] if isinstance(resp.data, dict) else resp.data

    def test_create_nested_groups_and_list_by_parent(self):
        self._login()
        cls = self.client.post(
            "/api/v1/classes/", {"name": "Class 10", "kind_label": "Class"}, format="json"
        )
        self.assertEqual(cls.status_code, 201, cls.data)
        self.assertIsNone(cls.data["parent"])
        cid = cls.data["id"]

        sec = self.client.post(
            "/api/v1/classes/",
            {"name": "Section A", "kind_label": "Section", "parent": cid},
            format="json",
        )
        self.assertEqual(sec.status_code, 201, sec.data)
        self.assertEqual(str(sec.data["parent"]), str(cid))
        self.assertEqual(sec.data["kind_label"], "Section")
        sid = sec.data["id"]

        # infinite nesting — a group under the section
        sub = self.client.post("/api/v1/classes/", {"name": "Group 1", "parent": sid}, format="json")
        self.assertEqual(sub.status_code, 201, sub.data)

        # children of the class = [section]
        self.assertEqual([r["id"] for r in self._rows(self.client.get(f"/api/v1/classes/?parent={cid}"))], [sid])
        # top-level = the class, not its descendants
        top_ids = [r["id"] for r in self._rows(self.client.get("/api/v1/classes/?parent=none"))]
        self.assertIn(cid, top_ids)
        self.assertNotIn(sid, top_ids)

    def test_cross_scope_parent_rejected(self):
        other = User.objects.create_user(email="other@o.com", password="Str0ng!pass")
        other_cls = ClassGroup.objects.create(user=other, created_by=other, name="Theirs")
        self._login()
        r = self.client.post("/api/v1/classes/", {"name": "Mine", "parent": other_cls.id}, format="json")
        self.assertIn(r.status_code, (400, 403, 404), r.data)
