"""Per-teacher class + subject access control — isolation + behaviour tests.

The security crux of the feature: an org MEMBER must only ever see/act on the
classes (and, when narrowed, the subjects) an admin granted them. Every test
here proves a boundary; do not weaken `common/scope.py` without one.
"""
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Organization, OrganizationMembership, ClassAccessGrant
from assessments.models import ClassGroup, Subject


class ClassAccessGrantModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="a@o.com", password="Str0ng!pass")
        self.teacher = User.objects.create_user(email="t@o.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="O", owner=self.admin)
        self.cls = ClassGroup.objects.create(
            organization=self.org, created_by=self.admin, name="10A"
        )

    def test_grant_defaults_to_all_subjects(self):
        g = ClassAccessGrant.objects.create(
            organization=self.org, user=self.teacher, class_group=self.cls
        )
        self.assertTrue(g.all_subjects)
        self.assertEqual(g.subjects.count(), 0)

    def test_grant_is_unique_per_org_user_class(self):
        ClassAccessGrant.objects.create(
            organization=self.org, user=self.teacher, class_group=self.cls
        )
        with self.assertRaises(IntegrityError):
            ClassAccessGrant.objects.create(
                organization=self.org, user=self.teacher, class_group=self.cls
            )

    def test_narrowed_grant_links_subjects(self):
        math = Subject.objects.create(class_group=self.cls, name="Math")
        Subject.objects.create(class_group=self.cls, name="Physics")
        g = ClassAccessGrant.objects.create(
            organization=self.org, user=self.teacher, class_group=self.cls, all_subjects=False
        )
        g.subjects.add(math)
        self.assertFalse(g.all_subjects)
        self.assertEqual(list(g.subjects.values_list("name", flat=True)), ["Math"])


class ClassAccessGrantApiTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.admin = User.objects.create_user(email="adm@o.com", password="Str0ng!pass")
        self.teacher = User.objects.create_user(email="tch@o.com", password="Str0ng!pass")
        self.outsider = User.objects.create_user(email="out@o.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="O", owner=self.admin)
        OrganizationMembership.objects.create(organization=self.org, user=self.admin, role="admin", status="active")
        OrganizationMembership.objects.create(organization=self.org, user=self.teacher, role="member", status="active")
        self.cls = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="10A")
        self.math = Subject.objects.create(class_group=self.cls, name="Math")
        # Second org + class — for cross-org isolation.
        self.org2 = Organization.objects.create(name="O2", owner=self.outsider)
        OrganizationMembership.objects.create(organization=self.org2, user=self.outsider, role="admin", status="active")
        self.cls2 = ClassGroup.objects.create(organization=self.org2, created_by=self.outsider, name="X")

    def _login(self, user):
        r = self.client.post("/api/v1/auth/login/", {"email": user.email, "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _h(self, org=None):
        return {"HTTP_X_ORGANIZATION_ID": str((org or self.org).id)}

    def _post(self, body, h=None):
        return self.client.post("/api/v1/class-grants/", body, format="json", **(h or self._h()))

    def test_member_cannot_create_grant(self):
        self._login(self.teacher)
        self.assertEqual(self._post({"user": self.teacher.id, "class_group": self.cls.id}).status_code, 403)

    def test_solo_no_header_cannot_create_grant(self):
        self._login(self.admin)
        r = self.client.post("/api/v1/class-grants/", {"user": self.teacher.id, "class_group": self.cls.id}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_admin_creates_grant_all_subjects(self):
        self._login(self.admin)
        r = self._post({"user": self.teacher.id, "class_group": self.cls.id})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data["all_subjects"])

    def test_admin_cannot_grant_cross_org_class(self):
        self._login(self.admin)
        self.assertEqual(self._post({"user": self.teacher.id, "class_group": self.cls2.id}).status_code, 400)

    def test_admin_cannot_grant_non_member(self):
        self._login(self.admin)
        self.assertEqual(self._post({"user": self.outsider.id, "class_group": self.cls.id}).status_code, 400)

    def test_list_filters_by_class_group(self):
        self._login(self.admin)
        self._post({"user": self.teacher.id, "class_group": self.cls.id})
        r = self.client.get(f"/api/v1/class-grants/?class_group={self.cls.id}", **self._h())
        self.assertEqual(r.status_code, 200)
        data = r.data["results"] if isinstance(r.data, dict) else r.data
        self.assertEqual(len(data), 1)

    def test_narrowed_grant_with_subjects(self):
        self._login(self.admin)
        r = self._post({"user": self.teacher.id, "class_group": self.cls.id, "all_subjects": False, "subjects": [self.math.id]})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertFalse(r.data["all_subjects"])
        self.assertEqual(r.data["subject_names"], ["Math"])


class ClassVisibilityViaGrantTests(APITestCase):
    """The crux: a member sees/edits an org class ONLY with a grant; admins see
    all; a grant never leaks across orgs."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.admin = User.objects.create_user(email="adm2@o.com", password="Str0ng!pass")
        self.teacher = User.objects.create_user(email="tch2@o.com", password="Str0ng!pass")
        self.outsider = User.objects.create_user(email="out2@o.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="O", owner=self.admin)
        OrganizationMembership.objects.create(organization=self.org, user=self.admin, role="admin", status="active")
        OrganizationMembership.objects.create(organization=self.org, user=self.teacher, role="member", status="active")
        self.cls = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="Granted")
        self.org2 = Organization.objects.create(name="O2", owner=self.outsider)
        OrganizationMembership.objects.create(organization=self.org2, user=self.outsider, role="admin", status="active")

    def _login(self, user):
        r = self.client.post("/api/v1/auth/login/", {"email": user.email, "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _h(self, org=None):
        return {"HTTP_X_ORGANIZATION_ID": str((org or self.org).id)}

    def _class_ids(self, h=None):
        r = self.client.get("/api/v1/classes/", **(h or self._h()))
        data = r.data["results"] if isinstance(r.data, dict) else r.data
        return r.status_code, [c["id"] for c in data]

    def _grant(self):
        ClassAccessGrant.objects.create(organization=self.org, user=self.teacher, class_group=self.cls)

    def test_member_without_grant_cannot_see_class(self):
        self._login(self.teacher)
        code, ids = self._class_ids()
        self.assertEqual(code, 200)
        self.assertNotIn(self.cls.id, ids)
        self.assertEqual(self.client.get(f"/api/v1/classes/{self.cls.id}/", **self._h()).status_code, 404)

    def test_member_with_grant_sees_and_reads_class(self):
        self._grant()
        self._login(self.teacher)
        code, ids = self._class_ids()
        self.assertIn(self.cls.id, ids)
        self.assertEqual(self.client.get(f"/api/v1/classes/{self.cls.id}/", **self._h()).status_code, 200)

    def test_member_without_grant_cannot_create_test(self):
        self._login(self.teacher)
        r = self.client.post("/api/v1/tests/", {"class_group": self.cls.id, "title": "T1"}, format="json", **self._h())
        self.assertEqual(r.status_code, 403)

    def test_member_with_grant_can_create_test(self):
        self._grant()
        self._login(self.teacher)
        r = self.client.post("/api/v1/tests/", {"class_group": self.cls.id, "title": "T1"}, format="json", **self._h())
        self.assertNotEqual(r.status_code, 403, r.data)  # access gate passed (grant = edit)

    def test_admin_sees_all_classes(self):
        self._login(self.admin)
        _, ids = self._class_ids()
        self.assertIn(self.cls.id, ids)

    def test_grant_does_not_leak_into_other_org(self):
        self._grant()
        self._login(self.teacher)
        # teacher is not a member of org2 → using org2's header is 403 regardless.
        self.assertEqual(self.client.get("/api/v1/classes/", **self._h(self.org2)).status_code, 403)
