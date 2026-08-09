from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Department, Membership, Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("short_name", "name", "org_type", "is_active")
    list_filter = ("org_type", "is_active")
    search_fields = ("name", "short_name", "slug")
    prepopulated_fields = {"slug": ("short_name",)}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "parent")
    list_filter = ("organization",)
    search_fields = ("name", "code")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("SITS", {"fields": ("phone", "employee_code", "is_trust_admin", "default_organization")}),
    )
    list_display = ("username", "email", "is_trust_admin", "is_staff", "is_active")
    list_filter = DjangoUserAdmin.list_filter + ("is_trust_admin",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "department", "is_active")
    list_filter = ("organization", "role", "is_active")
    search_fields = ("user__username", "user__email")
