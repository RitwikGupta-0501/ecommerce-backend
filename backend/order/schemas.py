from typing import List, Optional

from ninja import Schema
from pydantic import Field


# --- SCHEMAS ---
class AddressSchema(Schema):
    address_line1: str
    address_line2: str = ""
    city: str
    state: str
    pincode: str


class OrderItemSchema(Schema):
    product_id: int
    quantity: int = Field(..., gt=0)


class OrderCreateSchema(Schema):
    # Personal
    first_name: str
    last_name: str
    email: str
    phone: str
    # Business
    company_name: Optional[str]
    gstin: Optional[str]
    # Addresses
    billing_address: AddressSchema
    shipping_address: AddressSchema
    # Cart
    items: List[OrderItemSchema]
    save_info: bool = False


class OrderInitSchema(Schema):
    order_id: int
    razorpay_order_id: str
    amount: float
    currency: str
    key_id: str  # Sending public key to frontend for convenience


class SavedAddressSchema(Schema):
    id: int
    type: str
    full_name: str
    address_line1: str
    address_line2: str
    city: str
    state: str
    pincode: str
    is_default: bool


class PaymentVerifySchema(Schema):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
