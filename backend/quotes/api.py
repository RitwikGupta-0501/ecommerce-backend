import logging

from django.shortcuts import get_object_or_404
from django_q.tasks import async_task
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from product.models import Product

from .models import QuoteRequest
from .schemas import QuoteInputSchema, QuoteSuccessSchema

logger = logging.getLogger(__name__)

router = Router()


# --- Endpoints ---
@router.post("/request", response=QuoteSuccessSchema, auth=JWTAuth())
def create_quote_request(request, data: QuoteInputSchema):
    product = get_object_or_404(Product, id=data.product_id)

    quote = QuoteRequest.objects.create(
        product=product,
        user=request.auth if request.auth else None,
        email=data.email,
        phone=data.phone,
        quantity=data.quantity,
        message=data.message,
    )

    async_task("quotes.tasks.send_quote_email_task", quote.id)

    logger.info(
        "Quote request %s created for product %s by %s",
        quote.id,
        product.name,
        data.email,
    )

    return {"message": "Quote request received successfully", "quote_id": quote.id}
