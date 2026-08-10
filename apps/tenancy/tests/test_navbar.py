"""Phase 3 task 7: navbar links follow role. UX only — the decorator on each view is the
real boundary (context 04 §7); these tests just confirm the links match the decorators."""

import pytest
from django.urls import reverse

from apps.tenancy.models import Membership

from .factories import MembershipFactory, OrganizationFactory, UserFactory

pytestmark = pytest.mark.django_db


def _login(client, org, role):
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=role)
    client.force_login(user)
    return user


def test_dept_staff_sees_catalog_links_but_not_admin_links(client):
    org = OrganizationFactory()
    _login(client, org, Membership.Role.DEPT_STAFF)

    response = client.get(reverse("catalog:item_list"))
    content = response.content.decode()
    assert reverse("catalog:item_list") in content
    assert reverse("tenancy:member_list") not in content
    assert reverse("tenancy:audit_log_list") not in content
    assert reverse("tenancy:org_list") not in content


def test_org_admin_sees_member_and_audit_links_but_not_trust_links(client):
    org = OrganizationFactory()
    _login(client, org, Membership.Role.ORG_ADMIN)

    response = client.get(reverse("catalog:item_list"))
    content = response.content.decode()
    assert reverse("tenancy:member_list") in content
    assert reverse("tenancy:department_list") in content
    assert reverse("tenancy:audit_log_list") in content
    assert reverse("tenancy:org_list") not in content
    assert reverse("tenancy:user_search") not in content


def test_auditor_sees_audit_link_but_not_member_management(client):
    org = OrganizationFactory()
    _login(client, org, Membership.Role.AUDITOR)

    response = client.get(reverse("catalog:item_list"))
    content = response.content.decode()
    assert reverse("tenancy:audit_log_list") in content
    assert reverse("tenancy:member_list") not in content


def test_trust_admin_unpinned_sees_trust_and_catalog_links(client):
    trust_admin = UserFactory(is_trust_admin=True)
    client.force_login(trust_admin)

    response = client.get(reverse("catalog:item_list"))
    content = response.content.decode()
    assert reverse("tenancy:org_list") in content
    assert reverse("tenancy:user_search") in content
    assert reverse("catalog:item_list") in content  # is_trust_scope, not just a pinned org
