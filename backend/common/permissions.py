from rest_framework.permissions import IsAuthenticated

from organizations.models import OrganizationMembership


class IsInScope(IsAuthenticated):
    """Global default permission. Requires authentication everywhere, and at the object level
    confirms the row belongs to the requester's current scope.

    Solo scope  : obj.user_id == request.user.id
    Org scope   : obj.organization_id is set AND the user is an active member of that org.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Solo path: object owned by this user directly.
        user_id = getattr(obj, "user_id", None)
        if user_id is not None and user_id == request.user.id:
            return True

        # Org path: object owned by an organization the user actively belongs to.
        org_id = getattr(obj, "organization_id", None)
        if org_id is not None:
            return OrganizationMembership.objects.filter(
                organization_id=org_id,
                user=request.user,
                status=OrganizationMembership.ACTIVE,
            ).exists()

        return False
