import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import QuoteRequest

logger = logging.getLogger(__name__)


def send_quote_email_task(quote_id):
    try:
        quote = QuoteRequest.objects.get(id=quote_id)

        admin_subject = f"New Quote Request: {quote.product.name}"
        admin_message = f"""
        New Lead!

        Product: {quote.product.name}
        Quantity: {quote.quantity}

        Customer: {quote.email}
        Phone: {quote.phone or "N/A"}
        User ID: {quote.user_id or "Guest"}

        Message:
        {quote.message}
        """

        send_mail(
            admin_subject,
            admin_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )
        logger.info("Quote request notification sent to admin for quote %s", quote_id)

        customer_subject = f"We received your request: {quote.product.name}"
        customer_message = f"""
        Hi there,

        Thanks for requesting a quote for {quote.product.name} (Qty: {quote.quantity}).

        Our team has received your request and will get back to you shortly with pricing and availability.

        Best regards,
        The NexGen Team
        """

        send_mail(
            customer_subject,
            customer_message,
            settings.DEFAULT_FROM_EMAIL,
            [quote.email],
            fail_silently=True,
        )
        logger.info(
            "Quote request confirmation sent to %s for quote %s", quote.email, quote_id
        )

    except QuoteRequest.DoesNotExist:
        logger.warning("Quote request %s not found", quote_id)
    except Exception as e:
        logger.exception(
            "Failed to send quote email for quote %s: %s", quote_id, str(e)
        )
        raise e
