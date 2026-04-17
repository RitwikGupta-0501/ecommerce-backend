from ninja import Schema
from pydantic import Field

# --- Schemas ---
class QuoteInputSchema(Schema):
    product_id: int
    email: str
    phone: str = ""
    quantity: int = Field(1, gt=0)
    message: str = ""


class QuoteSuccessSchema(Schema):
    message: str
    quote_id: int


#
