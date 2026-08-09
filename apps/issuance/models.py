from django.conf import settings
from django.db import models

from apps.catalog.models import Item
from apps.core.models import TenantOwnedModel
from apps.inventory.models import Batch
from apps.tenancy.models import Department


class IssueRequest(TenantOwnedModel):
    """The outbound-request concept (was `Order` in the original design — D-06). Only the
    shape lands in Phase 2; approve/issue/reserve flow and document numbering are Phase 6/5.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        PARTIALLY_ISSUED = "PARTIALLY_ISSUED", "Partially issued"
        ISSUED = "ISSUED", "Issued"
        RETURNED = "RETURNED", "Returned"
        CANCELLED = "CANCELLED", "Cancelled"
        REJECTED = "REJECTED", "Rejected"

    # issue_number is unpopulated/non-unique until Phase 5's per-org-per-FY sequence
    # generator lands — do not add a uniqueness constraint here ahead of that.
    issue_number = models.CharField(max_length=50, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="issue_requests"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    total_items = models.PositiveIntegerField(default=0)
    total_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.issue_number or f"IssueRequest #{self.pk}"


class IssueItem(TenantOwnedModel):
    issue_request = models.ForeignKey(IssueRequest, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    quantity_requested = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_issued = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    batch = models.ForeignKey(
        Batch, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.item.sku} x{self.quantity_requested}"
