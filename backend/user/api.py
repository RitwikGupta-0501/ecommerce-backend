import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django_q.tasks import async_task
from ninja import Router
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import AccessToken, RefreshToken

from django.contrib.auth import authenticate
from django.http import HttpResponse
from .schemas import AuthResponseSchema, UserOutSchema, UserRegisterSchema, UserLoginSchema
import json

logger = logging.getLogger(__name__)

router = Router()

User = get_user_model()


class AuthThrottle(AnonRateThrottle):
    scope = "auth"


def set_auth_cookies(response: HttpResponse, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="Lax", max_age=300)
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="Lax", max_age=604800, path="/api/token/refresh")
    return response


@router.post("/login", auth=None, response={200: AuthResponseSchema}, throttle=AuthThrottle())
def login(request, data: UserLoginSchema):
    user = authenticate(username=data.email, password=data.password)
    if not user:
        raise HttpError(401, "Invalid email or password")
    
    refresh = RefreshToken.for_user(user)
    access = AccessToken.for_user(user)
    
    response_data = {
        "user": user,
        "tokens": {
            "access": str(access),
            "refresh": str(refresh),
        },
    }
    
    # We serialize the schema manually into JSON and return an HttpResponse
    response_schema = AuthResponseSchema.model_validate(response_data)
    response = HttpResponse(response_schema.model_dump_json(), content_type="application/json", status=200)
    return set_auth_cookies(response, str(access), str(refresh))


@router.post("/register", response={201: AuthResponseSchema}, auth=None, throttle=AuthThrottle())
def register_user(request, data: UserRegisterSchema):
    try:
        # 1. Create User
        user = User.objects.create_user(
            username=data.email,
            email=data.email,
            password=data.password,
            company_name=data.company_name,
            first_name=data.first_name,
            last_name=data.last_name,
        )

        # 2. Background Task (Email)
        async_task("user.tasks.send_welcome_email", user.id)

        # 3. Generate Tokens
        refresh = RefreshToken.for_user(user)
        access = AccessToken.for_user(user)

        response_data = {
            "user": user,
            "tokens": {
                "access": str(access),
                "refresh": str(refresh),
            },
        }
        
        response_schema = AuthResponseSchema.model_validate(response_data)
        response = HttpResponse(response_schema.model_dump_json(), content_type="application/json", status=201)
        return set_auth_cookies(response, str(access), str(refresh))

    except IntegrityError:
        raise HttpError(409, "A user with this email already exists.")
    except Exception as e:
        logger.exception("Registration failed: %s", str(e))
        raise HttpError(500, "Internal Server Error during registration.")


@router.get("/me", auth=JWTAuth(), response=UserOutSchema)
def get_me(request):
    """
    Used by the frontend to get 'Who am I?'
    after login or page reload.
    """
    return request.auth
