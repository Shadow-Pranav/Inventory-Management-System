import factory

from apps.catalog.tests.factories import ItemFactory
from apps.core.factories import TenantModelFactory, match_org
from apps.tenancy.tests.factories import DepartmentFactory, OrganizationFactory, UserFactory

from ..models import IssueItem, IssueRequest


class IssueRequestFactory(TenantModelFactory):
    class Meta:
        model = IssueRequest
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    department = factory.SubFactory(DepartmentFactory)
    requested_by = factory.SubFactory(UserFactory)
    purpose = "Routine restock"

    @factory.post_generation
    def _match_org(self, create, extracted, **kwargs):
        if create:
            match_org(self, "department")


class IssueItemFactory(TenantModelFactory):
    class Meta:
        model = IssueItem
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    issue_request = factory.SubFactory(IssueRequestFactory)
    item = factory.SubFactory(ItemFactory)
    quantity_requested = "1"

    @factory.post_generation
    def _match_org(self, create, extracted, **kwargs):
        if create:
            match_org(self, "issue_request", "item")
