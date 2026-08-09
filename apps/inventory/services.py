from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .exceptions import InsufficientStock
from .models import StockLevel, StockMovement

SIGN = {
    StockMovement.MovementType.RECEIPT: 1,
    StockMovement.MovementType.ISSUE: -1,
    StockMovement.MovementType.RETURN: 1,
    StockMovement.MovementType.TRANSFER_OUT: -1,
    StockMovement.MovementType.TRANSFER_IN: 1,
    StockMovement.MovementType.ADJUSTMENT_UP: 1,
    StockMovement.MovementType.ADJUSTMENT_DOWN: -1,
    StockMovement.MovementType.DAMAGE: -1,
    StockMovement.MovementType.EXPIRY: -1,
    StockMovement.MovementType.DISPOSAL: -1,
    StockMovement.MovementType.OPENING: 1,
}

# Moving-average cost updates on stock entering with a known cost basis only — never on
# issue, and never on a transfer (the cost basis moves with the stock, it isn't re-priced).
COST_BEARING = {StockMovement.MovementType.RECEIPT, StockMovement.MovementType.OPENING}


@transaction.atomic
def apply_movement(
    *,
    organization,
    item,
    location,
    movement_type,
    quantity,
    batch=None,
    serial_unit=None,
    unit_cost=None,
    source=None,
    actor=None,
    reason="",
):
    """Append a StockMovement and update the StockLevel row. The only writer of quantity."""
    if quantity <= 0:
        raise ValidationError("quantity must be positive; direction comes from movement_type")

    level, _ = (
        StockLevel.objects.for_organization(organization)
        .select_for_update()
        .get_or_create(
            organization=organization,
            item=item,
            location=location,
            batch=batch,
            defaults={"quantity": Decimal(0)},
        )
    )
    delta = SIGN[movement_type] * quantity
    new_qty = level.quantity + delta
    if new_qty < 0:
        raise InsufficientStock(
            item=item, location=location, available=level.quantity, requested=quantity
        )

    level.quantity = new_qty
    level.save(update_fields=["quantity", "updated_at"])

    effective_unit_cost = unit_cost if unit_cost is not None else item.unit_cost
    if movement_type in COST_BEARING and unit_cost is not None:
        item.unit_cost = _moving_average(item, quantity, unit_cost)
        item.save(update_fields=["unit_cost"])

    content_type = ContentType.objects.get_for_model(source) if source is not None else None
    object_id = source.pk if source is not None else None

    return StockMovement.objects.for_organization(organization).create(
        organization=organization,
        item=item,
        location=location,
        batch=batch,
        serial_unit=serial_unit,
        movement_type=movement_type,
        quantity=quantity,
        balance_after=new_qty,
        unit_cost=effective_unit_cost,
        total_value=quantity * effective_unit_cost,
        source_content_type=content_type,
        source_object_id=object_id,
        reason=reason,
        created_by=actor,
    )


def _moving_average(item, received_qty, received_cost):
    """Weighted average of on-hand cost across all locations, folding in this receipt.
    Called after the receiving StockLevel row has already been saved, so the aggregate
    below is the *post*-receipt total — `total_before` backs that out.
    """
    total_after = StockLevel.objects.for_organization(item.organization).filter(
        item=item
    ).aggregate(total=Sum("quantity"))["total"] or Decimal(0)
    total_before = total_after - received_qty
    if total_before <= 0:
        return received_cost
    return ((total_before * item.unit_cost) + (received_qty * received_cost)) / (
        total_before + received_qty
    )
