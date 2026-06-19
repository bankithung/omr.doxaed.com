from rest_framework import serializers

from common.logo_validators import validate_logo_image

from .models import AuditLog, ClassAccessGrant, Invitation, Organization, OrganizationMembership


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization.  The `role` field is annotated dynamically
    from the membership when the queryset is built in the view (see
    OrganizationListView).  It is read-only and not stored on the model.
    """

    role = serializers.CharField(read_only=True, default=None)

    class Meta:
        model = Organization
        fields = ["id", "name", "owner", "role", "created_at", "updated_at"]
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
