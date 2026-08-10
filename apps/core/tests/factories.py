import factory
from django.contrib.contenttypes.models import ContentType

from apps.core.factories import TenantModelFactory
from apps.tenancy.tests.factories import OrganizationFactory

from ..models import AuditLog


class AuditLogFactory(TenantModelFactory):
    """Registered by naming convention for
    apps/tenancy/tests/test_isolation.py's auto-discovery."""

    class Meta:
        model = AuditLog

    organization = factory.SubFactory(OrganizationFactory)
    action = AuditLog.Action.CREATE
    object_id = factory.Sequence(lambda n: n + 1)
    object_repr = factory.Sequence(lambda n: f"Test Object {n}")
    changes = factory.LazyFunction(dict)

    @factory.lazy_attribute
    def content_type(self):
        from apps.tenancy.models import Organization

        return ContentType.objects.get_for_model(Organization)
