from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Organization


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
