"""Signal receivers that populate `AuditLog` for every model listed in
`settings.AUDITED_MODELS`. Connected once from `CoreConfig.ready()` — do not import this
module anywhere else for its side effects, and never construct an `AuditLog` row by hand.

`changes` format:
- CREATE / UPDATE: `{field_name: [old, new]}`, `old` is `None` for CREATE.
- DELETE: `{field_name: value}` — the record's last known state, not a diff.
"""

import datetime

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save, pre_save

from .context import get_current_actor, get_current_actor_scope
from .models import AuditLog

SKIP_FIELDS = {"updated_at"}
_PREVIOUS_STATE_ATTR = "_audit_previous_state"


def _resolve_audited_models():
    return [apps.get_model(label) for label in settings.AUDITED_MODELS]


def _manager_for(model):
    # Cross-org fetch regardless of the ambient contextvar — the audit trail must see a
    # trust admin's unpinned write just as clearly as an org member's scoped one. Same
    # rationale as the tenancy layer's own all_objects escape hatch (context 02 §2).
    return getattr(model, "all_objects", None) or model._default_manager


def _serialize(value):
    """JSONField-safe form of any model field value. Anything that isn't already a JSON
    primitive (Decimal, UUID, FieldFile, ...) is stringified — this is an audit trail, not a
    faithful round-trippable snapshot, so `str()` is the right amount of effort."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    return str(value)


def _field_state(instance):
    return {
        field.name: _serialize(getattr(instance, field.attname))
        for field in instance._meta.fields
        if field.name not in SKIP_FIELDS
    }


def _record(*, instance, action, changes):
    if not changes:
        return
    organization_model = apps.get_model("tenancy", "Organization")
    organization = (
        instance
        if isinstance(instance, organization_model)
        else getattr(instance, "organization", None)
    )
    if organization is None:
        return
    AuditLog.all_objects.create(
        organization=organization,
        actor_scope=get_current_actor_scope(),
        created_by=get_current_actor(),
        action=action,
        content_type=ContentType.objects.get_for_model(instance.__class__),
        object_id=instance.pk,
        object_repr=str(instance)[:200],
        changes=changes,
    )


def _pre_save(sender, instance, raw, **kwargs):
    if raw:  # fixture loading — no meaningful actor/diff context
        return
    previous = _manager_for(sender).filter(pk=instance.pk).first() if instance.pk else None
    setattr(instance, _PREVIOUS_STATE_ATTR, _field_state(previous) if previous else None)


def _post_save(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if created:
        changes = {field: [None, value] for field, value in _field_state(instance).items()}
        _record(instance=instance, action=AuditLog.Action.CREATE, changes=changes)
        return

    previous_state = getattr(instance, _PREVIOUS_STATE_ATTR, None)
    if previous_state is None:  # pre_save found no row — shouldn't happen, fail closed
        return
    current_state = _field_state(instance)
    changes = {
        field: [previous_state[field], current_state[field]]
        for field in current_state
        if previous_state.get(field) != current_state[field]
    }
    _record(instance=instance, action=AuditLog.Action.UPDATE, changes=changes)


def _post_delete(sender, instance, **kwargs):
    _record(instance=instance, action=AuditLog.Action.DELETE, changes=_field_state(instance))


def connect():
    for model in _resolve_audited_models():
        label = model._meta.label
        pre_save.connect(_pre_save, sender=model, dispatch_uid=f"audit-pre-save-{label}")
        post_save.connect(_post_save, sender=model, dispatch_uid=f"audit-post-save-{label}")
        post_delete.connect(_post_delete, sender=model, dispatch_uid=f"audit-post-delete-{label}")
