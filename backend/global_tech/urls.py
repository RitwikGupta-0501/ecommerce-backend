"""
URL configuration for global_tech project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from ninja_extra import NinjaExtraAPI
from ninja.errors import HttpError
from django.db import connection
from ninja_jwt.controller import NinjaJWTDefaultController
from order.api import router as order_router
from product.api import router as product_router
from quotes.api import router as quotes_router
from user.api import router as user_auth_router

api = NinjaExtraAPI(
    title="Global Tech API", description="API for Next.js Frontend", version="1.0.0"
)

api.register_controllers(NinjaJWTDefaultController)

api.add_router("/products", product_router)
api.add_router("/auth", user_auth_router)
api.add_router("/quotes", quotes_router)
api.add_router("/order", order_router)

@api.get("/health", tags=["System"], auth=None)
def health_check(request):
    try:
        connection.ensure_connection()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HttpError(503, f"Database unavailable: {str(e)}")

urlpatterns = [
    path("admin/", admin.site.urls),  # URL for Admin page (handled by base django)
    path("api/", api.urls),  # URL for the api (handled by django ninja)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
