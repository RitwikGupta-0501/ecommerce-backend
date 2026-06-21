import re

from ninja import Schema
from pydantic import EmailStr, Field, field_validator, model_validator


# --- Input Schema (What the user sends) ---
class UserLoginSchema(Schema):
    email: EmailStr
    password: str

class UserRegisterSchema(Schema):
    email: EmailStr
    first_name: str
    last_name: str
    company_name: str | None = None
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_complexity(cls, v: str):
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v

    @model_validator(mode="after")
    def check_passwords_match(self):
        # Access attributes directly from 'self' in Pydantic V2
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


# 1. The Basic User Info (what you already have)
class UserOutSchema(Schema):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    company_name: str | None = None


# 2. A Schema for the Tokens
class TokenSchema(Schema):
    access: str
    refresh: str


# 3. The Combined Response Schema (The "Wrapper")
class AuthResponseSchema(Schema):
    user: UserOutSchema
    tokens: TokenSchema
