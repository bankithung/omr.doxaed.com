from rest_framework import serializers

from .models import AuditLog, Invitation, Organization, OrganizationMembership


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
