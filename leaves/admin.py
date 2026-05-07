"""Inregistrari Django admin."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, LeaveRequest, Signature


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "department", "is_staff")
    list_filter = ("role", "department", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Date LeaveFlow", {"fields": ("role", "department", "phone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Date LeaveFlow", {"fields": ("role", "department", "phone")}),
    )


class SignatureInline(admin.StackedInline):
    model = Signature
    extra = 0
    readonly_fields = ("signed_at",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "leave_type", "start_date", "end_date",
        "days", "status", "created_at",
    )
    list_filter = ("status", "leave_type", "created_at")
    search_fields = ("employee__username", "employee__first_name", "employee__last_name", "reason")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at", "decided_at", "days")
    inlines = [SignatureInline]


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("id", "leave_request", "manager", "signed_at")
    readonly_fields = ("signed_at",)
