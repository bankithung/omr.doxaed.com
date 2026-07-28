"""RBAC — roles, scoped bindings, individual grants, and has_perm()."""
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APITestCase

from accounts.models import User
from assessments.models import ClassGroup
from common.scope import has_perm
from organizations.models import (
    Organization,
    OrganizationMembership,
    Role,
    RoleBinding,
    PermissionGrant,
)
from organizations.role_seed import seed_org_roles
from organizations import permissions_catalog as P

_factory = APIRequestFactory()


def _req(user, org):
    r = _factory.get("/", HTTP_X_ORGANIZATION_ID=str(org.id))
    r.user = user
    return r


class RoleSeedTests(TestCase):
    def test_seed_creates_system_roles_and_owner_binding(self):
        owner = User.objects.create_user(email="o@o.com", password="Str0ng!pass")
        org = Organization.objects.create(name="O", owner=owner)
        seed_org_roles(org, owner)
        self.assertEqual(
            sorted(Role.objects.filter(organization=org).values_list("name", flat=True)),
            ["Admin", "Office", "Owner", "Supervisor", "Teacher", "Viewer"],
        )
        self.assertTrue(
            RoleBinding.objects.filter(organization=org, user=owner, role__name="Owner").exists()
        )


class HasPermTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="adm@o.com", password="Str0ng!pass")
        self.teacher = User.objects.create_user(email="tch@o.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="O", owner=self.admin)
        OrganizationMembership.objects.create(organization=self.org, user=self.admin, role="admin", status="active")
        OrganizationMembership.objects.create(organization=self.org, user=self.teacher, role="member", status="active")
        self.roles = seed_org_roles(self.org, self.admin)
        self.a = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="A", kind_label="Class")
        self.a1 = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="A1", parent=self.a, kind_label="Section")
        self.b = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="B", kind_label="Class")

    def test_admin_has_everything(self):
        r = _req(self.admin, self.org)
        self.assertTrue(has_perm(r, self.org, P.EXAM_CREATE, group=self.a))
        self.assertTrue(has_perm(r, self.org, P.ROLE_MANAGE))

    def test_owner_binding_without_admin_membership(self):
        owner = User.objects.create_user(email="own@o.com", password="Str0ng!pass")
        OrganizationMembership.objects.create(organization=self.org, user=owner, role="member", status="active")
        RoleBinding.objects.create(organization=self.org, user=owner, role=self.roles["Owner"])
        self.assertTrue(has_perm(_req(owner, self.org), self.org, P.ROLE_MANAGE))

    def test_scoped_teacher_binding(self):
        RoleBinding.objects.create(
            organization=self.org, user=self.teacher, role=self.roles["Teacher"], scope_group=self.a
        )
        r = _req(self.teacher, self.org)
        self.assertTrue(has_perm(r, self.org, P.EXAM_CREATE, group=self.a))       # the class
        self.assertTrue(has_perm(r, self.org, P.EXAM_CREATE, group=self.a1))      # a descendant
        self.assertFalse(has_perm(r, self.org, P.EXAM_CREATE, group=self.b))      # a sibling
        self.assertFalse(has_perm(r, self.org, P.MEMBER_INVITE))                  # org-wide → no

    def test_individual_grant(self):
        PermissionGrant.objects.create(
            organization=self.org, user=self.teacher, permission=P.EXAM_GRADE, scope_group=self.a
        )
        r = _req(self.teacher, self.org)
        self.assertTrue(has_perm(r, self.org, P.EXAM_GRADE, group=self.a))
        self.assertFalse(has_perm(r, self.org, P.EXAM_GRADE, group=self.b))

    def test_viewer_role(self):
        RoleBinding.objects.create(
            organization=self.org, user=self.teacher, role=self.roles["Viewer"], scope_group=self.a
        )
        r = _req(self.teacher, self.org)
        self.assertTrue(has_perm(r, self.org, P.EXAM_RESULTS_VIEW, group=self.a))
        self.assertFalse(has_perm(r, self.org, P.EXAM_CREATE, group=self.a))

    def test_member_without_any_role_has_nothing(self):
        r = _req(self.teacher, self.org)
        self.assertFalse(has_perm(r, self.org, P.EXAM_CREATE, group=self.a))
        self.assertFalse(has_perm(r, self.org, P.ROLE_MANAGE))


