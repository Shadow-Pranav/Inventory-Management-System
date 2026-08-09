import pytest
from django.test import RequestFactory

from apps.core.context import clear_current_organization, set_current_organization
from apps.tenancy.tests.factories import MembershipFactory, OrganizationFactory, UserFactory

from ..forms import ItemForm
from ..tests.factories import CategoryFactory, UnitOfMeasureFactory


def _fake_request(user, organization):
    request = RequestFactory().get("/")
    request.user = user
    request.organization = organization
    request.is_trust_scope = False
    return request


@pytest.mark.django_db
def test_item_form_class_construction_does_not_crash():
    """Regression test: TenantModelForm subclasses with FK fields to TenantOwnedModel used
    to raise UnscopedQueryError at import/class-definition time (fixed in apps/core/forms.py
    via TenantModelFormMetaclass). Merely importing/instantiating ItemForm with no request
    must not touch the DB or the active-organization contextvar at all.
    """
    form = ItemForm()
    assert "category" in form.fields
    assert "uom" in form.fields
    assert form.fields["category"].queryset.count() == 0
    assert form.fields["uom"].queryset.count() == 0


@pytest.mark.django_db
def test_item_form_narrows_category_and_uom_to_request_org():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    category_a = CategoryFactory(organization=org_a)
    category_b = CategoryFactory(organization=org_b)
    uom_a = UnitOfMeasureFactory(organization=org_a)
    UnitOfMeasureFactory(organization=org_b)

    user = UserFactory()
    MembershipFactory(user=user, organization=org_a)
    request = _fake_request(user, org_a)

    form = ItemForm(request=request)
    category_choices = set(form.fields["category"].queryset)
    assert category_a in category_choices
    assert category_b not in category_choices
    assert form.fields["uom"].queryset.get() == uom_a


@pytest.mark.django_db
def test_item_form_rejects_cross_org_category_in_post():
    """`form.is_valid()` runs `full_clean()`, which validates Item's UniqueConstraints via
    `_default_manager` (the strict TenantManager) — same as every other TenantOwnedModel
    query, it needs the active-organization contextvar set. In a real request the
    OrganizationMiddleware sets it before the view runs; here we set it ourselves, exactly
    like test_isolation.py's ORM-level assertions do.
    """
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    category_b = CategoryFactory(organization=org_b)
    uom_a = UnitOfMeasureFactory(organization=org_a)

    user = UserFactory()
    MembershipFactory(user=user, organization=org_a)
    request = _fake_request(user, org_a)

    set_current_organization(org_a)
    try:
        form = ItemForm(
            data={
                "name": "Stolen item",
                "sku": "STEAL-1",
                "category": category_b.pk,
                "uom": uom_a.pk,
                "item_type": "CONSUMABLE",
                "tracking_mode": "NONE",
                "reorder_level": "0",
                "min_order_qty": "0",
                "lead_time_days": "0",
                "gst_rate": "0",
                "is_active": True,
            },
            request=request,
        )
        assert not form.is_valid()
        assert "category" in form.errors
    finally:
        clear_current_organization()
