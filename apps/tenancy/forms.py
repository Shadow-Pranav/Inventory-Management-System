from django import forms

from apps.core.forms import TenantModelForm

from .models import Department, Membership


class MembershipInviteForm(forms.Form):
    """Creates a `User` (if one doesn't already exist for the email) and a `Membership` in
    the inviting org admin's organisation. Never a `ModelForm` — one submission touches two
    models, and `User` isn't tenant-owned."""

    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(choices=Membership.Role.choices)
    # .all_objects.none(), not .objects.none() — see context 02 §3 / MEMORY.md G-09: a plain
    # Form's class-body queryset default is evaluated at import time, before any request.
    department = forms.ModelChoiceField(queryset=Department.all_objects.none(), required=False)

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        if request is not None:
            self.fields["department"].queryset = Department.objects.for_request(request)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class MembershipRoleForm(TenantModelForm):
    """Org admin editing an existing member's role/department/active flag. Never `user` or
    `organization` — those are set once at invite time and aren't editable here."""

    tenant_fields = ["department"]

    class Meta:
        model = Membership
        fields = ["role", "department", "is_active"]


class DepartmentForm(TenantModelForm):
    tenant_fields = ["parent"]

    class Meta:
        model = Department
        fields = ["name", "code", "parent", "cost_centre_code"]
