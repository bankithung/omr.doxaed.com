from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password", "full_name", "is_email_verified")
        read_only_fields = ("id", "is_email_verified")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "is_email_verified")
        read_only_fields = ("id", "email", "is_email_verified")
