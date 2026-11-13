from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AdminUserCreationForm
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    list_display = ["username", "email", "role", "is_staff"]
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email")
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("FixIT Profile", {"fields": ("email", "role", "phone")}),
    )
    fieldsets = UserAdmin.fieldsets + (
        ("FixIT Profile", {"fields": ("role", "phone")}),
    )