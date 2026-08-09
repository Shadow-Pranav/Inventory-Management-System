import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from apps.tenancy.decorators import (
    get_tenant_object,
    require_org_context,
    require_role,
    require_trust_admin,
)
from apps.tenancy.models import Department, Membership
from apps.tenancy.tests.factories import (
    DepartmentFactory,
    MembershipFactory,
    OrganizationFactory,
    UserFactory,
)


def _request_for(rf, user, organization=None, membership=None, is_trust_scope=False):
    request = rf.get("/")
    request.user = user
    request.organization = organization
    request.membership = membership
    request.is_trust_scope = is_trust_scope
    return request


@pytest.mark.django_db
def test_require_org_context_redirects_with_no_organization():
    rf = RequestFactory()
    user = UserFactory()
    request = _request_for(rf, user)

    @require_org_context
    def view(request):
        return "ok"

    response = view(request)
    assert response.status_code == 302
    assert response.url == "/no-access/"


@pytest.mark.django_db
def test_require_org_context_allows_trust_scope_with_no_organization():
    rf = RequestFactory()
    user = UserFactory(is_trust_admin=True)
    request = _request_for(rf, user, is_trust_scope=True)

    @require_org_context
    def view(request):
        return "ok"

    assert view(request) == "ok"


@pytest.mark.django_db
def test_require_trust_admin_denies_non_trust_admin():
    rf = RequestFactory()
    user = UserFactory(is_trust_admin=False)
    request = _request_for(rf, user)

    @require_trust_admin
    def view(request):
        return "ok"

    with pytest.raises(PermissionDenied):
        view(request)


@pytest.mark.django_db
def test_require_trust_admin_allows_trust_admin():
    rf = RequestFactory()
    user = UserFactory(is_trust_admin=True)
    request = _request_for(rf, user)

    @require_trust_admin
    def view(request):
        return "ok"

    assert view(request) == "ok"


@pytest.mark.django_db
def test_require_role_allows_matching_role():
    rf = RequestFactory()
    org = OrganizationFactory()
    user = UserFactory()
    membership = MembershipFactory(user=user, organization=org, role=Membership.Role.STORE_MANAGER)
    request = _request_for(rf, user, organization=org, membership=membership)

    @require_role(Membership.Role.STORE_MANAGER, Membership.Role.ORG_ADMIN)
    def view(request):
        return "ok"

    assert view(request) == "ok"


@pytest.mark.django_db
def test_require_role_denies_non_matching_role():
    rf = RequestFactory()
    org = OrganizationFactory()
    user = UserFactory()
    membership = MembershipFactory(user=user, organization=org, role=Membership.Role.DEPT_STAFF)
    request = _request_for(rf, user, organization=org, membership=membership)

    @require_role(Membership.Role.STORE_MANAGER, Membership.Role.ORG_ADMIN)
    def view(request):
        return "ok"

    with pytest.raises(PermissionDenied):
        view(request)


@pytest.mark.django_db
def test_require_role_trust_admin_bypasses_role_check():
    rf = RequestFactory()
    user = UserFactory(is_trust_admin=True)
    request = _request_for(rf, user)

    @require_role(Membership.Role.STORE_MANAGER)
    def view(request):
        return "ok"

    assert view(request) == "ok"


@pytest.mark.django_db
def test_require_role_write_true_rejects_auditor():
    rf = RequestFactory()
    org = OrganizationFactory()
    user = UserFactory()
    membership = MembershipFactory(user=user, organization=org, role=Membership.Role.AUDITOR)
    request = _request_for(rf, user, organization=org, membership=membership)

    @require_role(Membership.Role.AUDITOR, write=True)
    def view(request):
        return "ok"

    with pytest.raises(PermissionDenied):
        view(request)


@pytest.mark.django_db
def test_require_role_write_false_allows_auditor_read():
    rf = RequestFactory()
    org = OrganizationFactory()
    user = UserFactory()
    membership = MembershipFactory(user=user, organization=org, role=Membership.Role.AUDITOR)
    request = _request_for(rf, user, organization=org, membership=membership)

    @require_role(Membership.Role.AUDITOR, write=False)
    def view(request):
        return "ok"

    assert view(request) == "ok"


@pytest.mark.django_db
def test_get_tenant_object_404s_on_cross_org_pk():
    rf = RequestFactory()
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    dept_b = DepartmentFactory(organization=org_b)
    user = UserFactory()
    membership = MembershipFactory(user=user, organization=org_a, role=Membership.Role.ORG_ADMIN)
    request = _request_for(rf, user, organization=org_a, membership=membership)

    from django.http import Http404

    with pytest.raises(Http404):
        get_tenant_object(Department, request, dept_b.pk)


@pytest.mark.django_db
def test_get_tenant_object_returns_same_org_object():
    rf = RequestFactory()
    org_a = OrganizationFactory()
    dept_a = DepartmentFactory(organization=org_a)
    user = UserFactory()
    membership = MembershipFactory(user=user, organization=org_a, role=Membership.Role.ORG_ADMIN)
    request = _request_for(rf, user, organization=org_a, membership=membership)

    found = get_tenant_object(Department, request, dept_a.pk)
    assert found.pk == dept_a.pk
