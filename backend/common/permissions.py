from rest_framework.permissions import IsAuthenticated


class IsInScope(IsAuthenticated):
    """Global default permission. Requires authentication everywhere, and at the object level
    confirms the row belongs to the requester's solo scope.

    Phase 0 implements the solo (user) path. Organization-scoped object access depends on
    membership, which is modeled in Phase 6; until then org-scoped objects are denied here and
    list endpoints must scope their querysets via ScopedQuerySet.in_scope().
    """

    def has_object_permission(self, request, view, obj):
        user_id = getattr(obj, "user_id", None)
        if user_id is not None:
            return request.user.is_authenticated and user_id == request.user.id
        return False
