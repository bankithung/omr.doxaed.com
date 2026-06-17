from django.conf import settings
from django.core.mail import send_mail


def send_invitation_email(invitation):
    """Send an invitation email with the accept link.

    Uses the console backend in development (configured in settings).
    The link points to {FRONTEND_URL}/accept-invite?token=<uuid>.
    """
    link = f"{settings.FRONTEND_URL}/accept-invite?token={invitation.token}"
    subject = f"You're invited to join {invitation.organization.name} on OMRFlow"
    body = (
        f"You have been invited to join {invitation.organization.name} as a "
        f"{invitation.role}.\n\n"
        f"Accept the invitation by clicking the link below:\n{link}\n\n"
        f"This invitation expires in 7 days.\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.email],
    )
