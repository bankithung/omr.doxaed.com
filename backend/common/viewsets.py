from rest_framework import viewsets

from common.permissions import IsInScope
from common.scope import scope_filter, scope_kwargs


class ScopedModelViewSet(viewsets.ModelViewSet):
    """Tenant-owned resources — routes through the active scope (solo or org).

    * Solo (no X-Organization-Id header): filters to request.user, stamps user= on create.
    * Org (valid X-Organization-Id header + active membership): filters to org,
      stamps organization= on create.

    ``owner_extra_fields`` names extra FK fields (e.g. ``created_by``) that are
    always stamped with ``request.user`` regardless of scope.
    """

    permission_classes = [IsInScope]
    owner_extra_fields = ()  # e.g. ("created_by",)

    def get_queryset(self):
        return super().get_queryset().filter(scope_filter(self.request))

    def perform_create(self, serializer):
        extra = {f: self.request.user for f in self.owner_extra_fields}
        serializer.save(**scope_kwargs(self.request), **extra)
