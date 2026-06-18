from rest_framework.permissions import IsAuthenticated

from organizations.models import OrganizationMembership


class IsInScope(IsAuthenticated):
    """Global default permission. Requires authentication everywhere, and at the object level
    confirms the row belongs to the requester's current scope AND is visible to them.

    Solo scope  : obj.user_id == request.user.id
    Org scope   : obj.organization_id is set AND the user is an active member of that org.

    Folder visibility (Product v2 Phase 5B): for views that expose a scoped
    ``get_queryset`` (which already ANDs scope_filter & visibility_q), object
    permission is decided by *re-running the SAME predicate* —
    ``view.get_queryset().filter(pk=obj.pk).exists()``. This guarantees identical
    list/object semantics: a member who cannot list object X cannot retrieve,
    update or delete it either (no list/object drift, no IDOR). Active-org admins
    short-circuit to full access. Solo objects and non-scoped views fall back to
    the original user_id / org-membership check.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Solo path: object owned by this user directly (folders never apply solo).
        user_id = getattr(obj, "user_id", None)
        if user_id is not None and user_id == request.user.id:
            return True

        # Reuse the view's scoped queryset predicate so object perms == list perms
        # EXACTLY (no list/object drift, no IDOR). The viewset's get_queryset
        # already ANDs scope_filter & visibility_q; for an active-org admin
        # visibility_q is a no-op (full org pool) while scope_filter still bounds
        # it to the active org — so the same call correctly grants admins full
        # access without leaking other orgs' rows. ScopedModelViewSet and any
        # viewset overriding get_queryset qualify.
        get_queryset = getattr(view, "get_queryset", None)
        if callable(get_queryset):
            try:
                qs = view.get_queryset()
            except Exception:
                qs = None
            if qs is not None and qs.model is type(obj):
                return qs.filter(pk=obj.pk).exists()

        # Non-scoped view (e.g. organizations/billing) OR queryset model mismatch:
        # fall back to the original org-membership check (active members — admin
        # or not — keep access to their org's rows under those views).
        return self._org_member_ok(request, obj)

    @staticmethod
    def _org_member_ok(request, obj):
        org_id = getattr(obj, "organization_id", None)
        if org_id is not None:
            return OrganizationMembership.objects.filter(
                organization_id=org_id,
                user=request.user,
                status=OrganizationMembership.ACTIVE,
            ).exists()
        return False
