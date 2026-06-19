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

    # A malformed header (non-numeric / not a valid pk) is a bad request, NOT a
    # server error: a stale or garbage `X-Organization-Id` (e.g. the string
    # "undefined" left in localStorage) must never 500 the request — it would
    # otherwise raise ValueError when cast to the membership FK's integer.
    try:
        org_id = int(org_id)
    except (TypeError, ValueError):
        raise PermissionDenied("Invalid organization.")

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


def visibility_q(request, class_prefix="", row_creator_prefix="created_by"):
    """ORG-scope folder-visibility predicate. AND this with scope_filter(request).
    SOLO scope and ADMINs → Q() (no-op; admin = full org access, bounded to the
    active org via request._membership). class_prefix = FK path to the governing
    ClassGroup ("" when the row IS the ClassGroup). row_creator_prefix = FK path to
    the row's own created_by (used for class-less rows, e.g. orphan rosters).

    NOTE: because shares__ is a reverse join, a queryset filtered with this Q can
    yield duplicate rows — every get_queryset using visibility_q MUST end with
    ``.distinct()``.
    """
    # Importing here avoids an app-loading import cycle (folders → common).
    from folders.models import FolderShare

    org = get_active_org(request)
    if org is None:
        return Q()  # solo: folders never apply
    membership = getattr(request, "_membership", None)
    if membership is not None and membership.role == OrganizationMembership.ADMIN:
        return Q()  # admin: full access within active org
    user = request.user
    cp = class_prefix
    fp = f"{cp}folder__"
    q = (
        Q(**{f"{fp}created_by": user})
        | Q(**{f"{fp}shares__shared_with": user})
        | Q(**{f"{fp}shares__share_scope": FolderShare.SHARE_ORG})
    )
    # loose class (folder IS NULL): visible to the governing class's creator
    if cp:
        q |= (
            Q(**{f"{cp}folder__isnull": True})
            & ~Q(**{f"{cp}isnull": True})
            & Q(**{f"{cp}created_by": user})
        )
        # class-less row (e.g. orphan roster): visible to the row's own creator
        q |= (Q(**{f"{cp}isnull": True}) & Q(**{row_creator_prefix: user}))
    else:
        q |= (Q(**{"folder__isnull": True}) & Q(**{"created_by": user}))
    # Direct per-teacher access grant — an admin granted this member the governing
    # class (Phase: class+subject access control). The class is already org-scoped
    # by scope_filter, so a grant on it can only come from THIS org.
    q |= Q(**{f"{cp}access_grants__user": user})
    return q


def is_active_admin(request):
    """True if the request is in org scope AND the requester is an ACTIVE ADMIN of
    the active org (bounded to the active X-Organization-Id via request._membership).
    """
    org = get_active_org(request)
    if org is None:
        return False
    membership = getattr(request, "_membership", None)
    return membership is not None and membership.role == OrganizationMembership.ADMIN


def can_edit_class(request, class_group):
    """EDIT-rights predicate for a folder-governed resource (Step 4).

    List/retrieve is allowed for ANY visibility grant; create/update/delete on a
    folder-governed resource requires EDIT rights:
      * SOLO scope            → owner (already enforced by scope_filter) → True
      * ACTIVE-ORG ADMIN      → True (admins have full edit per the owner decision)
      * folder creator        → True
      * an EDIT FolderShare   → True (member-share to this user OR an org-wide
                                 EDIT share), provided the user is an active member
      * loose class (folder=None) → only its own creator may edit
    A VIEW-only grant returns False (→ caller raises 403).

    `class_group` may be None (class-less resource) — then only solo/admin/creator
    of the row applies and the caller is responsible for the creator check.
    """
    from folders.models import FolderShare

    org = get_active_org(request)
    if org is None:
        return True  # solo: scope_filter already proved ownership
    if is_active_admin(request):
        return True
    # A direct per-teacher access grant in the active org = edit rights on that
    # class (create/update tests, rosters, subjects under it).
    from organizations.models import ClassAccessGrant
    if class_group is not None and ClassAccessGrant.objects.filter(
        organization=org.id, user=request.user, class_group=class_group
    ).exists():
        return True
    if class_group is None:
        return False
    user = request.user
    folder = getattr(class_group, "folder", None)
    if folder is None:
        # Loose class: only the class creator may edit.
        return class_group.created_by_id == user.id
    if folder.created_by_id == user.id:
        return True
    # Must be an active member of the folder's org to inherit a share.
    if not OrganizationMembership.objects.filter(
        organization_id=org.id,
        user=user,
        status=OrganizationMembership.ACTIVE,
    ).exists():
        return False
    return FolderShare.objects.filter(
        Q(folder=folder),
        Q(permission=FolderShare.PERM_EDIT),
        Q(shared_with=user) | Q(share_scope=FolderShare.SHARE_ORG),
    ).exists()
