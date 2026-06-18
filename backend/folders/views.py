"""
folders.views — Folder + FolderShare + Subject endpoints (Product v2 Phase 5B).

Security model
--------------
* Folders are OwnerScopedModel rows (solo user XOR organization). Scope is
  resolved header-only via common.scope (X-Organization-Id).
* Folder visibility (org scope): a folder is visible if the requester created it,
  it is member-shared to them, it has an org-wide share, OR they are an active-org
  admin. Solo scope: only the owner's own folders.
* Writes (create/update/delete a folder, create/delete a share, create/delete a
  subject) require EDIT rights: folder/class creator OR active-org admin (admins
  have full edit per the owner decision). VIEW-only members get 403.
"""
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.models import ClassGroup, Subject
from assessments.serializers import SubjectSerializer
from common.scope import (
    can_edit_class,
    get_active_org,
    is_active_admin,
    parent_in_scope,
    scope_filter,
    scope_kwargs,
)
from common.viewsets import ScopedModelViewSet
from folders.models import Folder, FolderShare
from folders.serializers import FolderSerializer, FolderShareSerializer

_EDIT_DENIED = "You have view-only access to this folder; editing is not permitted."


def _folder_visibility_q(request):
    """Org-scope folder-visibility predicate for the Folder model itself.
    SOLO and ADMIN → Q() (scope_filter alone bounds them)."""
    org = get_active_org(request)
    if org is None:
        return Q()
    if is_active_admin(request):
        return Q()
    user = request.user
    return (
        Q(created_by=user)
        | Q(shares__shared_with=user)
        | Q(shares__share_scope=FolderShare.SHARE_ORG)
    )


def _can_edit_folder(request, folder):
    """EDIT rights on a folder: solo owner / active-org admin / folder creator /
    an EDIT FolderShare (member or org-wide)."""
    org = get_active_org(request)
    if org is None:
        return True  # solo: scope_filter already proved ownership
    if is_active_admin(request):
        return True
    user = request.user
    if folder.created_by_id == user.id:
        return True
    return FolderShare.objects.filter(
        Q(shared_with=user) | Q(share_scope=FolderShare.SHARE_ORG),
        folder=folder,
        permission=FolderShare.PERM_EDIT,
    ).exists()


class FolderViewSet(ScopedModelViewSet):
    """
    GET/POST   /api/v1/folders/
    GET/PATCH/DELETE /api/v1/folders/<id>/
    """

    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    owner_extra_fields = ("created_by",)

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(_folder_visibility_q(self.request))
            .distinct()
            .order_by("name", "id")
        )

    def perform_update(self, serializer):
        if not _can_edit_folder(self.request, serializer.instance):
            raise PermissionDenied(_EDIT_DENIED)
        serializer.save()

    def perform_destroy(self, instance):
        if not _can_edit_folder(self.request, instance):
            raise PermissionDenied(_EDIT_DENIED)
        instance.delete()


