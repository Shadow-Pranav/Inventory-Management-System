import pytest

from apps.tenancy.models import Membership
from apps.tenancy.tests.factories import (
    DepartmentFactory,
    MembershipFactory,
    OrganizationFactory,
    UserFactory,
)

from ..models import IssueRequest


@pytest.mark.django_db
def test_issue_request_create(client):
    org = OrganizationFactory()
    department = DepartmentFactory(organization=org)
    user = UserFactory()
    MembershipFactory(
        user=user, organization=org, role=Membership.Role.DEPT_STAFF, department=department
    )
    client.force_login(user)

    response = client.post(
        "/issuance/issue-requests/new/",
        {"department": department.pk, "purpose": "Monthly stationery"},
    )
    assert response.status_code == 302
    issue_request = IssueRequest.all_objects.get(organization=org, purpose="Monthly stationery")
    assert issue_request.requested_by == user


@pytest.mark.django_db
def test_issue_request_cannot_use_other_org_department(client):
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    department_b = DepartmentFactory(organization=org_b)
    user = UserFactory()
    MembershipFactory(user=user, organization=org_a, role=Membership.Role.DEPT_STAFF)
    client.force_login(user)

    response = client.post(
        "/issuance/issue-requests/new/",
        {"department": department_b.pk, "purpose": "Should fail"},
    )
    assert response.status_code == 200
    assert not IssueRequest.all_objects.filter(purpose="Should fail").exists()
