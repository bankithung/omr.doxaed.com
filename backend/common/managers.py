from django.db import models


class ScopedQuerySet(models.QuerySet):
    """Filters tenant-owned rows to a single owner scope (solo user XOR organization)."""

    def in_scope(self, *, user=None, organization=None):
        if organization is not None:
            return self.filter(organization=organization)
        if user is not None:
            return self.filter(user=user)
        return self.none()


class ScopedManager(models.Manager.from_queryset(ScopedQuerySet)):
    pass