class FolderShareViewSet(viewsets.ModelViewSet):
    """
    GET/POST   /api/v1/folders/<folder_pk>/shares/
    DELETE     /api/v1/folders/<folder_pk>/shares/<pk>/

    Writes validate:
      (a) the parent folder belongs to the active scope (parent_in_scope);
      (b) for SHARE_MEMBER, shared_with has an ACTIVE membership in the folder's
          organization (cross-org grantees rejected with 400);
      (c) only the folder creator or an active-org admin may create/delete shares.
    Admin cross-member share actions are logged to AuditLog when available.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FolderShareSerializer

    def _get_folder(self):
        """Resolve the parent folder, scoped to the active scope. 404 otherwise."""
        folder_pk = self.kwargs["folder_pk"]
        try:
            folder = Folder.objects.filter(scope_filter(self.request)).get(pk=folder_pk)
        except Folder.DoesNotExist:
            from django.http import Http404

            raise Http404
        return folder

    def get_queryset(self):
        folder = self._get_folder()
        # Only someone who can see the folder may list its shares.
        if not (
            _folder_is_visible(self.request, folder)
        ):
            from django.http import Http404

            raise Http404
        return FolderShare.objects.filter(folder=folder)

    def _require_share_admin(self, request, folder):
        """Only the folder creator or an active-org admin may mutate shares."""
        if is_active_admin(request):
            return
        if folder.created_by_id == request.user.id:
            return
        raise PermissionDenied(
            "Only the folder owner or an organisation admin may manage shares."
        )

    def create(self, request, *args, **kwargs):
        folder = self._get_folder()
        # (a) parent_in_scope — folder belongs to active scope (already scoped by
        # _get_folder, but assert explicitly for defence-in-depth).
        if not parent_in_scope(folder, request):
            return Response({"folder": "Folder not found in your account."}, status=400)
        # (c) only creator / active-org admin may create shares.
        self._require_share_admin(request, folder)

        org = get_active_org(request)
        if org is None:
            return Response(
                {"detail": "Folder sharing is only available in an organisation."},
                status=400,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        share_scope = serializer.validated_data.get("share_scope", FolderShare.SHARE_MEMBER)
        shared_with = serializer.validated_data.get("shared_with")

        if share_scope == FolderShare.SHARE_MEMBER:
            if shared_with is None:
                return Response(
                    {"shared_with": "Required for a member share."}, status=400
                )
            # (b) grantee must be an ACTIVE member of the folder's organization.
            from organizations.models import OrganizationMembership

            is_member = OrganizationMembership.objects.filter(
                organization_id=folder.organization_id,
                user=shared_with,
                status=OrganizationMembership.ACTIVE,
            ).exists()
            if not is_member:
                return Response(
                    {"shared_with": "User is not an active member of this organisation."},
                    status=400,
                )
        else:  # SHARE_ORG
            shared_with = None

        share = FolderShare.objects.create(
            folder=folder,
            shared_with=shared_with,
            share_scope=share_scope,
            permission=serializer.validated_data.get("permission", FolderShare.PERM_VIEW),
            created_by=request.user,
        )

        # Audit admin-driven cross-member access grants.
        self._audit(request, folder, share, action="folder_share_created")

        out = self.get_serializer(share)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        folder = self._get_folder()
        self._require_share_admin(request, folder)
        try:
            share = FolderShare.objects.get(folder=folder, pk=kwargs["pk"])
        except FolderShare.DoesNotExist:
            from django.http import Http404

            raise Http404
        self._audit(request, folder, share, action="folder_share_deleted")
        share.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _audit(request, folder, share, action):
        """Log admin cross-member share actions to AuditLog if the model exists."""
        if not is_active_admin(request):
            return
        try:
            from organizations.models import AuditLog
        except Exception:
            return
        org = get_active_org(request)
        if org is None:
            return
        try:
            AuditLog.objects.create(
                organization=org,
                actor=request.user,
                action=action,
                target_type="FolderShare",
                target_id=share.id,
                metadata={
                    "folder_id": folder.id,
                    "share_scope": share.share_scope,
                    "permission": share.permission,
                    "shared_with": share.shared_with_id,
                },
            )
        except Exception:
            # Auditing must never break the request path.
            pass


def _folder_is_visible(request, folder):
    """True if the requester may see the folder (creator / shared / org-share /
    active-org admin / solo owner)."""
    org = get_active_org(request)
    if org is None:
        return folder.user_id == request.user.id
    if is_active_admin(request):
        return True
    user = request.user
    if folder.created_by_id == user.id:
        return True
    return FolderShare.objects.filter(
        Q(shared_with=user) | Q(share_scope=FolderShare.SHARE_ORG),
        folder=folder,
    ).exists()


class SubjectViewSet(viewsets.ModelViewSet):
    """
    GET/POST   /api/v1/subjects/?class_group=<id>
    DELETE     /api/v1/subjects/<id>/

    Scoped through class_group__ + folder visibility (class_prefix="class_group__").
    Create validates parent_in_scope(class_group) AND EDIT rights on the class.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SubjectSerializer

    def get_queryset(self):
        from common.scope import visibility_q

        qs = Subject.objects.filter(
            scope_filter(self.request, "class_group__")
            & visibility_q(self.request, "class_group__", "class_group__created_by")
        ).distinct()
        class_group = self.request.query_params.get("class_group")
        if class_group:
            qs = qs.filter(class_group_id=class_group)
        return qs

    def perform_create(self, serializer):
        cg = serializer.validated_data["class_group"]
        if not can_edit_class(self.request, cg):
            raise PermissionDenied(_EDIT_DENIED)
        serializer.save()

    def perform_update(self, serializer):
        if not can_edit_class(self.request, serializer.instance.class_group):
            raise PermissionDenied(_EDIT_DENIED)
        serializer.save()

    def perform_destroy(self, instance):
        if not can_edit_class(self.request, instance.class_group):
            raise PermissionDenied(_EDIT_DENIED)
        instance.delete()
