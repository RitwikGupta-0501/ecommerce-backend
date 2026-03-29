from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Order, OrderItem, SavedAddress


# Register your models here.
class OrderItemInLine(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quatity", "price_at_purchase")


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    inlines = [OrderItemInline]
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("email", "first_name", "last_name", "razorpay_order_id")
    readonly_fields = (
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        "created_at",
        "updated_at",
    )


@admin.register(SavedAddress)
class SavedAddressAdmin(ModelAdmin):
    list_display = ("user", "full_name", "city", "type", "is_default")
