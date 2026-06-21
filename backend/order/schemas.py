from typing import List, Optional

from ninja import Schema
from pydantic import Field, EmailStr, field_validator
import re


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
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[\d\s\-()]{7,15}$")
    company_name: Optional[str] = Field(None, max_length=255)
    gstin: Optional[str] = Field(None, max_length=15)
    billing_address: AddressSchema
    shipping_address: AddressSchema
    items: List[OrderItemSchema] = Field(..., min_length=1, max_length=50)
    save_info: bool = False

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v):
        if v and not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", v):
            raise ValueError("Invalid GSTIN format")
        return v


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
