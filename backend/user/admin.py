from django.contrib import admin
from unfold.admin import ModelAdmin
from . import models


# Register your models here.
@admin.register(models.User)
class UserAdmin(ModelAdmin):
    list_display = ("email", "first_name", "last_name", "company_name", "is_staff")
    search_fields = ("email", "first_name", "last_name")

