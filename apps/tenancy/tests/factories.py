import factory
from django.contrib.auth import get_user_model

from apps.core.factories import TenantModelFactory
from apps.tenancy.models import Department, Membership, Organization

User = get_user_model()


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    slug = factory.Sequence(lambda n: f"test-org-{n}")
    name = factory.LazyAttribute(lambda o: f"Test Org {o.slug}")
    short_name = factory.LazyAttribute(lambda o: o.slug)
    org_type = Organization.OrgType.COLLEGE


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"test-user-{n}")
    email = factory.LazyAttribute(lambda u: f"{u.username}@test.local")


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    role = Membership.Role.STORE_MANAGER
    is_active = True


class DepartmentFactory(TenantModelFactory):
    """Registered by naming convention for apps/tenancy/tests/test_isolation.py's
    auto-discovery: <app_label>.tests.factories.<ModelName>Factory."""

    class Meta:
        model = Department

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Test Department {n}")
    code = factory.Sequence(lambda n: f"DEPT{n}")
