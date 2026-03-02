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

        # 2. Process Items (Same as before)
        calculated_total = 0
        for item_data in data.items:
            product = get_object_or_404(Product, id=item_data.product_id)
            if product.price_type != "fixed" or not product.price:
                continue

            line_total = product.price * item_data.quantity
            calculated_total += line_total

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data.quantity,
                price_at_purchase=product.price,
            )

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
        order.status = "FAILED"
        order.save()
        logger.error("Payment signature verification failed for order %s", order.id)
        raise HttpError(400, "Invalid Payment Signature")

    with transaction.atomic():
        order.status = "PAID"
        order.razorpay_payment_id = data.razorpay_payment_id
        order.razorpay_signature = data.razorpay_signature
        order.save()

    logger.info(
        "Payment verified successfully for order %s. Razorpay Payment ID: %s",
        order.id,
        data.razorpay_payment_id,
    )

    return {"status": "success", "message": "Payment verified successfully"}
