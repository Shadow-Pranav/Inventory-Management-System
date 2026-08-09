from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TenantOwnedModel


class UnitOfMeasure(TenantOwnedModel):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    decimal_places = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "symbol"], name="uniq_uom_org_symbol"),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.symbol


class Category(TenantOwnedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name", "parent"], name="uniq_category_org_name_parent"
            ),
        ]
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Item(TenantOwnedModel):
    class ItemType(models.TextChoices):
        CONSUMABLE = "CONSUMABLE", "Consumable"
        ASSET = "ASSET", "Asset"
        SPARE = "SPARE", "Spare"
        SERVICE = "SERVICE", "Service"

    class TrackingMode(models.TextChoices):
        NONE = "NONE", "None"
        BATCH = "BATCH", "Batch"
        SERIAL = "SERIAL", "Serial"

    class ReorderLevelSource(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        COMPUTED = "COMPUTED", "Computed"

    # No `quantity` field, deliberately — stock is derived from StockLevel (D-05, context 04 §2).
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50)
    barcode = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="items")
    item_type = models.CharField(
        max_length=20, choices=ItemType.choices, default=ItemType.CONSUMABLE
    )
    tracking_mode = models.CharField(
        max_length=10, choices=TrackingMode.choices, default=TrackingMode.NONE
    )
    is_perishable = models.BooleanField(default=False)
    shelf_life_days = models.PositiveIntegerField(null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    reorder_level_source = models.CharField(
        max_length=10, choices=ReorderLevelSource.choices, default=ReorderLevelSource.MANUAL
    )
    min_order_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    lead_time_days = models.PositiveIntegerField(default=0)
    hsn_code = models.CharField(max_length=8, blank=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    image = models.ImageField(upload_to="item_images/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "sku"], name="uniq_item_org_sku"),
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_item_org_name"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Supplier(TenantOwnedModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    pan = models.CharField(max_length=10, blank=True)
    payment_terms_days = models.PositiveIntegerField(default=0)
    rating = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_supplier_org_code"),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class ItemSupplier(TenantOwnedModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="supplier_links")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="item_links")
    supplier_sku = models.CharField(max_length=50, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    lead_time_days = models.PositiveIntegerField(default=0)
    is_preferred = models.BooleanField(default=False)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "item", "supplier"],
                name="uniq_itemsupplier_org_item_supplier",
            ),
        ]
        ordering = ["-is_preferred", "unit_price"]

    def __str__(self):
        return f"{self.item} via {self.supplier}"
