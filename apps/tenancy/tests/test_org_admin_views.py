import pytest
from django.core import mail
from django.urls import reverse

from apps.core.context import clear_current_actor, set_current_actor
from apps.core.models import AuditLog
from apps.tenancy.models import Department, Membership

from .factories import DepartmentFactory, MembershipFactory, OrganizationFactory, UserFactory

pytestmark = pytest.mark.django_db


def _login_org_admin(client, org):
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.ORG_ADMIN)
    client.force_login(user)
    return user


def test_member_list_shows_only_own_org_members(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    _login_org_admin(client, org_a)
    other_member = UserFactory(email="orgb-member@test.local")
    MembershipFactory(user=other_member, organization=org_b, role=Membership.Role.DEPT_STAFF)

    response = client.get(reverse("tenancy:member_list"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "orgb-member@test.local" not in content


def test_member_invite_creates_user_membership_and_sends_email(client):
    org = OrganizationFactory()
    _login_org_admin(client, org)

    response = client.post(
        reverse("tenancy:member_invite"),
        {
            "email": "new.hire@test.local",
            "first_name": "New",
            "last_name": "Hire",
            "role": Membership.Role.DEPT_STAFF,
            "department": "",
        },
    )
    assert response.status_code == 302

    membership = Membership.objects.get(organization=org, user__email="new.hire@test.local")
    assert membership.role == Membership.Role.DEPT_STAFF
    assert not membership.user.has_usable_password()
    assert len(mail.outbox) == 1
    assert "new.hire@test.local" in mail.outbox[0].to


def test_member_invite_existing_org_member_is_rejected(client):
    org = OrganizationFactory()
    _login_org_admin(client, org)
    existing = UserFactory(email="already@test.local")
    MembershipFactory(user=existing, organization=org, role=Membership.Role.DEPT_STAFF)

    response = client.post(
        reverse("tenancy:member_invite"),
        {
            "email": "already@test.local",
            "role": Membership.Role.STORE_MANAGER,
            "department": "",
        },
    )
    assert response.status_code == 200  # form re-rendered with error
    assert Membership.objects.filter(organization=org, user=existing).count() == 1


def test_member_invite_forbidden_for_non_org_admin(client):
    org = OrganizationFactory()
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.STORE_MANAGER)
    client.force_login(user)

    response = client.post(
        reverse("tenancy:member_invite"),
        {"email": "x@test.local", "role": Membership.Role.DEPT_STAFF, "department": ""},
    )
    assert response.status_code == 403


def test_member_update_changes_role_and_deactivates(client):
    org = OrganizationFactory()
    _login_org_admin(client, org)
    target_user = UserFactory()
    membership = MembershipFactory(
        user=target_user, organization=org, role=Membership.Role.DEPT_STAFF
    )

    response = client.post(
        reverse("tenancy:member_update", args=[membership.pk]),
        {"role": Membership.Role.STORE_MANAGER, "department": "", "is_active": ""},
    )
    assert response.status_code == 302
    membership.refresh_from_db()
    assert membership.role == Membership.Role.STORE_MANAGER
    assert membership.is_active is False


def test_member_update_404s_for_other_org_membership(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    _login_org_admin(client, org_a)
    other_membership = MembershipFactory(organization=org_b, role=Membership.Role.DEPT_STAFF)

    response = client.get(reverse("tenancy:member_update", args=[other_membership.pk]))
    assert response.status_code == 404


def test_department_create_and_list(client):
    org = OrganizationFactory()
    _login_org_admin(client, org)

    response = client.post(
        reverse("tenancy:department_create"),
        {"name": "Radiology", "code": "RAD", "parent": "", "cost_centre_code": ""},
    )
    assert response.status_code == 302
    assert Department.all_objects.filter(organization=org, code="RAD").exists()


def test_department_update_404s_for_other_org(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    _login_org_admin(client, org_a)
    dept_b = DepartmentFactory(organization=org_b)

    response = client.get(reverse("tenancy:department_update", args=[dept_b.pk]))
    assert response.status_code == 404


def test_audit_log_list_shows_only_own_org_entries(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    admin_a = _login_org_admin(client, org_a)

    set_current_actor(admin_a, "ORG")
    DepartmentFactory(organization=org_a, name="Org A Dept")
    DepartmentFactory(organization=org_b, name="Org B Dept")
    clear_current_actor()

    response = client.get(reverse("tenancy:audit_log_list"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Org A Dept" in content
    assert "Org B Dept" not in content


def test_audit_log_list_visible_to_auditor(client):
    org = OrganizationFactory()
    auditor = UserFactory()
    MembershipFactory(user=auditor, organization=org, role=Membership.Role.AUDITOR)
    client.force_login(auditor)

    response = client.get(reverse("tenancy:audit_log_list"))
    assert response.status_code == 200


def test_audit_log_list_forbidden_for_store_manager(client):
    org = OrganizationFactory()
    manager = UserFactory()
    MembershipFactory(user=manager, organization=org, role=Membership.Role.STORE_MANAGER)
    client.force_login(manager)

    response = client.get(reverse("tenancy:audit_log_list"))
    assert response.status_code == 403


def test_audit_log_written_for_department_created_through_view(client):
    org = OrganizationFactory()
    _login_org_admin(client, org)

    client.post(
        reverse("tenancy:department_create"),
        {"name": "Cardiology", "code": "CARD", "parent": "", "cost_centre_code": ""},
    )

    dept = Department.all_objects.get(organization=org, code="CARD")
    assert AuditLog.all_objects.filter(
        organization=org, action=AuditLog.Action.CREATE, object_id=dept.pk
    ).exists()
