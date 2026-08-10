"""Auto-discovering tenant isolation suite (context 02 §6).

Discovers every concrete `TenantOwnedModel` subclass via `apps.get_models()`. A model is
covered here automatically once its app registers a `<ModelName>Factory` in
`apps/<app>/tests/factories.py` — nothing to remember beyond that naming convention.

View-level assertions from context 02 §6 (404-not-403 on a foreign org's object, a
cross-org FK POST failing validation, an auditor getting 403 on a write endpoint, and
`?search=` not leaking another org's names) are added once a model has real CRUD views.
None of the current tenant models do yet (Department's UI lands in Phase 3) — only the
manager/queryset-level checks (org-scoped filtering, trust-admin sees all, unscoped access
raises) run until then. Do not read "fewer assertions than context 02 lists" as a gap in
this file; it's a gap in what's been built so far, tracked in MEMORY.md.
"""

import importlib

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.core.context import clear_current_organization, set_current_organization
from apps.core.exceptions import UnscopedQueryError
from apps.core.models import TenantOwnedModel
from apps.tenancy.middleware import OrganizationMiddleware
from apps.tenancy.models import Membership
from apps.tenancy.tests.factories import MembershipFactory, OrganizationFactory, UserFactory

User = get_user_model()


# AuditLog is deliberately excluded from this generic suite: apps/core/audit.py audits
# `tenancy.Organization` itself, so the `OrganizationFactory()` calls every test below makes
# for org_a/org_b are *not* side-effect-free for AuditLog the way they are for every other
# model — each one writes its own "Organization created" row. That breaks the "make() adds
# exactly one row" assumption these four tests share. AuditLog's own isolation (and the
# audit-writing behaviour itself) is covered directly in apps/core/tests/test_audit.py.
EXCLUDED_FROM_GENERIC_SUITE = {"AuditLog"}


def tenant_owned_models():
    return [
        model
        for model in django_apps.get_models()
        if issubclass(model, TenantOwnedModel)
        and not model._meta.abstract
        and model.__name__ not in EXCLUDED_FROM_GENERIC_SUITE
    ]


def factory_for(model):
    try:
        module = importlib.import_module(f"apps.{model._meta.app_label}.tests.factories")
    except ImportError:
        return None
    return getattr(module, f"{model.__name__}Factory", None)


TENANT_MODELS = tenant_owned_models()
MODEL_IDS = [m.__name__ for m in TENANT_MODELS]


class FakeRequest:
    """Minimal stand-in for the parts of HttpRequest the tenant managers/querysets read."""

    def __init__(self, organization=None, is_trust_scope=False):
        self.organization = organization
        self.is_trust_scope = is_trust_scope


@pytest.fixture(autouse=True)
def _clear_thread_local_after_test():
    yield
    clear_current_organization()


@pytest.mark.django_db
@pytest.mark.parametrize("model", TENANT_MODELS, ids=MODEL_IDS)
def test_org_scoped_count_excludes_other_org(model):
    make = factory_for(model)
    if make is None:
        pytest.skip(f"No factory registered for {model.__name__} yet")
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    make(organization=org_b)

    request = FakeRequest(organization=org_a)
    assert model.objects.for_request(request).count() == 0

    make(organization=org_a)
    assert model.objects.for_request(request).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("model", TENANT_MODELS, ids=MODEL_IDS)
def test_trust_admin_sees_all_orgs(model):
    make = factory_for(model)
    if make is None:
        pytest.skip(f"No factory registered for {model.__name__} yet")
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    make(organization=org_a)
    make(organization=org_b)

    request = FakeRequest(is_trust_scope=True)
    assert model.objects.for_request(request).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("model", TENANT_MODELS, ids=MODEL_IDS)
def test_unscoped_manager_access_raises(model):
    make = factory_for(model)
    if make is None:
        pytest.skip(f"No factory registered for {model.__name__} yet")
    org = OrganizationFactory()
    make(organization=org)

    clear_current_organization()
    with pytest.raises(UnscopedQueryError):
        list(model.objects.all())


@pytest.mark.django_db
@pytest.mark.parametrize("model", TENANT_MODELS, ids=MODEL_IDS)
def test_scoped_manager_matches_current_organization(model):
    make = factory_for(model)
    if make is None:
        pytest.skip(f"No factory registered for {model.__name__} yet")
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    make(organization=org_b)
    make(organization=org_a)

    set_current_organization(org_a)
    assert model.objects.count() == 1


@pytest.mark.django_db
def test_membership_role_change_takes_effect_without_relogin():
    org = OrganizationFactory()
    user = UserFactory()
    membership = MembershipFactory(user=user, organization=org, role=Membership.Role.DEPT_STAFF)

    rf = RequestFactory()
    middleware = OrganizationMiddleware(lambda r: None)

    request = rf.get("/")
    request.user = user
    request.session = {}
    middleware(request)
    assert request.membership.role == Membership.Role.DEPT_STAFF

    membership.role = Membership.Role.ORG_ADMIN
    membership.save()

    request = rf.get("/")
    request.user = user
    request.session = {}
    middleware(request)
    assert request.membership.role == Membership.Role.ORG_ADMIN


@pytest.mark.django_db
def test_user_with_no_membership_gets_no_organization():
    user = UserFactory()
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    request.session = {}

    middleware = OrganizationMiddleware(lambda r: None)
    middleware(request)
    assert request.organization is None
    assert request.membership is None


@pytest.mark.django_db
def test_thread_local_cleared_even_if_view_raises():
    org = OrganizationFactory()
    user = UserFactory()
    MembershipFactory(user=user, organization=org, role=Membership.Role.STORE_MANAGER)

    def exploding_view(request):
        raise ValueError("boom")

    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    request.session = {}

    middleware = OrganizationMiddleware(exploding_view)
    with pytest.raises(ValueError):
        middleware(request)

    from apps.core.context import get_current_organization

    assert get_current_organization() is None
