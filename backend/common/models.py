import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.managers import ScopedManager


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class OwnerScopedModel(UUIDModel):
    """Abstract base: every tenant-owned row is owned by exactly one of `user` (solo) or
    `organization`. Enforced in the DB via a CheckConstraint and in Python via clean()."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ScopedManager()

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(user__isnull=False) & Q(organization__isnull=True))
                    | (Q(user__isnull=True) & Q(organization__isnull=False))
                ),
                name="%(app_label)s_%(class)s_exactly_one_scope",
            )
        ]

    def clean(self):
        if bool(self.user_id) == bool(self.organization_id):
            raise ValidationError("Exactly one of user or organization must be set.")
