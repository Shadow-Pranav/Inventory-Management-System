import pytest
from django.core.exceptions import ValidationError

from apps.catalog.tests.factories import UnitOfMeasureFactory
from apps.core.context import clear_current_actor, set_current_actor
from apps.core.models import AuditLog
from apps.tenancy.tests.factories import DepartmentFactory, OrganizationFactory, UserFactory
from apps.tenancy.tests.test_isolation import FakeRequest

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_actor_after_test():
    yield
    clear_current_actor()


def test_create_writes_audit_log_with_full_field_state():
    org = OrganizationFactory()
    actor = UserFactory()
    set_current_actor(actor, "ORG")

    dept = DepartmentFactory(organization=org, name="Pharmacy")

    entry = AuditLog.all_objects.get(
        organization=org, action=AuditLog.Action.CREATE, object_id=dept.pk
    )
    assert entry.created_by == actor
    assert entry.actor_scope == AuditLog.ActorScope.ORG
    assert entry.changes["name"] == [None, "Pharmacy"]


def test_update_writes_only_the_changed_fields():
    org = OrganizationFactory()
    dept = DepartmentFactory(organization=org, name="Old Name", code="OLD")
    set_current_actor(UserFactory(), "ORG")

    dept.name = "New Name"
    dept.save()

    entry = AuditLog.all_objects.get(
        organization=org, action=AuditLog.Action.UPDATE, object_id=dept.pk
    )
    assert entry.changes == {"name": ["Old Name", "New Name"]}


def test_noop_save_writes_no_audit_log():
    org = OrganizationFactory()
    dept = DepartmentFactory(organization=org)
    set_current_actor(UserFactory(), "ORG")

    before = AuditLog.all_objects.filter(organization=org).count()
    dept.save()  # no field changes
    after = AuditLog.all_objects.filter(organization=org).count()

    assert after == before


def test_delete_writes_audit_log_with_last_known_state():
    org = OrganizationFactory()
    dept = DepartmentFactory(organization=org, name="Radiology")
    dept_pk = dept.pk
    set_current_actor(UserFactory(), "ORG")

    dept.delete()

    entry = AuditLog.all_objects.get(
        organization=org, action=AuditLog.Action.DELETE, object_id=dept_pk
    )
    assert entry.changes["name"] == "Radiology"


def test_trust_admin_write_marked_actor_scope_trust():
    org = OrganizationFactory()
    trust_admin = UserFactory(is_trust_admin=True)
    set_current_actor(trust_admin, "TRUST")

    dept = DepartmentFactory(organization=org)

    entry = AuditLog.all_objects.get(
        organization=org, action=AuditLog.Action.CREATE, object_id=dept.pk
    )
    assert entry.actor_scope == AuditLog.ActorScope.TRUST


def test_organization_creation_is_audited_against_itself():
    set_current_actor(UserFactory(), "ORG")
    org = OrganizationFactory()

    entry = AuditLog.all_objects.get(
        organization=org, action=AuditLog.Action.CREATE, object_id=org.pk
    )
    assert entry.object_repr == str(org)


def test_audit_log_is_org_scoped():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    set_current_actor(UserFactory(), "ORG")
    DepartmentFactory(organization=org_a)
    DepartmentFactory(organization=org_b)

    request = FakeRequest(organization=org_a)
    entries = AuditLog.objects.for_request(request)
    assert entries.count() >= 1
    assert all(entry.organization_id == org_a.pk for entry in entries)


def test_audit_log_is_append_only():
    org = OrganizationFactory()
    set_current_actor(UserFactory(), "ORG")
    dept = DepartmentFactory(organization=org)
    entry = AuditLog.all_objects.get(
        organization=org, action=AuditLog.Action.CREATE, object_id=dept.pk
    )

    with pytest.raises(ValidationError):
        entry.object_repr = "tampered"
        entry.save()


def test_model_not_in_audited_models_writes_nothing():
    """The signal receivers are only connected for settings.AUDITED_MODELS, not every
    TenantOwnedModel — UnitOfMeasure isn't in that list, so creating one must not touch
    AuditLog at all."""
    org = OrganizationFactory()
    set_current_actor(UserFactory(), "ORG")
    before = AuditLog.all_objects.count()
    UnitOfMeasureFactory(organization=org)
    after = AuditLog.all_objects.count()
    assert after == before
