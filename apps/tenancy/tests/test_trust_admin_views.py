import pytest
from django.core import mail
from django.urls import reverse

from apps.tenancy.models import Membership, Organization

from .factories import MembershipFactory, OrganizationFactory, UserFactory

pytestmark = pytest.mark.django_db


def _login_trust_admin(client):
    user = UserFactory(is_trust_admin=True)
    client.force_login(user)
    return user


def test_org_list_forbidden_for_non_trust_admin(client):
    org = OrganizationFactory()
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.ORG_ADMIN)
    client.force_login(user)

    response = client.get(reverse("tenancy:org_list"))
    assert response.status_code == 403


def test_org_create_pins_session_and_redirects_to_member_invite(client):
    _login_trust_admin(client)

    response = client.post(
        reverse("tenancy:org_create"),
        {
            "name": "SRMS New College",
            "short_name": "NEWCOL",
            "slug": "newcol",
            "org_type": Organization.OrgType.COLLEGE,
            "address": "",
            "city": "",
            "state": "",
            "pincode": "",
            "contact_email": "",
            "contact_phone": "",
            "theme_color": "",
            "fiscal_year_start_month": 4,
            "currency": "INR",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("tenancy:member_invite")
    org = Organization.objects.get(slug="newcol")
    assert client.session["active_organization_id"] == str(org.pk)


def test_org_create_then_invite_first_admin_end_to_end(client):
    """The whole point of pinning on create: the very next request (member_invite) must
    work for a trust admin with no membership of their own in the new org."""
    _login_trust_admin(client)
    client.post(
        reverse("tenancy:org_create"),
        {
            "name": "SRMS Another College",
            "short_name": "ANOTH",
            "slug": "anoth",
            "org_type": Organization.OrgType.COLLEGE,
            "fiscal_year_start_month": 4,
            "currency": "INR",
            "is_active": "on",
        },
    )
    org = Organization.objects.get(slug="anoth")

    response = client.post(
        reverse("tenancy:member_invite"),
        {
            "email": "first.admin@test.local",
            "role": Membership.Role.ORG_ADMIN,
            "department": "",
        },
    )
    assert response.status_code == 302
    assert Membership.objects.filter(
        organization=org, user__email="first.admin@test.local", role=Membership.Role.ORG_ADMIN
    ).exists()
    assert len(mail.outbox) == 1


def test_org_update_edits_existing_org(client):
    _login_trust_admin(client)
    org = OrganizationFactory(name="Old Name")

    response = client.post(
        reverse("tenancy:org_update", args=[org.pk]),
        {
            "name": "New Name",
            "short_name": org.short_name,
            "slug": org.slug,
            "org_type": org.org_type,
            "fiscal_year_start_month": 4,
            "currency": "INR",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    org.refresh_from_db()
    assert org.name == "New Name"


def test_user_search_forbidden_for_non_trust_admin(client):
    org = OrganizationFactory()
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.ORG_ADMIN)
    client.force_login(user)

    response = client.get(reverse("tenancy:user_search"), {"q": "test"})
    assert response.status_code == 403


def test_user_search_finds_users_across_organizations(client):
    _login_trust_admin(client)
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    target = UserFactory(email="findme@test.local", first_name="Findable")
    MembershipFactory(user=target, organization=org_a, role=Membership.Role.STORE_MANAGER)
    MembershipFactory(user=target, organization=org_b, role=Membership.Role.AUDITOR)
    UserFactory(email="noise@test.local")

    response = client.get(reverse("tenancy:user_search"), {"q": "findme"})
    assert response.status_code == 200
    content = response.content.decode()
    assert "findme@test.local" in content
    assert "noise@test.local" not in content
    assert org_a.short_name in content
    assert org_b.short_name in content


def test_user_search_no_query_shows_no_results(client):
    _login_trust_admin(client)
    UserFactory(email="someone@test.local")

    response = client.get(reverse("tenancy:user_search"))
    assert response.status_code == 200
    assert "someone@test.local" not in response.content.decode()
