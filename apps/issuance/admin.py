from django.contrib import admin

from .models import IssueItem, IssueRequest


class IssueItemInline(admin.TabularInline):
    model = IssueItem
    extra = 0


@admin.register(IssueRequest)
class IssueRequestAdmin(admin.ModelAdmin):
    list_display = ("issue_number", "organization", "department", "status", "requested_by")
    list_filter = ("organization", "status")
    search_fields = ("issue_number",)
    inlines = [IssueItemInline]
