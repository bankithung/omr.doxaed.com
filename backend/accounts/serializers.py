from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """Registration serializer that does NOT expose unique-email errors.

    We validate the password (for new signups) but intentionally avoid raising
    on duplicate email — the view handles that case silently to prevent
    user-enumeration.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=False, default="")

    def validate_password(self, value):
        # Only validate password if the email is not already taken.
        # We can't know that here without a DB query, so we always validate
        # (it's cheap and the error is only shown to real new users).
        validate_password(value)
        return value


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "is_email_verified")
        read_only_fields = ("id", "email", "is_email_verified")
