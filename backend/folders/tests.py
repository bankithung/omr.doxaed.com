from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from folders.models import Folder, FolderShare
from organizations.models import Organization

User = get_user_model()


class FolderOwnerScopedXORTests(TestCase):
    """Folder inherits OwnerScopedModel: exactly one of user/organization must be set."""

    def setUp(self):
        self.user = User.objects.create_user(email="f@example.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="TestOrg", owner=self.user)

    def test_folder_with_both_user_and_org_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Folder.objects.create(
                    created_by=self.user,
                    name="Both",
                    user=self.user,
                    organization=self.org,
                )

    def test_folder_with_neither_user_nor_org_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Folder.objects.create(
                    created_by=self.user,
                    name="Neither",
                    # no user, no organization
                )

    def test_folder_with_user_only_succeeds(self):
        f = Folder.objects.create(created_by=self.user, name="UserFolder", user=self.user)
        self.assertEqual(f.name, "UserFolder")
        self.assertIsNone(f.organization_id)

    def test_folder_with_org_only_succeeds(self):
        f = Folder.objects.create(created_by=self.user, name="OrgFolder", organization=self.org)
        self.assertEqual(f.name, "OrgFolder")
        self.assertIsNone(f.user_id)


class FolderShareUniquenessTests(TestCase):
    """FolderShare uniqueness constraints."""

    def setUp(self):
        self.user = User.objects.create_user(email="fs@example.com", password="Str0ng!pass")
        self.user2 = User.objects.create_user(email="fs2@example.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="ShareOrg", owner=self.user)
        self.folder = Folder.objects.create(
            created_by=self.user, name="F", organization=self.org
        )

    def test_duplicate_member_share_raises_integrity_error(self):
        FolderShare.objects.create(
            folder=self.folder,
            shared_with=self.user2,
            share_scope=FolderShare.SHARE_MEMBER,
            permission=FolderShare.PERM_VIEW,
            created_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FolderShare.objects.create(
                    folder=self.folder,
                    shared_with=self.user2,
                    share_scope=FolderShare.SHARE_MEMBER,
                    permission=FolderShare.PERM_EDIT,
                    created_by=self.user,
                )

    def test_duplicate_org_share_raises_integrity_error(self):
        FolderShare.objects.create(
            folder=self.folder,
            shared_with=None,
            share_scope=FolderShare.SHARE_ORG,
            permission=FolderShare.PERM_VIEW,
            created_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FolderShare.objects.create(
                    folder=self.folder,
                    shared_with=None,
                    share_scope=FolderShare.SHARE_ORG,
                    permission=FolderShare.PERM_EDIT,
                    created_by=self.user,
                )

    def test_member_share_str(self):
        fs = FolderShare.objects.create(
            folder=self.folder,
            shared_with=self.user2,
            share_scope=FolderShare.SHARE_MEMBER,
            permission=FolderShare.PERM_VIEW,
            created_by=self.user,
        )
        self.assertIn("member", str(fs))
