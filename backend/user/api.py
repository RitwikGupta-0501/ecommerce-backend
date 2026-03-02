import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django_q.tasks import async_task
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import AccessToken, RefreshToken

from .schemas import AuthResponseSchema, UserOutSchema, UserRegisterSchema

logger = logging.getLogger(__name__)

router = Router()

User = get_user_model()


@router.post("/register", response={201: AuthResponseSchema}, auth=None)
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

        # 4. Return
        return 201, {
            "user": user,
            "tokens": {
                "access": str(access),  # Cast to string
                "refresh": str(refresh),  # Cast to string
            },
        }

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
