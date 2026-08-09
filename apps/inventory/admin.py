from django.contrib import admin

from .models import Batch, Location, SerialUnit, StockLevel, StockMovement


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "location_type", "is_active")
    list_filter = ("organization", "location_type", "is_active")
    search_fields = ("name", "code")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("item", "batch_number", "expiry_date", "supplier")
    list_filter = ("organization",)
    search_fields = ("batch_number", "item__name", "item__sku")


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ("item", "location", "batch", "quantity", "reserved_quantity")
    list_filter = ("organization", "location")
    search_fields = ("item__name", "item__sku")


@admin.register(SerialUnit)
class SerialUnitAdmin(admin.ModelAdmin):
    list_display = ("serial_number", "item", "status", "current_location", "current_holder")
    list_filter = ("organization", "status")
    search_fields = ("serial_number", "item__sku")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "movement_type", "item", "location", "quantity", "balance_after")
    list_filter = ("organization", "movement_type")
    search_fields = ("item__name", "item__sku")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
