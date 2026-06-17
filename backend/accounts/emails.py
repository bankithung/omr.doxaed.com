from django.conf import settings
from django.core.mail import send_mail

from .tokens import make_uid_token


def _send(user, subject, path):
    uid, token = make_uid_token(user)
    link = f"{settings.FRONTEND_URL}{path}?uid={uid}&token={token}"
    send_mail(subject, f"Open this link:\n{link}\n", settings.DEFAULT_FROM_EMAIL, [user.email])
    return uid, token


def send_verification_email(user):
    return _send(user, "Verify your OMRFlow email", "/verify-email")


def send_password_reset_email(user):
    return _send(user, "Reset your OMRFlow password", "/reset-password")
