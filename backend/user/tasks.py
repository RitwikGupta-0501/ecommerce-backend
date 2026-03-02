import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_welcome_email(user_id):
    """
    Fetches the user and sends a welcome email.
    Running this in a background task prevents the API from hanging.
    """
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)

        send_mail(
            subject="Welcome to Global Tech!",
            message=f"Hi {user.first_name},\n\nThanks for creating an account with us.",
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@globaltech.com",
            recipient_list=[user.email],
            fail_silently=True,
        )
        logger.info("Welcome email sent to %s", user.email)
        return f"Welcome email sent to {user.email}"

    except User.DoesNotExist:
        logger.warning("User %s not found, welcome email skipped.", user_id)
        return f"User {user_id} not found, email skipped."
    except Exception as e:
        logger.exception("Failed to send welcome email to user %s: %s", user_id, str(e))
        raise e
