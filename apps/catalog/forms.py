from apps.core.forms import TenantModelForm

from .models import Category, Item


class CategoryForm(TenantModelForm):
    tenant_fields = ["parent"]

    class Meta:
        model = Category
        fields = ["name", "code", "parent"]


class ItemForm(TenantModelForm):
    tenant_fields = ["category", "uom"]

    class Meta:
        model = Item
        fields = [
            "name",
            "sku",
            "barcode",
            "description",
            "category",
            "uom",
            "item_type",
            "tracking_mode",
            "is_perishable",
            "shelf_life_days",
            "reorder_level",
            "min_order_qty",
            "lead_time_days",
            "hsn_code",
            "gst_rate",
            "is_active",
        ]
