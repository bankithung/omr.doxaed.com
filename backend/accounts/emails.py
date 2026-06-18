from django.conf import settings
from django.core.mail import send_mail

from .tokens import make_uid_token


def _send(user, subject, path):
    uid, token = make_uid_token(user)
    link = f"{settings.FRONTEND_URL}{path}?uid={uid}&token={token}"
    send_mail(subject, f"Open this link:\n{link}\n", settings.DEFAULT_FROM_EMAIL, [user.email])
    return uid, token


def send_verification_email(user):
    return _send(user, "Verify your DoxaEd OMR email", "/verify-email")


def send_password_reset_email(user):
    return _send(user, "Reset your DoxaEd OMR password", "/reset-password")


def send_account_exists_email(user):
    """Notify an existing user that someone tried to register with their email."""
    login_link = f"{settings.FRONTEND_URL}/login"
    send_mail(
        "You already have a DoxaEd OMR account",
        (
            f"Hi {user.full_name or user.email},\n\n"
            "Someone just tried to sign up at DoxaEd OMR using your email address.\n"
            "If that was you, you already have an account — log in here:\n"
            f"{login_link}\n\n"
            "If this wasn't you, no action is needed.\n"
        ),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
