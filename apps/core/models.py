from django.conf import settings
from django.db import models

from .managers import TenantManager


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        abstract = True


class TenantOwnedModel(TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="+"
    )

    # objects must stay first: Django uses the first-declared manager as `_default_manager`
    # internally (some admin/reverse-relation code paths), and that must be the strict,
    # scoped TenantManager — never the unscoped all_objects. Deliberately against DJ012.
    objects = TenantManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        abstract = True
