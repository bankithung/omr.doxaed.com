from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .emails import send_invitation_email
from .models import AuditLog, Invitation, Organization, OrganizationMembership
from .serializers import (
    AcceptInviteSerializer,
    AuditLogSerializer,
    InviteSerializer,
    MemberRoleSerializer,
    MembershipSerializer,
    OrganizationSerializer,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_membership(request, org_id, role=None):
    """Return the active OrganizationMembership for request.user in org_id.

    Raises:
        Http404      if the org doesn't exist.
        PermissionDenied (→ 403) if the user is not an active member.
        PermissionDenied (→ 403) if `role` is specified and the membership role
                         does not match (e.g. require admin but user is member).
    """
    org = get_object_or_404(Organization, pk=org_id)
    membership = OrganizationMembership.objects.filter(
        organization=org, user=request.user, status=OrganizationMembership.ACTIVE
    ).first()
    if not membership:
        raise PermissionDenied("Not an active member of this organization.")
    if role and membership.role != role:
        raise PermissionDenied(f"This action requires the '{role}' role.")
    return membership


def _active_admin_count(org):
    """Return the count of active admin members in org."""
    return OrganizationMembership.objects.filter(
        organization=org,
        role=OrganizationMembership.ADMIN,
        status=OrganizationMembership.ACTIVE,
    ).count()


def _log(org, actor, action, target_type="", target_id=None, metadata=None):
    AuditLog.objects.create(
        organization=org,
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Organization list / create
# ---------------------------------------------------------------------------

class OrganizationListCreateView(APIView):
    """
    GET  /api/v1/organizations/  → list orgs the user is an active member of.
    POST /api/v1/organizations/  → create an org (owner=request.user).

    # TODO Phase 7: require active subscription before allowing org creation.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            OrganizationMembership.objects.filter(
                user=request.user, status=OrganizationMembership.ACTIVE
            )
            .select_related("organization")
        )
        results = []
        for m in memberships:
            data = OrganizationSerializer(m.organization).data
            data["role"] = m.role
            results.append(data)
        return Response(results)

    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = Organization.objects.create(
            name=serializer.validated_data["name"],
            owner=request.user,
        )
        # Creator becomes an active admin.
        OrganizationMembership.objects.create(
            organization=org,
            user=request.user,
            role=OrganizationMembership.ADMIN,
            status=OrganizationMembership.ACTIVE,
        )
        _log(org, request.user, "org.created", target_type="organization", target_id=org.id)
        out = OrganizationSerializer(org).data
        out["role"] = OrganizationMembership.ADMIN
        return Response(out, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------

class InviteView(APIView):
    """POST /api/v1/organizations/{id}/invite/ — admin only."""

    permission_classes = [IsAuthenticated]

    def post(self, request, org_id):
        membership = require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = membership.organization

        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]

        # Check for existing active membership with that email.
        target_user = User.objects.filter(email__iexact=email).first()
        if target_user:
            existing = OrganizationMembership.objects.filter(
                organization=org,
                user=target_user,
                status=OrganizationMembership.ACTIVE,
            ).first()
            if existing:
                return Response(
                    {"detail": "This user is already an active member."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        invitation = Invitation.objects.create(
            organization=org,
            email=email,
            role=role,
            invited_by=request.user,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        send_invitation_email(invitation)
        _log(
            org,
            request.user,
            "member.invited",
            target_type="invitation",
            target_id=invitation.id,
            metadata={"email": email, "role": role},
        )
        return Response(
            {
                "detail": "Invitation sent.",
                "email": email,
                "role": role,
                "token": str(invitation.token),
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Accept Invitation
# ---------------------------------------------------------------------------

class AcceptInviteView(APIView):
    """POST /api/v1/invitations/accept/ — authenticated user accepts by token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        invitation = Invitation.objects.filter(token=token).select_related("organization").first()

        # Invalid token.
        if invitation is None:
            return Response(
                {"detail": "Invalid or expired invitation token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Already accepted.
        if invitation.accepted_at is not None:
            return Response(
                {"detail": "This invitation has already been accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Expired.
        if timezone.now() > invitation.expires_at:
            return Response(
                {"detail": "This invitation has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Email mismatch.
        if request.user.email.lower() != invitation.email.lower():
            return Response(
                {"detail": "This invitation was sent to a different email address."},
                status=status.HTTP_403_FORBIDDEN,
            )

        org = invitation.organization

        # Create or re-activate membership.
        membership, created = OrganizationMembership.objects.get_or_create(
            organization=org,
            user=request.user,
            defaults={
                "role": invitation.role,
                "status": OrganizationMembership.ACTIVE,
            },
        )
        if not created:
            membership.role = invitation.role
            membership.status = OrganizationMembership.ACTIVE
            membership.save(update_fields=["role", "status"])

        # Mark invitation accepted.
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])

        _log(
            org,
            request.user,
            "member.joined",
            target_type="user",
            target_id=request.user.id,
            metadata={"email": request.user.email, "role": invitation.role},
        )

        return Response(
            {
                "detail": "Invitation accepted. You are now a member.",
                "organization": org.id,
                "role": membership.role,
            }
        )


# ---------------------------------------------------------------------------
# Member list / management
# ---------------------------------------------------------------------------

class MemberListView(APIView):
    """GET /api/v1/organizations/{id}/members/ — any active member."""

    permission_classes = [IsAuthenticated]

    def get(self, request, org_id):
        require_membership(request, org_id)  # any active member
        org = get_object_or_404(Organization, pk=org_id)
        memberships = (
            OrganizationMembership.objects.filter(organization=org)
            .exclude(status=OrganizationMembership.REMOVED)
            .select_related("user")
            .order_by("joined_at")
        )
        serializer = MembershipSerializer(memberships, many=True)
        return Response(serializer.data)


class MemberDetailView(APIView):
    """
    PATCH /api/v1/organizations/{id}/members/{user_id}/ — admin changes role.
    DELETE /api/v1/organizations/{id}/members/{user_id}/ — admin removes member.
    """

    permission_classes = [IsAuthenticated]

    def _get_target(self, org, user_id):
        return get_object_or_404(
            OrganizationMembership,
            organization=org,
            user_id=user_id,
            status=OrganizationMembership.ACTIVE,
        )

    def patch(self, request, org_id, user_id):
        admin_membership = require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = admin_membership.organization

        target = self._get_target(org, user_id)
        serializer = MemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        # Last-admin protection: cannot demote the only remaining active admin.
        if (
            target.role == OrganizationMembership.ADMIN
            and new_role != OrganizationMembership.ADMIN
            and _active_admin_count(org) <= 1
        ):
            return Response(
                {"detail": "Cannot demote the only active admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_role = target.role
        target.role = new_role
        target.save(update_fields=["role"])

        _log(
            org,
            request.user,
            "member.role_changed",
            target_type="user",
            target_id=target.user_id,
            metadata={"from_role": old_role, "to_role": new_role},
        )
        return Response(MembershipSerializer(target).data)

    def delete(self, request, org_id, user_id):
        admin_membership = require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = admin_membership.organization

        target = self._get_target(org, user_id)

        # Last-admin protection.
        if (
            target.role == OrganizationMembership.ADMIN
            and _active_admin_count(org) <= 1
        ):
            return Response(
                {"detail": "Cannot remove the only active admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target.status = OrganizationMembership.REMOVED
        target.save(update_fields=["status"])

        _log(
            org,
            request.user,
            "member.removed",
            target_type="user",
            target_id=target.user_id,
            metadata={"email": target.user.email},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class AuditLogView(APIView):
    """GET /api/v1/organizations/{id}/audit/ — admin only, newest first."""

    permission_classes = [IsAuthenticated]

    def get(self, request, org_id):
        require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = get_object_or_404(Organization, pk=org_id)
        logs = AuditLog.objects.filter(organization=org).select_related("actor").order_by("-created_at")

        # Minimal pagination: honour ?page and PAGE_SIZE from DRF settings.
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(logs, request)
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)
