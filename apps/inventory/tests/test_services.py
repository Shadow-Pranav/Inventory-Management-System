import threading
from decimal import Decimal

import pytest
from django.db import connection

from apps.catalog.tests.factories import ItemFactory
from apps.inventory.exceptions import InsufficientStock
from apps.inventory.models import StockLevel, StockMovement
from apps.inventory.services import apply_movement
from apps.inventory.tests.factories import LocationFactory
from apps.tenancy.tests.factories import OrganizationFactory


@pytest.mark.django_db
def test_receipt_increases_stock_and_records_movement():
    org = OrganizationFactory()
    item = ItemFactory(organization=org, unit_cost="10.00")
    location = LocationFactory(organization=org)

    movement = apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.RECEIPT,
        quantity=Decimal("5"),
        unit_cost=Decimal("10.00"),
    )

    level = StockLevel.all_objects.get(organization=org, item=item, location=location, batch=None)
    assert level.quantity == Decimal("5")
    assert movement.balance_after == Decimal("5")
    assert movement.quantity == Decimal("5")


@pytest.mark.django_db
def test_issue_more_than_available_raises_and_writes_nothing():
    org = OrganizationFactory()
    item = ItemFactory(organization=org)
    location = LocationFactory(organization=org)
    apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.RECEIPT,
        quantity=Decimal("3"),
        unit_cost=Decimal("5"),
    )

    with pytest.raises(InsufficientStock):
        apply_movement(
            organization=org,
            item=item,
            location=location,
            movement_type=StockMovement.MovementType.ISSUE,
            quantity=Decimal("10"),
        )

    level = StockLevel.all_objects.get(organization=org, item=item, location=location, batch=None)
    assert level.quantity == Decimal("3")
    assert not StockMovement.all_objects.filter(
        item=item, movement_type=StockMovement.MovementType.ISSUE
    ).exists()


@pytest.mark.django_db
def test_moving_average_weights_by_prior_quantity():
    org = OrganizationFactory()
    item = ItemFactory(organization=org, unit_cost="0")
    location = LocationFactory(organization=org)

    apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.RECEIPT,
        quantity=Decimal("10"),
        unit_cost=Decimal("10.00"),
    )
    item.refresh_from_db()
    assert item.unit_cost == Decimal("10.00")

    apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.RECEIPT,
        quantity=Decimal("10"),
        unit_cost=Decimal("20.00"),
    )
    item.refresh_from_db()
    assert item.unit_cost == Decimal("15.00")


@pytest.mark.django_db
def test_issue_never_updates_moving_average():
    org = OrganizationFactory()
    item = ItemFactory(organization=org, unit_cost="10.00")
    location = LocationFactory(organization=org)
    apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.RECEIPT,
        quantity=Decimal("10"),
        unit_cost=Decimal("10.00"),
    )

    apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.ISSUE,
        quantity=Decimal("4"),
    )
    item.refresh_from_db()
    assert item.unit_cost == Decimal("10.00")


@pytest.mark.django_db
def test_stock_movement_is_append_only():
    org = OrganizationFactory()
    item = ItemFactory(organization=org)
    location = LocationFactory(organization=org)
    movement = apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.RECEIPT,
        quantity=Decimal("1"),
        unit_cost=Decimal("1"),
    )

    from django.core.exceptions import ValidationError

    movement.reason = "trying to edit history"
    with pytest.raises(ValidationError):
        movement.save()


@pytest.mark.django_db(transaction=True)
def test_concurrent_issues_exactly_deplete_stock_no_oversell():
    """Phase 2 acceptance: 10 parallel issues of 1 unit from a stock of 5 → exactly 5 succeed."""
    org = OrganizationFactory()
    item = ItemFactory(organization=org)
    location = LocationFactory(organization=org)
    apply_movement(
        organization=org,
        item=item,
        location=location,
        movement_type=StockMovement.MovementType.RECEIPT,
        quantity=Decimal("5"),
        unit_cost=Decimal("1"),
    )

    results = []
    lock = threading.Lock()

    def issue_one():
        try:
            apply_movement(
                organization=org,
                item=item,
                location=location,
                movement_type=StockMovement.MovementType.ISSUE,
                quantity=Decimal("1"),
            )
            with lock:
                results.append("ok")
        except InsufficientStock:
            with lock:
                results.append("insufficient")
        finally:
            connection.close()

    threads = [threading.Thread(target=issue_one) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 5
    assert results.count("insufficient") == 5

    level = StockLevel.all_objects.get(organization=org, item=item, location=location, batch=None)
    assert level.quantity == Decimal("0")
