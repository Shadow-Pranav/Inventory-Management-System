from django.contrib import messages
from django.shortcuts import redirect, render

from apps.tenancy.decorators import require_org_context, require_role
from apps.tenancy.models import Membership

from .exceptions import InsufficientStock
from .forms import StockAdjustmentForm
from .models import StockLevel
from .services import apply_movement


@require_org_context
def stock_level_list(request):
    levels = StockLevel.objects.for_request(request).select_related("item", "location", "batch")
    return render(request, "inventory/stock_level_list.html", {"levels": levels})


@require_role(Membership.Role.ORG_ADMIN, Membership.Role.STORE_MANAGER, write=True)
def stock_adjustment_create(request):
    if request.organization is None:
        return redirect("tenancy:switch_organization")
    form = StockAdjustmentForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        try:
            apply_movement(
                organization=request.organization,
                item=form.cleaned_data["item"],
                location=form.cleaned_data["location"],
                movement_type=form.cleaned_data["direction"],
                quantity=form.cleaned_data["quantity"],
                actor=request.user,
                reason=form.cleaned_data["reason"],
            )
        except InsufficientStock as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Stock adjustment recorded.")
            return redirect("inventory:stock_level_list")
    return render(request, "inventory/stock_adjustment_form.html", {"form": form})