class RbacApiIntegrationTests(APITestCase):
    """RBAC role bindings gate the real API (visibility_q + can_edit_class)."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.admin = User.objects.create_user(email="adm2@o.com", password="Str0ng!pass")
        self.teacher = User.objects.create_user(email="tch2@o.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="O", owner=self.admin)
        OrganizationMembership.objects.create(organization=self.org, user=self.admin, role="admin", status="active")
        OrganizationMembership.objects.create(organization=self.org, user=self.teacher, role="member", status="active")
        self.roles = seed_org_roles(self.org, self.admin)
        self.a = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="A", kind_label="Class")
        self.b = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="B", kind_label="Class")

    def _login(self, u):
        r = self.client.post("/api/v1/auth/login/", {"email": u.email, "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _h(self):
        return {"HTTP_X_ORGANIZATION_ID": str(self.org.id)}

    def _class_ids(self):
        r = self.client.get("/api/v1/classes/", **self._h())
        data = r.data["results"] if isinstance(r.data, dict) else r.data
        return [c["id"] for c in data]

    def test_teacher_binding_grants_visibility_and_edit(self):
        from organizations.models import RoleBinding
        RoleBinding.objects.create(
            organization=self.org, user=self.teacher, role=self.roles["Teacher"], scope_group=self.a
        )
        self._login(self.teacher)
        ids = self._class_ids()
        self.assertIn(str(self.a.id), ids)
        self.assertNotIn(str(self.b.id), ids)
        # can create a test under A
        ra = self.client.post("/api/v1/tests/", {"class_group": self.a.id, "title": "T"}, format="json", **self._h())
        self.assertNotEqual(ra.status_code, 403, ra.data)
        # cannot under B
        rb = self.client.post("/api/v1/tests/", {"class_group": self.b.id, "title": "T"}, format="json", **self._h())
        self.assertEqual(rb.status_code, 403)

    def test_viewer_binding_sees_but_cannot_edit(self):
        from organizations.models import RoleBinding
        RoleBinding.objects.create(
            organization=self.org, user=self.teacher, role=self.roles["Viewer"], scope_group=self.a
        )
        self._login(self.teacher)
        self.assertEqual(self.client.get(f"/api/v1/classes/{self.a.id}/", **self._h()).status_code, 200)
        r = self.client.post("/api/v1/tests/", {"class_group": self.a.id, "title": "T"}, format="json", **self._h())
        self.assertEqual(r.status_code, 403)

    def test_admin_manages_roles_member_cannot(self):
        # member without role.manage → 403 on the roles endpoint
        self._login(self.teacher)
        self.assertEqual(self.client.get("/api/v1/roles/", **self._h()).status_code, 403)
        # admin creates a custom role + assigns a scoped binding
        self._login(self.admin)
        self.assertEqual(self.client.get("/api/v1/roles/", **self._h()).status_code, 200)
        cr = self.client.post(
            "/api/v1/roles/",
            {"name": "Grader", "permissions": ["exam.grade", "exam.results.view"]},
            format="json", **self._h(),
        )
        self.assertEqual(cr.status_code, 201, cr.data)
        rb = self.client.post(
            "/api/v1/role-bindings/",
            {"user": self.teacher.id, "role": cr.data["id"], "scope_group": self.a.id},
            format="json", **self._h(),
        )
        self.assertEqual(rb.status_code, 201, rb.data)
        # the permission catalog is available to any member
        self._login(self.teacher)
        cat = self.client.get("/api/v1/permissions/")
        self.assertEqual(cat.status_code, 200)
        self.assertTrue(any(item["code"] == "exam.grade" for item in cat.data))
