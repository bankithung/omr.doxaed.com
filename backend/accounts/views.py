from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from .emails import (
    send_account_exists_email,
    send_password_reset_email,
    send_verification_email,
)
from .serializers import MeSerializer, RegisterSerializer
from .tokens import read_uid_token

User = get_user_model()

_REGISTER_SUCCESS = {"detail": "Check your email to verify your account."}


class RegisterView(APIView):
    """Registration endpoint with no-enumeration: always returns 201."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        # Check whether email already exists *before* full validation so we
        # can skip the password-validation step for duplicates (avoids leaking
        # information via error messages).
        email = (request.data.get("email") or "").strip().lower()
        existing_user = User.objects.filter(email__iexact=email).first() if email else None

        if existing_user:
            # Silent duplicate: notify the existing user and return identical
            # success response — caller cannot distinguish new vs existing.
            send_account_exists_email(existing_user)
            return Response(_REGISTER_SUCCESS, status=status.HTTP_201_CREATED)

        # New email: validate fully (password included).
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            full_name=serializer.validated_data.get("full_name", ""),
        )
        send_verification_email(user)
        return Response(_REGISTER_SUCCESS, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify_email"

    def post(self, request):
        user = read_uid_token(request.data.get("uid"), request.data.get("token"))
        if user is None:
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email verified."})


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = MeSerializer(self.user).data
        return data


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    """Blacklist the provided refresh token, invalidating the session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except (KeyError, TokenError):
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        email = request.data.get("email", "")
        user = User.objects.filter(email__iexact=email).first()
        if user:
            send_password_reset_email(user)
        return Response({"detail": "If that email exists, a reset link was sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        user = read_uid_token(request.data.get("uid"), request.data.get("token"))
        new_password = request.data.get("new_password", "")
        if user is None:
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new_password, user)
        except DjangoValidationError as e:
            return Response({"new_password": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class GoogleLoginView(APIView):
    """Sign in (or sign up) with a Google ID token.

    Body: ``{"id_token": "<GIS credential JWT>"}``.

    Env-gated: when ``GOOGLE_CLIENT_ID`` is empty the feature is considered
    unconfigured and we return 503 — the frontend hides its button in that case,
    so this is a defensive backstop, never a user-facing path in normal use.

    On success the SAME ``{access, refresh, user}`` payload as the email login
    view is returned, so the frontend can reuse its token-storage logic.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        client_id = settings.GOOGLE_CLIENT_ID
        if not client_id:
            return Response(
                {"detail": "Google sign-in is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        token = request.data.get("id_token", "")
        if not token:
            return Response(
                {"detail": "Missing id_token."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the ID token's signature, audience (our client_id), issuer and
        # expiry against Google's public keys. Any failure → 400 (never 500).
        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), client_id
            )
        except Exception:
            return Response(
                {"detail": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = (idinfo.get("email") or "").strip().lower()
        if not email or not idinfo.get("email_verified"):
            return Response(
                {"detail": "Google account email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        full_name = (idinfo.get("name") or "").strip()

        # Link by case-insensitive email. New users get an unusable password
        # (they can only sign in via Google or reset to set one) and are marked
        # email-verified because Google already verified the address.
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(email=email, full_name=full_name, is_email_verified=True)
            user.set_unusable_password()
            user.save()
        elif not user.is_email_verified:
            # Existing local user signing in via Google for the first time:
            # Google has now verified the address, so trust it.
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": MeSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
