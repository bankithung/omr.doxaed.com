from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .emails import send_verification_email
from .serializers import MeSerializer, RegisterSerializer
from .tokens import read_uid_token

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email(user)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except (KeyError, TokenError):
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
