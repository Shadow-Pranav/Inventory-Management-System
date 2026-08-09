from decimal import Decimal

import pytest

from apps.catalog.tests.factories import ItemFactory
from apps.tenancy.models import Membership
from apps.tenancy.tests.factories import MembershipFactory, OrganizationFactory, UserFactory

from ..models import StockLevel
from ..services import apply_movement
from .factories import LocationFactory


@pytest.mark.django_db
def test_stock_level_list_shows_only_own_org(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    item_a = ItemFactory(organization=org_a, name="Org A Item")
    location_a = LocationFactory(organization=org_a)
    item_b = ItemFactory(organization=org_b, name="Org B Item")
    location_b = LocationFactory(organization=org_b)
    apply_movement(
        organization=org_a,
        item=item_a,
        location=location_a,
        movement_type="OPENING",
        quantity=Decimal("5"),
        unit_cost=Decimal("1"),
    )
    apply_movement(
        organization=org_b,
        item=item_b,
        location=location_b,
        movement_type="OPENING",
        quantity=Decimal("5"),
        unit_cost=Decimal("1"),
    )

    user = UserFactory()
    MembershipFactory(user=user, organization=org_a, role=Membership.Role.STORE_MANAGER)
    client.force_login(user)

    response = client.get("/inventory/stock/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Org A Item" in content
    assert "Org B Item" not in content


@pytest.mark.django_db
def test_stock_adjustment_view_routes_through_apply_movement(client):
    org = OrganizationFactory()
    item = ItemFactory(organization=org)
    location = LocationFactory(organization=org)
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.STORE_MANAGER)
    client.force_login(user)

    response = client.post(
        "/inventory/stock/adjust/",
        {
            "item": item.pk,
            "location": location.pk,
            "direction": "ADJUSTMENT_UP",
            "quantity": "7",
            "reason": "Initial count",
        },
    )
    assert response.status_code == 302
    level = StockLevel.all_objects.get(organization=org, item=item, location=location, batch=None)
    assert level.quantity == Decimal("7")


@pytest.mark.django_db
def test_stock_adjustment_cannot_use_other_org_item(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    item_b = ItemFactory(organization=org_b)
    location_a = LocationFactory(organization=org_a)
    user = UserFactory()
    MembershipFactory(user=user, organization=org_a, role=Membership.Role.STORE_MANAGER)
    client.force_login(user)

    response = client.post(
        "/inventory/stock/adjust/",
        {
            "item": item_b.pk,
            "location": location_a.pk,
            "direction": "ADJUSTMENT_UP",
            "quantity": "7",
            "reason": "Should fail",
        },
    )
    assert response.status_code == 200  # re-rendered with form errors, not a redirect
    assert not StockLevel.all_objects.filter(item=item_b, location=location_a).exists()
