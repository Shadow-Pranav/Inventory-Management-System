"""Task 1 of Phase 3 (see PROMPTS.md): a permission matrix (role x view x read/write) as
a test fixture, so the matrix *is* the test. This exercises real URLs through the Django
test client -- unlike test_decorators.py, which unit-tests the decorators in isolation, this
catches a view that forgot to apply a decorator at all.

Add a row here whenever a new view is wired up in catalog/inventory/issuance (or any future
app). The policy encoded below comes from the role table in CLAUDE.md SS6, not from reading
the decorator arguments back out of views.py -- that would just be testing the code against
itself.
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.catalog.tests.factories import CategoryFactory, ItemFactory, UnitOfMeasureFactory
from apps.inventory.tests.factories import LocationFactory, StockLevelFactory
from apps.issuance.tests.factories import IssueRequestFactory
from apps.tenancy.models import Membership
from apps.tenancy.tests.factories import (
    DepartmentFactory,
    MembershipFactory,
    OrganizationFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

ALL_ROLES = [
    Membership.Role.ORG_ADMIN,
    Membership.Role.STORE_MANAGER,
    Membership.Role.DEPT_STAFF,
    Membership.Role.AUDITOR,
]


def _login_as(client, org, role):
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=role)
    client.force_login(user)
    return user


def _build_matrix(org):
    """Returns (label, http_method, path, post_data_or_none, allowed_roles) tuples."""
    category = CategoryFactory(organization=org)
    uom = UnitOfMeasureFactory(organization=org)
    item = ItemFactory(organization=org, category=category, uom=uom)
    location = LocationFactory(organization=org)
    StockLevelFactory(organization=org, item=item, location=location)
    department = DepartmentFactory(organization=org)
    IssueRequestFactory(organization=org, department=department)

    item_form_data = {
        "sku": "PTI-001",
        "category": category.pk,
        "uom": uom.pk,
        "item_type": "CONSUMABLE",
        "tracking_mode": "NONE",
        "reorder_level": "0",
        "min_order_qty": "0",
        "lead_time_days": "0",
        "gst_rate": "0",
        "is_active": "on",
    }

    return [
        (
            "category_list",
            "get",
            reverse("catalog:category_list"),
            None,
            ALL_ROLES,
        ),
        (
            "category_create",
            "post",
            reverse("catalog:category_create"),
            {"name": "Perm Test Cat", "code": "PTC"},
            [Membership.Role.ORG_ADMIN],
        ),
        (
            "item_list",
            "get",
            reverse("catalog:item_list"),
            None,
            ALL_ROLES,
        ),
        (
            "item_detail",
            "get",
            reverse("catalog:item_detail", args=[item.pk]),
            None,
            ALL_ROLES,
        ),
        (
            "item_create",
            "post",
            reverse("catalog:item_create"),
            {**item_form_data, "name": "Perm Test Item"},
            [Membership.Role.ORG_ADMIN, Membership.Role.STORE_MANAGER],
        ),
        (
            "item_update",
            "post",
            reverse("catalog:item_update", args=[item.pk]),
            {**item_form_data, "sku": item.sku, "name": item.name},
            [Membership.Role.ORG_ADMIN, Membership.Role.STORE_MANAGER],
        ),
        (
            "stock_level_list",
            "get",
            reverse("inventory:stock_level_list"),
            None,
            ALL_ROLES,
        ),
        (
            "stock_adjustment_create",
            "post",
            reverse("inventory:stock_adjustment_create"),
            {
                "item": item.pk,
                "location": location.pk,
                "direction": "OPENING",
                "quantity": "1",
                "reason": "permission matrix test",
            },
            [Membership.Role.ORG_ADMIN, Membership.Role.STORE_MANAGER],
        ),
        (
            "issue_request_list",
            "get",
            reverse("issuance:issue_request_list"),
            None,
            ALL_ROLES,
        ),
        (
            "issue_request_create",
            "post",
            reverse("issuance:issue_request_create"),
            {"department": department.pk, "purpose": "permission matrix test"},
            [
                Membership.Role.ORG_ADMIN,
                Membership.Role.STORE_MANAGER,
                Membership.Role.DEPT_STAFF,
            ],
        ),
    ]


@pytest.mark.parametrize("role", ALL_ROLES)
def test_permission_matrix_role_access(client, role):
    org = OrganizationFactory()
    matrix = _build_matrix(org)
    _login_as(client, org, role)

    for label, method, path, data, allowed_roles in matrix:
        response = getattr(client, method)(path, data)
        if role in allowed_roles:
            assert response.status_code != 403, f"{label}: {role} should be permitted, got 403"
        else:
            assert response.status_code == 403, (
                f"{label}: {role} should be forbidden, got {response.status_code}"
            )


def test_permission_matrix_auditor_forbidden_on_every_write_view():
    """Belt-and-braces on Phase 3 Task 2's acceptance criterion, expressed against the
    same matrix used above rather than a hand-picked subset."""
    org = OrganizationFactory()
    matrix = _build_matrix(org)
    client = Client()
    _login_as(client, org, Membership.Role.AUDITOR)

    write_views = [row for row in matrix if row[1] == "post"]
    assert write_views, "matrix has no write views to check"
    for label, method, path, data, _allowed_roles in write_views:
        response = getattr(client, method)(path, data)
        assert response.status_code == 403, (
            f"{label}: auditor should get 403, got {response.status_code}"
        )


def test_permission_matrix_trust_admin_bypasses_every_role_check():
    org = OrganizationFactory()
    matrix = _build_matrix(org)
    trust_admin = UserFactory(is_trust_admin=True)

    client = Client()
    client.force_login(trust_admin)
    session = client.session
    session["active_organization_id"] = str(org.pk)
    session.save()

    for label, method, path, data, _allowed_roles in matrix:
        response = getattr(client, method)(path, data)
        assert response.status_code != 403, f"{label}: trust admin should never get 403, got 403"
