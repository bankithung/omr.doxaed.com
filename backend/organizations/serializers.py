from rest_framework import serializers

from common.logo_validators import validate_logo_image

from .models import (
    AuditLog,
    ClassAccessGrant,
    Invitation,
    Organization,
    OrganizationMembership,
    PermissionGrant,
    Role,
    RoleBinding,
)


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization.  The `role` field is annotated dynamically
    from the membership when the queryset is built in the view (see
    OrganizationListView).  It is read-only and not stored on the model.
    """

    role = serializers.CharField(read_only=True, default=None)

    class Meta:
        model = Organization
        fields = ["id", "name", "type", "owner", "role", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "role", "created_at", "updated_at"]


class MembershipSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationMembership — list endpoint."""

    email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user_id", "email", "role", "status", "joined_at"]
        read_only_fields = fields


class InviteSerializer(serializers.Serializer):
    """Input for POST /organizations/{id}/invite/."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=OrganizationMembership.ROLE_CHOICES,
        default=OrganizationMembership.MEMBER,
    )


class AcceptInviteSerializer(serializers.Serializer):
    """Input for POST /invitations/accept/."""

    token = serializers.UUIDField()


class MemberRoleSerializer(serializers.Serializer):
    """Input for PATCH /organizations/{id}/members/{user_id}/."""

    role = serializers.ChoiceField(choices=OrganizationMembership.ROLE_CHOICES)


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_email",
            "action",
            "target_type",
            "target_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class OrgBrandingSerializer(serializers.ModelSerializer):
    """
    GET/PUT /api/v1/organizations/<id>/branding/
    Exposes logo + default_sheet_heading.  Supports multipart upload for logo.
    """

    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[validate_logo_image],
    )
    default_sheet_heading = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    class Meta:
        model = Organization
        fields = ["logo", "default_sheet_heading"]

    def update(self, instance, validated_data):
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save(update_fields=list(validated_data.keys()))
        return instance


class ClassAccessGrantSerializer(serializers.ModelSerializer):
    """Admin-managed grant of a class (and optionally only some subjects) to a
    member. Validates that the class, user and subjects all belong to the ACTIVE
    organization (read from the X-Organization-Id header via common.scope)."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    subject_names = serializers.SerializerMethodField()

    class Meta:
        model = ClassAccessGrant
        fields = [
            "id", "user", "user_email", "class_group",
            "all_subjects", "subjects", "subject_names", "created_at",
        ]
        read_only_fields = ["id", "user_email", "subject_names", "created_at"]

    def get_subject_names(self, obj):
        return list(obj.subjects.values_list("name", flat=True))

    def validate(self, attrs):
        from common.scope import get_active_org  # lazy: avoid app-load cycle

        org = get_active_org(self.context["request"])
        if org is None:
            raise serializers.ValidationError("Switch to an organization to manage access grants.")
        cg = attrs.get("class_group") or getattr(self.instance, "class_group", None)
        if cg is None or cg.organization_id != org.id:
            raise serializers.ValidationError({"class_group": "Class is not in this organization."})
        user = attrs.get("user") or getattr(self.instance, "user", None)
        if user is None or not OrganizationMembership.objects.filter(
            organization=org, user=user, status=OrganizationMembership.ACTIVE
        ).exists():
            raise serializers.ValidationError({"user": "Not an active member of this organization."})
        subs = attrs.get("subjects")
        if subs and any(s.class_group_id != cg.id for s in subs):
            raise serializers.ValidationError({"subjects": "Subjects must belong to this class."})
        return attrs


def _active_org(context):
    from common.scope import get_active_org

    org = get_active_org(context["request"])
    if org is None:
        raise serializers.ValidationError("Switch to an organization first.")
    return org


def _assert_active_member(org, user):
    if user is None or not OrganizationMembership.objects.filter(
        organization=org, user=user, status=OrganizationMembership.ACTIVE
    ).exists():
        raise serializers.ValidationError({"user": "Not an active member of this organization."})


def _assert_scope_in_org(org, scope_group):
    if scope_group is not None and scope_group.organization_id != org.id:
        raise serializers.ValidationError({"scope_group": "Group is not in this organization."})


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "is_system", "permissions", "created_at"]
        read_only_fields = ["id", "is_system", "created_at"]

    def validate_permissions(self, value):
        from organizations.permissions_catalog import VALID_CODES

        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions must be a list of codes.")
        bad = [c for c in value if c not in VALID_CODES]
        if bad:
            raise serializers.ValidationError(f"Unknown permission codes: {bad}")
        return value


class RoleBindingSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = RoleBinding
        fields = ["id", "user", "user_email", "role", "role_name", "scope_group", "created_at"]
        read_only_fields = ["id", "user_email", "role_name", "created_at"]

    def validate(self, attrs):
        org = _active_org(self.context)
        user = attrs.get("user") or getattr(self.instance, "user", None)
        role = attrs.get("role") or getattr(self.instance, "role", None)
        _assert_active_member(org, user)
        if role is None or role.organization_id != org.id:
            raise serializers.ValidationError({"role": "Role is not in this organization."})
        _assert_scope_in_org(org, attrs.get("scope_group"))
        return attrs


class PermissionGrantSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = PermissionGrant
        fields = ["id", "user", "user_email", "permission", "scope_group", "created_at"]
        read_only_fields = ["id", "user_email", "created_at"]

    def validate_permission(self, value):
        from organizations.permissions_catalog import VALID_CODES

        if value not in VALID_CODES:
            raise serializers.ValidationError("Unknown permission code.")
        return value

    def validate(self, attrs):
        org = _active_org(self.context)
        _assert_active_member(org, attrs.get("user") or getattr(self.instance, "user", None))
        _assert_scope_in_org(org, attrs.get("scope_group"))
        return attrs
