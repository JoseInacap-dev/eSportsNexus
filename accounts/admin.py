from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import OrganizationMembership, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "display_name", "is_staff", "is_active")
    search_fields = ("username", "email", "display_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Perfil", {"fields": ("display_name", "phone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Perfil", {"fields": ("email", "display_name", "phone")}),
    )


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("user__username", "organization__name")
