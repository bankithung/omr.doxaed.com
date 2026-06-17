from django.core.exceptions import PermissionDenied
from django.db.models import Q

from organizations.models import OrganizationMembership


def get_active_org(request):
    """Return the active Organization for this request, or None for solo scope.

    Reads the `X-Organization-Id` header ONLY.  If set, verifies the user has
    an *active* membership; raises PermissionDenied otherwise.  Caches the
    result on the request object to avoid repeated DB hits within the same
    request cycle.

    Header-only by design: a `?org=` query-param fallback would be
    CSRF-reachable (a cross-origin GET could append `?org=`), so org activation
    is restricted to the custom header the frontend already sends.
    """
    if hasattr(request, "_active_org_resolved"):
        return request._active_org_cache

    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        request._active_org_resolved = True
        request._active_org_cache = None
        return None

    m = (
        OrganizationMembership.objects.filter(
            organization_id=org_id,
            user=request.user,
            status=OrganizationMembership.ACTIVE,
        )
        .select_related("organization")
        .first()
    )
    if not m:
        raise PermissionDenied("Not a member of this organization.")

    request._active_org_resolved = True
    request._active_org_cache = m.organization
    request._membership = m
    return m.organization


def scope_filter(request, prefix=""):
    """Return a Q object that filters a queryset to the current scope.

    Solo scope  → Q(user=request.user)
    Org scope   → Q(organization=org)

    Pass `prefix` for child FK chains, e.g. ``prefix="test__"``.
    """
    org = get_active_org(request)
    if org is not None:
        return Q(**{f"{prefix}organization": org})
    return Q(**{f"{prefix}user": request.user})


def scope_kwargs(request):
    """Return the dict of kwargs to stamp on a new object.

    Solo scope  → {'user': request.user}
    Org scope   → {'organization': org}

    Note: only one key is returned — never both — so the OwnerScopedModel
    XOR CheckConstraint is satisfied.
    """
    org = get_active_org(request)
    return {"organization": org} if org is not None else {"user": request.user}


def parent_in_scope(value, request):
    """Return True if the parent FK object `value` belongs to the current scope.

    Solo scope  → parent.user_id == request.user.id
    Org scope   → parent.organization_id == active_org.id
    """
    org = get_active_org(request)
    if org is not None:
        return getattr(value, "organization_id", None) == org.id
    return getattr(value, "user_id", None) == request.user.id
