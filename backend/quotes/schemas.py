from ninja import Schema
from pydantic import Field, EmailStr

# --- Schemas ---
class QuoteInputSchema(Schema):
    product_id: int
    email: EmailStr
    phone: str = ""
    quantity: int = Field(1, gt=0, le=10000)
    message: str = Field("", max_length=2000)


class QuoteSuccessSchema(Schema):
    message: str
    quote_id: int


#
