from django.conf import settings
from django.db import models
from django.db.models import Q

from common.models import OwnerScopedModel, UUIDModel


class Folder(OwnerScopedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="folders_created",
    )
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    class Meta(OwnerScopedModel.Meta):
        pass

    def __str__(self):
        return self.name


class FolderShare(UUIDModel):
    SHARE_MEMBER = "member"
    SHARE_ORG = "org"
    PERM_VIEW = "view"
    PERM_EDIT = "edit"

    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="shares")
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="folder_shares",
    )
    share_scope = models.CharField(
        max_length=8,
        choices=[
            (SHARE_MEMBER, "Member"),
            (SHARE_ORG, "Whole organisation"),
        ],
        default=SHARE_MEMBER,
    )
    permission = models.CharField(
        max_length=8,
        choices=[
            (PERM_VIEW, "View"),
            (PERM_EDIT, "Edit"),
        ],
        default=PERM_VIEW,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="folder_shares_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["folder", "shared_with"],
                name="uniq_foldershare_member",
            ),
            models.UniqueConstraint(
                fields=["folder"],
                condition=Q(share_scope="org"),
                name="uniq_foldershare_org",
            ),
        ]

    def __str__(self):
        return f"FolderShare folder={self.folder_id} shared_with={self.shared_with_id} scope={self.share_scope}"
