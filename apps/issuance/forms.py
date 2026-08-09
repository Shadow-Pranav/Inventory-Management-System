from apps.core.forms import TenantModelForm

from .models import IssueRequest


class IssueRequestForm(TenantModelForm):
    tenant_fields = ["department"]

    class Meta:
        model = IssueRequest
        fields = ["department", "purpose"]
