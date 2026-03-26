from django.contrib import admin
from django.db import models
from django_json_widget.widgets import JSONEditorWidget
from unfold.admin import ModelAdmin, TabularInline  # Import from Unfold

from .models import Product, ProductImage


# Use Unfold's TabularInline for a better looking upload section
class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    tab = True  # Unfold specific: puts inlines in a nice tab!


@admin.register(Product)
class ProductAdmin(ModelAdmin):  # Inherit from ModelAdmin
    inlines = [ProductImageInline]
    list_display = ("name", "price", "category", "type", "price_type", "rating")
    search_fields = ("name", "category", "type")

    # Your JSON widget still works perfectly here!
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)

        # Template for Features (List)
        initial["features"] = [
            "Feature 1 (Edit me)",
            "Feature 2 (Edit me)",
            "Feature 3 (Edit me)",
        ]

        # Template for Specifications (Dictionary)
        initial["specifications"] = {
            "License Type": "Perpetual",
            "Version": "1.0",
            "Compatibility": "Windows/Mac",
            "Language": "English",
        }

        return initial
