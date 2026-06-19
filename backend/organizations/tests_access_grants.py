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
