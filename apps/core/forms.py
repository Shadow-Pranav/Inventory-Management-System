from django import forms


class TenantModelForm(forms.ModelForm):
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
