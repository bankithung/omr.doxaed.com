from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import billing.limits as billing_limits
from common.scope import get_active_org, is_active_admin

from .emails import send_invitation_email
from .models import AuditLog, ClassAccessGrant, Invitation, Organization, OrganizationMembership
from .serializers import (
    AcceptInviteSerializer,
    AuditLogSerializer,
    ClassAccessGrantSerializer,
    InviteSerializer,
    MemberRoleSerializer,
    MembershipSerializer,
    OrgBrandingSerializer,
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

    # Org creation is intentionally open; the free plan gates the org to 1 seat (admin). Paid plans unlock more seats/caps via billing.
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
            type=serializer.validated_data.get("type", Organization.OTHER),
            owner=request.user,
        )
        # Creator becomes an active admin.
        OrganizationMembership.objects.create(
            organization=org,
            user=request.user,
            role=OrganizationMembership.ADMIN,
            status=OrganizationMembership.ACTIVE,
        )
        # Seed the org's system roles (Owner/Admin/Teacher/Viewer) + bind the
        # creator to Owner so RBAC checks resolve from day one.
        from organizations.role_seed import seed_org_roles

        seed_org_roles(org, request.user)
        # SECURITY: the request may carry a `plan` for UX, but a paid plan is NEVER
        # activated here — that would be a payment bypass (any user could self-grant
        # a paid plan). New orgs start on Free; paid activation happens only through
        # the signature-verified Razorpay webhook (SubscribeView → webhook). The
        # `plan` field is intentionally ignored server-side. (Local testing without
        # a gateway: `manage.py set_org_plan <slug> <code>`.)
        _log(org, request.user, "org.created", target_type="organization", target_id=org.id)
        out = OrganizationSerializer(org).data
        out["role"] = OrganizationMembership.ADMIN
        return Response(out, status=status.HTTP_201_CREATED)


