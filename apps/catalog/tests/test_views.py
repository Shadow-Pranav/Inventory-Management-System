import pytest

from apps.tenancy.models import Membership
from apps.tenancy.tests.factories import MembershipFactory, OrganizationFactory, UserFactory

from .factories import CategoryFactory, ItemFactory, UnitOfMeasureFactory


@pytest.mark.django_db
def test_item_list_requires_login(client):
    response = client.get("/catalog/items/")
    assert response.status_code == 302  # redirected to login


@pytest.mark.django_db
def test_item_list_shows_only_own_org_items(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    item_a = ItemFactory(organization=org_a, name="Org A Item")
    ItemFactory(organization=org_b, name="Org B Item")

    user = UserFactory()
    MembershipFactory(user=user, organization=org_a, role=Membership.Role.STORE_MANAGER)
    client.force_login(user)

    response = client.get("/catalog/items/")
    assert response.status_code == 200
    content = response.content.decode()
    assert item_a.name in content
    assert "Org B Item" not in content


@pytest.mark.django_db
def test_item_create_org_admin_can_create(client):
    org = OrganizationFactory()
    category = CategoryFactory(organization=org)
    uom = UnitOfMeasureFactory(organization=org)
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.ORG_ADMIN)
    client.force_login(user)

    response = client.post(
        "/catalog/items/new/",
        {
            "name": "New Item",
            "sku": "NI-001",
            "category": category.pk,
            "uom": uom.pk,
            "item_type": "CONSUMABLE",
            "tracking_mode": "NONE",
            "reorder_level": "0",
            "min_order_qty": "0",
            "lead_time_days": "0",
            "gst_rate": "0",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    from apps.catalog.models import Item

    assert Item.all_objects.filter(organization=org, sku="NI-001").exists()


@pytest.mark.django_db
def test_item_create_auditor_forbidden(client):
    org = OrganizationFactory()
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.AUDITOR)
    client.force_login(user)

    response = client.get("/catalog/items/new/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_item_detail_404s_for_other_org(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    item_b = ItemFactory(organization=org_b)

    user = UserFactory()
    MembershipFactory(user=user, organization=org_a, role=Membership.Role.STORE_MANAGER)
    client.force_login(user)

    response = client.get(f"/catalog/items/{item_b.pk}/")
    assert response.status_code == 404
