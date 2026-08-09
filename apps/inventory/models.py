from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.models import Item, Supplier
from apps.core.models import TenantOwnedModel
from apps.tenancy.models import Department


class Location(TenantOwnedModel):
    class LocationType(models.TextChoices):
        MAIN_STORE = "MAIN_STORE", "Main Store"
        SUB_STORE = "SUB_STORE", "Sub Store"
        DEPT_STORE = "DEPT_STORE", "Department Store"
        LAB = "LAB", "Lab"
        WARD = "WARD", "Ward"
        KITCHEN = "KITCHEN", "Kitchen"

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30)
    location_type = models.CharField(max_length=20, choices=LocationType.choices)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="locations"
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_location_org_code"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.short_name})"


class Batch(TenantOwnedModel):
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="batches")
    batch_number = models.CharField(max_length=64)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name="batches"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "item", "batch_number"], name="uniq_batch_org_item_number"
            ),
        ]
        ordering = ["expiry_date"]

    def __str__(self):
        return f"{self.item.sku}/{self.batch_number}"


class StockLevel(TenantOwnedModel):
    """The current-quantity table. Mutated only inside apply_movement() with
    select_for_update() — never `.update(quantity=...)`, never `instance.quantity -= n`.
    """

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="stock_levels")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="stock_levels")
    batch = models.ForeignKey(
        Batch, null=True, blank=True, on_delete=models.PROTECT, related_name="stock_levels"
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    reserved_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        constraints = [
            # Postgres treats NULL as distinct in a unique index, so `batch` being nullable
            # means the constraint below alone would let multiple rows exist for the same
            # (org, item, location) whenever batch is NULL (untracked items). The second,
            # partial constraint closes that gap explicitly.
            models.UniqueConstraint(
                fields=["organization", "item", "location", "batch"],
                name="uniq_stocklevel_org_item_location_batch",
            ),
            models.UniqueConstraint(
                fields=["organization", "item", "location"],
                condition=models.Q(batch__isnull=True),
                name="uniq_stocklevel_org_item_location_no_batch",
            ),
        ]

    @property
    def available(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.item.sku} @ {self.location.code}: {self.quantity}"


class SerialUnit(TenantOwnedModel):
    class Status(models.TextChoices):
        IN_STOCK = "IN_STOCK", "In stock"
        ISSUED = "ISSUED", "Issued"
        IN_REPAIR = "IN_REPAIR", "In repair"
        RETIRED = "RETIRED", "Retired"
        LOST = "LOST", "Lost"

    # `asset` (O2O to assets.Asset) is deferred until apps.assets exists — Phase 7.
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="serial_units")
    serial_number = models.CharField(max_length=100)
    batch = models.ForeignKey(
        Batch, null=True, blank=True, on_delete=models.SET_NULL, related_name="serial_units"
    )
    current_location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    current_holder = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.IN_STOCK)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "serial_number"], name="uniq_serialunit_org_serial"
            ),
        ]
        ordering = ["serial_number"]

    def __str__(self):
        return self.serial_number


class StockMovement(TenantOwnedModel):
    """THE LEDGER. Append-only — never updated, never deleted. A mistake is corrected by a
    compensating movement, not an edit. The only writer is apply_movement()."""

    class MovementType(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        ISSUE = "ISSUE", "Issue"
        RETURN = "RETURN", "Return"
        TRANSFER_OUT = "TRANSFER_OUT", "Transfer out"
        TRANSFER_IN = "TRANSFER_IN", "Transfer in"
        ADJUSTMENT_UP = "ADJUSTMENT_UP", "Adjustment up"
        ADJUSTMENT_DOWN = "ADJUSTMENT_DOWN", "Adjustment down"
        DAMAGE = "DAMAGE", "Damage"
        EXPIRY = "EXPIRY", "Expiry"
        DISPOSAL = "DISPOSAL", "Disposal"
        OPENING = "OPENING", "Opening balance"

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="movements")
    batch = models.ForeignKey(
        Batch, null=True, blank=True, on_delete=models.PROTECT, related_name="movements"
    )
    serial_unit = models.ForeignKey(
        SerialUnit, null=True, blank=True, on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    balance_after = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # GenericFK → GRN / Issue / Adjustment. Target models don't all exist yet (procurement
    # is Phase 5, issuance lands later this phase) — GenericForeignKey doesn't need them to.
    source_content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    source_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    source = GenericForeignKey("source_content_type", "source_object_id")

    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="stockmovement_quantity_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "item", "created_at"]),
            models.Index(fields=["organization", "movement_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError(
                "StockMovement is append-only — corrections are compensating movements."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movement_type} {self.quantity} {self.item.sku} @ {self.location.code}"
