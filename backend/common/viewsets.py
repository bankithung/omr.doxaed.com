from rest_framework import viewsets

from common.permissions import IsInScope


class ScopedModelViewSet(viewsets.ModelViewSet):
    """Tenant-owned resources, solo scope. Filters to request.user and stamps the owner on create.
    Org scope (membership) arrives in Phase 6."""

    permission_classes = [IsInScope]
    owner_extra_fields = ()  # e.g. ("created_by",)

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        extra = {f: self.request.user for f in self.owner_extra_fields}
        serializer.save(user=self.request.user, **extra)
