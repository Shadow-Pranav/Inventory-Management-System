from django import forms
from django.db import models
from django.forms.models import ModelFormMetaclass
from django.utils.text import capfirst


def _unscoped_fk_formfield_callback(field, **kwargs):
    """Used only at form *class definition* time (see TenantModelFormMetaclass below).

    Django's ModelForm machinery builds a form field for every FK/M2M by calling
    `field.formfield()`. For ForeignKey/ManyToManyField, that method's *own* defaults
    dict does `"queryset": self.remote_field.model._default_manager.using(using)` as a
    dict-literal entry — evaluated unconditionally while the dict is built, before any
    `queryset` we pass in `kwargs` ever gets a chance to override it. `_default_manager`
    is the strict TenantManager for any TenantOwnedModel (G-07: it must stay the default
    manager for other Django internals), so this crashes with UnscopedQueryError at
    import time — no request, no active-organization contextvar, no form instance yet.
    Passing `queryset=...` in kwargs to `field.formfield()` does NOT avoid this; the only
    way is to not call `field.formfield()` for these fields at all.

    `all_objects.none()` here fails closed: any FK/M2M field a form author forgets to
    list in `tenant_fields` renders as an empty, obviously-broken dropdown in dev — not a
    cross-org data leak, and not a crash.
    """
    remote_model = getattr(field.remote_field, "model", None) if field.remote_field else None
    if remote_model is None or not hasattr(remote_model, "all_objects"):
        return field.formfield(**kwargs)

    common = {
        "required": not field.blank,
        "label": capfirst(field.verbose_name),
        "help_text": field.help_text,
        "queryset": remote_model.all_objects.none(),
        **kwargs,
    }
    if isinstance(field, models.ManyToManyField):
        return forms.ModelMultipleChoiceField(**common)
    common["to_field_name"] = field.remote_field.field_name
    return forms.ModelChoiceField(**common)


class TenantModelFormMetaclass(ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        meta = attrs.get("Meta")
        if meta is not None and not hasattr(meta, "formfield_callback"):
            meta.formfield_callback = staticmethod(_unscoped_fk_formfield_callback)
        return super().__new__(mcs, name, bases, attrs)


class TenantModelForm(forms.ModelForm, metaclass=TenantModelFormMetaclass):
    """Narrows every FK-to-tenant-data field to the request's organization.

    Without this, a crafted POST can set a foreign-key field to another org's row and
    it validates cleanly — the dropdown must never even render foreign options.
    """

    tenant_fields: list[str] = []

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        if self.request is None:
            return
        for field_name in self.tenant_fields:
            field = self.fields.get(field_name)
            if field is None:
                continue
            field_model = field.queryset.model
            field.queryset = field_model.objects.for_request(self.request)
