from django.db.models import Q
from rest_framework import serializers

from common.scope import is_active_admin, parent_in_scope
from folders.models import Folder, FolderShare


class FolderSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        required=False,
        allow_null=True,
    )
    permission = serializers.SerializerMethodField()
    share_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = (
            "id",
            "name",
            "parent",
            "created_by",
            "created_at",
            "permission",
            "share_count",
        )
        read_only_fields = ("id", "created_by", "created_at", "permission", "share_count")

    def validate_parent(self, value):
        if value is None:
            return value
        request = self.context["request"]
        # Parent folder must belong to the requester's active scope.
        if not parent_in_scope(value, request):
            raise serializers.ValidationError("Parent folder not found in your account.")
        return value

    def get_permission(self, obj):
        """Computed edit/view permission for the requesting user."""
        request = self.context.get("request")
        if request is None:
            return FolderShare.PERM_VIEW
        user = request.user
        # Folder creator and active-org admins have edit.
        if obj.created_by_id == getattr(user, "id", None):
            return FolderShare.PERM_EDIT
        if is_active_admin(request):
            return FolderShare.PERM_EDIT
        # Highest permission across applicable shares (member-share OR org-share).
        has_edit = obj.shares.filter(
            Q(shared_with=user) | Q(share_scope=FolderShare.SHARE_ORG),
            permission=FolderShare.PERM_EDIT,
        ).exists()
        return FolderShare.PERM_EDIT if has_edit else FolderShare.PERM_VIEW

    def get_share_count(self, obj):
        return obj.shares.count()


class FolderShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = FolderShare
        fields = (
            "id",
            "folder",
            "shared_with",
            "share_scope",
            "permission",
            "created_by",
            "created_at",
        )
        read_only_fields = ("id", "folder", "created_by", "created_at")
