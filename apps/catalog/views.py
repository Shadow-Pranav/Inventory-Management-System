from django.contrib import messages
from django.shortcuts import redirect, render

from apps.tenancy.decorators import get_tenant_object, require_org_context, require_role
from apps.tenancy.models import Membership

from .forms import CategoryForm, ItemForm
from .models import Category, Item


@require_org_context
def category_list(request):
    categories = Category.objects.for_request(request).select_related("parent")
    return render(request, "catalog/category_list.html", {"categories": categories})


@require_role(Membership.Role.ORG_ADMIN, write=True)
def category_create(request):
    if request.organization is None:
        return redirect("tenancy:switch_organization")
    form = CategoryForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        category = form.save(commit=False)
        category.organization = request.organization
        category.created_by = request.user
        category.save()
        messages.success(request, f"Category '{category.name}' created.")
        return redirect("catalog:category_list")
    return render(request, "catalog/category_form.html", {"form": form})


@require_org_context
def item_list(request):
    items = Item.objects.for_request(request).select_related("category", "uom")
    return render(request, "catalog/item_list.html", {"items": items})


@require_org_context
def item_detail(request, pk):
    item = get_tenant_object(Item, request, pk)
    return render(request, "catalog/item_detail.html", {"item": item})


@require_role(Membership.Role.ORG_ADMIN, Membership.Role.STORE_MANAGER, write=True)
def item_create(request):
    if request.organization is None:
        return redirect("tenancy:switch_organization")
    form = ItemForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.organization = request.organization
        item.created_by = request.user
        item.save()
        messages.success(request, f"Item '{item.name}' created.")
        return redirect("catalog:item_detail", pk=item.pk)
    return render(request, "catalog/item_form.html", {"form": form})


@require_role(Membership.Role.ORG_ADMIN, Membership.Role.STORE_MANAGER, write=True)
def item_update(request, pk):
    item = get_tenant_object(Item, request, pk)
    form = ItemForm(request.POST or None, instance=item, request=request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Item '{item.name}' updated.")
        return redirect("catalog:item_detail", pk=item.pk)
    return render(request, "catalog/item_form.html", {"form": form, "item": item})
