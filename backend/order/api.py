import json
import logging
from typing import List

import razorpay
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from product.models import Product

from .models import Order, OrderItem, SavedAddress
from .schemas import (
    OrderCreateSchema,
    OrderInitSchema,
    PaymentVerifySchema,
    SavedAddressSchema,
)

logger = logging.getLogger(__name__)

router = Router()


# Initialize Razorpay Client
def get_razorpay_client():
    """
    Returns an authenticated Razorpay client.
    Using a function ensures we don't crash if settings are missing
    until we actually try to use it.
    """
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# --- ENDPOINTS ---
@router.post("/initiate", response=OrderInitSchema, auth=JWTAuth())  # <--- Added Auth
def initiate_order(request, data: OrderCreateSchema):
    logger.info(
        "Order initiation started for user: %s",
        request.auth.email if request.auth else "anonymous",
    )

    client = get_razorpay_client()

    with transaction.atomic():
        # 1. Create Order
        # Since auth is required, request.auth is GUARANTEED to be the user
        order = Order.objects.create(
            user=request.auth,  # <--- Simplified! No "if/else" needed
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            company_name=data.company_name,
            gstin=data.gstin,
            # Address Mapping...
            billing_address_line1=data.billing_address.address_line1,
            billing_address_line2=data.billing_address.address_line2,
            billing_city=data.billing_address.city,
            billing_state=data.billing_address.state,
            billing_pincode=data.billing_address.pincode,
            shipping_address_line1=data.shipping_address.address_line1,
            shipping_address_line2=data.shipping_address.address_line2,
            shipping_city=data.shipping_address.city,
            shipping_state=data.shipping_address.state,
            shipping_pincode=data.shipping_address.pincode,
            status="PENDING",
        )

        # 2. Process Items (Bulk optimized)
        product_ids = [item.product_id for item in data.items]
        products = Product.objects.in_bulk(product_ids)

        calculated_total = 0
        order_items_to_create = []

        for item_data in data.items:
            product = products.get(item_data.product_id)
            if not product:
                raise HttpError(404, f"Product with ID {item_data.product_id} not found")

            if product.price_type != "fixed" or not product.price:
                raise HttpError(400, f"Product {product.name} is not available for direct purchase")

            line_total = product.price * item_data.quantity
            calculated_total += line_total

            order_items_to_create.append(
                OrderItem(
                    order=order,
                    product=product,
                    quantity=item_data.quantity,
                    price_at_purchase=product.price,
                )
            )

        if not order_items_to_create:
            raise HttpError(400, "Order must contain at least one valid item")

        OrderItem.objects.bulk_create(order_items_to_create)

        order.total_amount = calculated_total
        order.save()

        # 3. Handle "Save Address" (Protected automatically now)
        if data.save_info:
            SavedAddress.objects.create(
                user=request.auth,  # <--- Simple
                type="SHIPPING",
                full_name=f"{data.first_name} {data.last_name}",
                phone=data.phone,
                address_line1=data.shipping_address.address_line1,
                address_line2=data.shipping_address.address_line2,
                city=data.shipping_address.city,
                state=data.shipping_address.state,
                pincode=data.shipping_address.pincode,
            )

        # 4. Razorpay Logic (Same as before)
        amount_in_paise = int(calculated_total * 100)
        razorpay_order = client.order.create(
            {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"order_rcptid_{order.id}",
                "payment_capture": 1,
            }
        )

        order.razorpay_order_id = razorpay_order["id"]
        order.save()

    logger.info(
        "Order %s initiated successfully. Amount: %s, Razorpay Order ID: %s",
        order.id,
        calculated_total,
        order.razorpay_order_id,
    )

    return {
        "order_id": order.id,
        "razorpay_order_id": order.razorpay_order_id,
        "amount": calculated_total,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
    }


@router.get("/my-addresses", response=List[SavedAddressSchema], auth=JWTAuth())
def get_my_addresses(request):
    # This requires the user to be logged in
    if not request.auth:
        return []
    return SavedAddress.objects.filter(user=request.auth)


@router.post("/verify", auth=JWTAuth())
def verify_payment(request, data: PaymentVerifySchema):
    logger.info(
        "Payment verification started for Razorpay order: %s", data.razorpay_order_id
    )

    order = get_object_or_404(Order, razorpay_order_id=data.razorpay_order_id)

    if order.user != request.auth:
        logger.warning(
            "Unauthorized payment verification attempt for order %s by user %s",
            order.id,
            request.auth.email,
        )
        raise HttpError(403, "You are not authorized to verify this order")

    # Idempotency check
    if order.status == "PAID":
        return {"status": "success", "message": "Payment already verified"}

    client = get_razorpay_client()

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": data.razorpay_order_id,
                "razorpay_payment_id": data.razorpay_payment_id,
                "razorpay_signature": data.razorpay_signature,
            }
        )
    except razorpay.errors.SignatureVerificationError:
        with transaction.atomic():
            order.status = "FAILED"
            order.save(update_fields=["status", "updated_at"])
        logger.error("Payment signature verification failed for order %s", order.id)
        raise HttpError(400, "Invalid Payment Signature")

    with transaction.atomic():
        order.status = "PAID"
        order.razorpay_payment_id = data.razorpay_payment_id
        order.razorpay_signature = data.razorpay_signature
        order.save(update_fields=["status", "razorpay_payment_id", "razorpay_signature", "updated_at"])

    logger.info(
        "Payment verified successfully for order %s. Razorpay Payment ID: %s",
        order.id,
        data.razorpay_payment_id,
    )

    return {"status": "success", "message": "Payment verified successfully"}


@router.post("/webhook", auth=None)
def razorpay_webhook(request):
    """
    Razorpay Webhook to ensure payments are captured
    even if the user closes their browser prematurely.
    """
    signature = request.headers.get("X-Razorpay-Signature", "")
    body_data = request.body.decode("utf-8")
    client = get_razorpay_client()

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured.")
        raise HttpError(500, "Webhook secret not configured")

    try:
        client.utility.verify_webhook_signature(
            body_data, signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        logger.error("Invalid Razorpay webhook signature")
        raise HttpError(400, "Invalid webhook signature")

    try:
        payload = json.loads(body_data)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload in webhook")
        raise HttpError(400, "Invalid payload")

    try:
        event = payload.get("event")
        
        # We listen for both order.paid and payment.captured
        if event in ("payment.captured", "order.paid"):
            
            if event == "order.paid":
                razorpay_order_id = payload["payload"]["order"]["entity"]["id"]
                razorpay_payment_id = None # Usually captured via payment.captured
            else:
                razorpay_order_id = payload["payload"]["payment"]["entity"]["order_id"]
                razorpay_payment_id = payload["payload"]["payment"]["entity"]["id"]

            if razorpay_order_id:
                order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
                if order and order.status != "PAID":
                    order.status = "PAID"
                    if razorpay_payment_id:
                        order.razorpay_payment_id = razorpay_payment_id
                    order.save()
                    logger.info("Order %s marked as PAID via webhook event: %s", order.id, event)
                    
    except KeyError as e:
        logger.error("Missing expected key in Razorpay webhook payload: %s", str(e))
        # Return 400 for malformed payloads so it's clear the request itself is bad
        raise HttpError(400, "Malformed payload structure")
    except Exception as e:
        logger.exception("Unexpected error processing Razorpay webhook: %s", str(e))
        # Raise 500 for DB issues or unexpected errors so Razorpay RETRIES the webhook later
        raise HttpError(500, "Internal server error")
        
    return {"status": "success"}
