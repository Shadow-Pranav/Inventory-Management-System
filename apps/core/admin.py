from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "organization",
        "action",
        "content_type",
        "object_id",
        "created_by",
        "actor_scope",
    )
    list_filter = ("action", "actor_scope", "organization", "content_type")
    search_fields = ("object_repr",)
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
