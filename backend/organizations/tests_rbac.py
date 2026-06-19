"""RBAC — roles, scoped bindings, individual grants, and has_perm()."""
from django.test import TestCase
from rest_framework.test import APIRequestFactory

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
            ["Admin", "Owner", "Teacher", "Viewer"],
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
