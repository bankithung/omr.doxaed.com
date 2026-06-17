from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Phase 0 skeleton. Membership, invitations, roles, audit log arrive in Phase 6.
    Exists now because the owner-scope foundation references this table."""

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
