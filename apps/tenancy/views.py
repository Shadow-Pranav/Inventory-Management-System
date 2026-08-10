from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.models import AuditLog
from apps.tenancy.decorators import get_tenant_object, require_role, require_trust_admin

from .emails import send_password_setup_email
from .forms import DepartmentForm, MembershipInviteForm, MembershipRoleForm, OrganizationForm
from .models import Department, Membership, Organization

User = get_user_model()


def no_access(request):
    return render(request, "tenancy/no_access.html")


@login_required
def switch_organization(request):
    if request.user.is_trust_admin:
        available = Organization.objects.filter(is_active=True).order_by("name")
    else:
        available = (
            Organization.objects.filter(
                memberships__user=request.user,
                memberships__is_active=True,
                is_active=True,
            )
            .distinct()
            .order_by("name")
        )

    if request.method == "POST":
        org_id = request.POST.get("organization_id")
        if not org_id:
            request.session.pop("active_organization_id", None)
        elif available.filter(pk=org_id).exists():
            request.session["active_organization_id"] = org_id
        return redirect(request.POST.get("next") or "admin:index")

    return render(
        request,
        "tenancy/switch_organization.html",
        {"available_organizations": available},
    )


def _membership_queryset(request):
    """`Membership` predates `TenantOwnedModel` (it links a cross-org `User` to one
    `Organization`) and isn't a `TenantOwnedModel` subclass — no `TenantManager`, no
    `.for_request()`, no `get_tenant_object()`. Scoped by hand here, the same way
    `switch_organization` above already scopes it. Flagged as a deferred architecture
    question in MEMORY.md rather than changed mid-phase (on_delete semantics differ from
    TenantOwnedModel's default and a base-class change deserves its own slice)."""
    qs = Membership.objects.select_related("user", "organization", "department")
    if request.is_trust_scope:
        return qs
    if request.organization is None:
        return qs.none()
    return qs.filter(organization=request.organization)


def _unique_username(email):
    base = email.split("@")[0]
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f"{base}{suffix}"
    return username


@require_role(Membership.Role.ORG_ADMIN)
def member_list(request):
    members = _membership_queryset(request).order_by("user__email")
    return render(request, "tenancy/member_list.html", {"members": members})


@require_role(Membership.Role.ORG_ADMIN, write=True)
def member_invite(request):
    if request.organization is None:
        return redirect("tenancy:switch_organization")
    form = MembershipInviteForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": _unique_username(email),
                "first_name": form.cleaned_data["first_name"],
                "last_name": form.cleaned_data["last_name"],
            },
        )
        if user_created:
            user.set_unusable_password()
            user.save()

        _, member_created = Membership.objects.get_or_create(
            user=user,
            organization=request.organization,
            defaults={
                "role": form.cleaned_data["role"],
                "department": form.cleaned_data["department"],
            },
        )
        if not member_created:
            form.add_error("email", "This person is already a member of this organisation.")
        else:
            send_password_setup_email(request, user)
            messages.success(request, f"Invited {user.email} — a password-setup email was sent.")
            return redirect("tenancy:member_list")
    return render(request, "tenancy/member_form.html", {"form": form})


@require_role(Membership.Role.ORG_ADMIN, write=True)
def member_update(request, pk):
    membership = get_object_or_404(_membership_queryset(request), pk=pk)
    form = MembershipRoleForm(request.POST or None, instance=membership, request=request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated {membership.user.email}.")
        return redirect("tenancy:member_list")
    return render(
        request, "tenancy/member_role_form.html", {"form": form, "membership": membership}
    )


@require_role(Membership.Role.ORG_ADMIN)
def department_list(request):
    departments = Department.objects.for_request(request).select_related("parent")
    return render(request, "tenancy/department_list.html", {"departments": departments})


@require_role(Membership.Role.ORG_ADMIN, write=True)
def department_create(request):
    if request.organization is None:
        return redirect("tenancy:switch_organization")
    form = DepartmentForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        department = form.save(commit=False)
        department.organization = request.organization
        department.created_by = request.user
        department.save()
        messages.success(request, f"Department '{department.name}' created.")
        return redirect("tenancy:department_list")
    return render(request, "tenancy/department_form.html", {"form": form})


@require_role(Membership.Role.ORG_ADMIN, write=True)
def department_update(request, pk):
    department = get_tenant_object(Department, request, pk)
    form = DepartmentForm(request.POST or None, instance=department, request=request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Department '{department.name}' updated.")
        return redirect("tenancy:department_list")
    return render(request, "tenancy/department_form.html", {"form": form, "department": department})


@require_role(Membership.Role.ORG_ADMIN, Membership.Role.AUDITOR)
def audit_log_list(request):
    entries = AuditLog.objects.for_request(request).select_related("content_type", "created_by")[
        :200
    ]
    return render(request, "tenancy/audit_log_list.html", {"entries": entries})


@require_trust_admin
def org_list(request):
    organizations = Organization.objects.order_by("name")
    return render(request, "tenancy/org_list.html", {"organizations": organizations})


@require_trust_admin
def org_create(request):
    form = OrganizationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        org = form.save()
        # Pin the trust admin to the org they just created so the next click — inviting the
        # first Org Admin — lands member_invite in the right organisation without a manual
        # switch. member_invite already works for a trust admin: require_role's is_trust_admin
        # bypass plus a pinned request.organization is all it needs.
        request.session["active_organization_id"] = str(org.pk)
        messages.success(request, f"Organisation '{org.name}' created. Invite its first admin.")
        return redirect("tenancy:member_invite")
    return render(request, "tenancy/org_form.html", {"form": form})


@require_trust_admin
def org_update(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    form = OrganizationForm(request.POST or None, instance=org)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Organisation '{org.name}' updated.")
        return redirect("tenancy:org_list")
    return render(request, "tenancy/org_form.html", {"form": form, "organization": org})


@require_trust_admin
def user_search(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        users = User.objects.filter(
            Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
        ).prefetch_related("memberships__organization")[:50]
        results = list(users)
    return render(request, "tenancy/user_search.html", {"query": query, "results": results})
