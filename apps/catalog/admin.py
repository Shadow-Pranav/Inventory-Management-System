from django.contrib import admin

from .models import Category, Item, ItemSupplier, Supplier, UnitOfMeasure


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ("symbol", "name", "organization", "decimal_places")
    list_filter = ("organization",)
    search_fields = ("name", "symbol")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "parent")
    list_filter = ("organization",)
    search_fields = ("name", "code")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "organization", "category", "item_type", "is_active")
    list_filter = ("organization", "item_type", "tracking_mode", "is_active")
    search_fields = ("name", "sku", "barcode")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "rating", "is_blacklisted")
    list_filter = ("organization", "is_blacklisted")
    search_fields = ("name", "code", "gstin")


@admin.register(ItemSupplier)
class ItemSupplierAdmin(admin.ModelAdmin):
    list_display = ("item", "supplier", "unit_price", "is_preferred")
    list_filter = ("organization", "is_preferred")