class OrgDetailView(APIView):
    """PATCH /api/v1/organizations/<id>/ — admin renames the org / changes its type.
    DELETE — the OWNER permanently deletes the organization (cascades its data)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, org_id):
        membership = require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = membership.organization
        serializer = OrganizationSerializer(org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if "name" in serializer.validated_data:
            org.name = serializer.validated_data["name"]
        if "type" in serializer.validated_data:
            org.type = serializer.validated_data["type"]
        if "slug" in serializer.validated_data:
            org.slug = serializer.validated_data["slug"]
        org.save()
        _log(org, request.user, "org.updated", target_type="organization", target_id=org.id)
        out = OrganizationSerializer(org).data
        out["role"] = membership.role
        return Response(out)

    def delete(self, request, org_id):
        org = get_object_or_404(Organization, pk=org_id)
        if org.owner_id != request.user.id:
            raise PermissionDenied("Only the organization owner can delete it.")
        org.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------

class InviteView(APIView):
    """POST /api/v1/organizations/{id}/invite/ — admin only."""

    permission_classes = [IsAuthenticated]

    def post(self, request, org_id):
        membership = require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = membership.organization

        # ---- seat gate -------------------------------------------------------
        if not billing_limits.can_add_seat(org):
            return Response(
                {
                    "detail": (
                        "Seat limit reached for your plan. "
                        "Upgrade to add more staff."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]

        # Granular RBAC role (optional) — derive the coarse membership role from it
        # so the admin gate stays consistent (Owner/Admin → admin, else member).
        from organizations.models import Role
        from organizations.permissions_catalog import ADMIN_ROLE_NAMES

        rbac_role = None
        rbac_role_id = request.data.get("rbac_role")
        if rbac_role_id:
            rbac_role = Role.objects.filter(organization=org, id=rbac_role_id).first()
            if rbac_role is None:
                return Response(
                    {"detail": "Invalid role for this organization."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            role = (
                OrganizationMembership.ADMIN
                if rbac_role.name in ADMIN_ROLE_NAMES
                else OrganizationMembership.MEMBER
            )

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
            rbac_role=rbac_role,
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

        # ---- seat gate (re-check at accept time) -----------------------------
        # An invite created while the org was on a paid plan can be accepted
        # after a downgrade.  Re-check the seat gate before granting a NEW active
        # seat.  Re-accepting your own already-active seat must still work, so
        # only gate when the user is not already an active member.
        already_active = OrganizationMembership.objects.filter(
            organization=org,
            user=request.user,
            status=OrganizationMembership.ACTIVE,
        ).exists()
        if not already_active and not billing_limits.can_add_seat(org):
            return Response(
                {"detail": "Seat limit reached for this organization's plan."},
                status=status.HTTP_403_FORBIDDEN,
            )

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

        # Apply the granular RBAC role as an org-wide binding.
        if invitation.rbac_role_id:
            from organizations.models import RoleBinding

            RoleBinding.objects.get_or_create(
                organization=org,
                user=request.user,
                role=invitation.rbac_role,
                scope_group=None,
                defaults={"granted_by": invitation.invited_by},
            )

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


# ---------------------------------------------------------------------------
# Org branding
# ---------------------------------------------------------------------------

class OrgBrandingView(APIView):
    """
    GET  /api/v1/organizations/<id>/branding/ — admin only.
    PUT  /api/v1/organizations/<id>/branding/ — admin only (multipart for logo).

    Returns / updates Organization.logo + Organization.default_sheet_heading.
    Non-members → 404 (via require_membership).
    Non-admin members → 403 (via require_membership).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, org_id):
        membership = require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = membership.organization
        serializer = OrgBrandingSerializer(org, context={"request": request})
        return Response(serializer.data)

    def put(self, request, org_id):
        membership = require_membership(request, org_id, role=OrganizationMembership.ADMIN)
        org = membership.organization
        serializer = OrgBrandingSerializer(
            org, data=request.data, partial=False, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _log(
            org,
            request.user,
            "org.branding_updated",
            target_type="organization",
            target_id=org.id,
        )
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Class access grants (per-teacher class + subject access control)
# ---------------------------------------------------------------------------

class ClassAccessGrantViewSet(viewsets.ModelViewSet):
    """Admin-only CRUD for per-teacher class+subject access grants in the ACTIVE
    org (resolved from the X-Organization-Id header). Members / solo users → 403.
    Filter with ?class_group=<id> or ?user=<id>."""

    serializer_class = ClassAccessGrantSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Every grant operation requires being an ACTIVE ADMIN of the active org.
        if not is_active_admin(request):
            raise PermissionDenied("Only an organization admin can manage access grants.")

    def get_queryset(self):
        org = get_active_org(self.request)  # guaranteed non-None by initial()
        qs = (
            ClassAccessGrant.objects.filter(organization=org)
            .select_related("user", "class_group")
            .prefetch_related("subjects")
            .order_by("class_group_id", "id")
        )
        cg = self.request.query_params.get("class_group")
        if cg:
            qs = qs.filter(class_group_id=cg)
        u = self.request.query_params.get("user")
        if u and u.isdigit():
            qs = qs.filter(user_id=int(u))
        return qs

    def perform_create(self, serializer):
        org = get_active_org(self.request)
        serializer.save(organization=org, granted_by=self.request.user)
        _log(org, self.request.user, "access.granted",
             target_type="class_grant", target_id=serializer.instance.id,
             metadata={"user_id": serializer.instance.user_id,
                       "class_group_id": serializer.instance.class_group_id})

    def perform_destroy(self, instance):
        org = get_active_org(self.request)
        _log(org, self.request.user, "access.revoked",
             target_type="class_grant", target_id=instance.id,
             metadata={"user_id": instance.user_id, "class_group_id": instance.class_group_id})
        instance.delete()


# ─── RBAC management (roles, scoped bindings, individual grants) ───────────────
# Gate: active-org admin OR a holder of the role.manage permission.


class _RbacAdminMixin:
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from common.scope import has_perm
        from organizations.permissions_catalog import ROLE_MANAGE

        org = get_active_org(request)
        if org is None:
            raise PermissionDenied("Switch to an organization first.")
        if not (is_active_admin(request) or has_perm(request, org, ROLE_MANAGE)):
            raise PermissionDenied("You do not have permission to manage roles.")

    def _org(self):
        return get_active_org(self.request)


class RoleViewSet(_RbacAdminMixin, viewsets.ModelViewSet):
    def get_serializer_class(self):
        from organizations.serializers import RoleSerializer

        return RoleSerializer

    def get_queryset(self):
        from organizations.models import Role

        return Role.objects.filter(organization=self._org()).order_by("name")

    def perform_create(self, serializer):
        serializer.save(organization=self._org(), is_system=False)

    def perform_update(self, serializer):
        if serializer.instance.is_system:
            raise PermissionDenied("System roles can't be edited.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_system:
            raise PermissionDenied("System roles can't be deleted.")
        instance.delete()


class RoleBindingViewSet(_RbacAdminMixin, viewsets.ModelViewSet):
    def get_serializer_class(self):
        from organizations.serializers import RoleBindingSerializer

        return RoleBindingSerializer

    def get_queryset(self):
        from organizations.models import RoleBinding

        qs = RoleBinding.objects.filter(organization=self._org()).select_related("user", "role")
        user = self.request.query_params.get("user")
        if user and user.isdigit():
            qs = qs.filter(user_id=user)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(organization=self._org(), granted_by=self.request.user)


class PermissionGrantViewSet(_RbacAdminMixin, viewsets.ModelViewSet):
    def get_serializer_class(self):
        from organizations.serializers import PermissionGrantSerializer

        return PermissionGrantSerializer

    def get_queryset(self):
        from organizations.models import PermissionGrant

        qs = PermissionGrant.objects.filter(organization=self._org()).select_related("user")
        user = self.request.query_params.get("user")
        if user and user.isdigit():
            qs = qs.filter(user_id=user)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(organization=self._org(), granted_by=self.request.user)


class PermissionCatalogView(APIView):
    """GET /api/v1/permissions/ — the permission catalog for the Roles UI matrix."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from organizations.permissions_catalog import CATALOG

        return Response([{"code": c, "label": label, "group": group} for c, label, group in CATALOG])
