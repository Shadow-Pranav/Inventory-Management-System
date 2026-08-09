from django import forms

from apps.catalog.models import Item

from .models import Location, StockMovement


class StockAdjustmentForm(forms.Form):
    """Not a ModelForm over StockLevel — adjustments go through apply_movement(), never a
    direct field write (context 04 §2). `item`/`location` querysets are narrowed to the
    request's organization here, the same job TenantModelForm.tenant_fields does for real
    ModelForms.
    """

    # Class-body queryset must go through `all_objects` (unscoped), never `objects` (the
    # strict TenantManager) — this evaluates at class-definition/import time, with no
    # request and no active-organization contextvar. See apps/core/forms.py for the fuller
    # version of this same problem in TenantModelForm.
    item = forms.ModelChoiceField(queryset=Item.all_objects.none())
    location = forms.ModelChoiceField(queryset=Location.all_objects.none())
    direction = forms.ChoiceField(
        choices=[
            (StockMovement.MovementType.ADJUSTMENT_UP, "Increase"),
            (StockMovement.MovementType.ADJUSTMENT_DOWN, "Decrease"),
        ]
    )
    quantity = forms.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    reason = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        if request is not None:
            self.fields["item"].queryset = Item.objects.for_request(request)
            self.fields["location"].queryset = Location.objects.for_request(request)
