from django.contrib import messages
from django.shortcuts import redirect, render

from apps.tenancy.decorators import require_org_context, require_role
from apps.tenancy.models import Membership

from .forms import IssueRequestForm
from .models import IssueRequest


@require_org_context
def issue_request_list(request):
    requests_qs = IssueRequest.objects.for_request(request).select_related(
        "department", "requested_by"
    )
    return render(request, "issuance/issue_request_list.html", {"issue_requests": requests_qs})


@require_role(
    Membership.Role.ORG_ADMIN,
    Membership.Role.STORE_MANAGER,
    Membership.Role.DEPT_STAFF,
    write=True,
)
def issue_request_create(request):
    if request.organization is None:
        return redirect("tenancy:switch_organization")
    form = IssueRequestForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        issue_request = form.save(commit=False)
        issue_request.organization = request.organization
        issue_request.requested_by = request.user
        issue_request.created_by = request.user
        issue_request.save()
        messages.success(request, "Issue request raised.")
        return redirect("issuance:issue_request_list")
    return render(request, "issuance/issue_request_form.html", {"form": form})
