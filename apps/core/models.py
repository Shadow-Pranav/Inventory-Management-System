from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
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


class AuditLog(TenantOwnedModel):
    """Written only by apps/core/audit.py's signal receivers — never construct one by hand
    in a view. `organization` is the org whose data changed, which is not necessarily the
    actor's own org: a trust admin editing IMS data produces a row with organization=IMS and
    actor_scope=TRUST (context 02 §4), visible to the IMS org admin as oversight."""

    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"

    class ActorScope(models.TextChoices):
        ORG = "ORG", "Within organisation"
        TRUST = "TRUST", "Trust admin, cross-org"

    action = models.CharField(max_length=10, choices=Action.choices)
    actor_scope = models.CharField(
        max_length=10, choices=ActorScope.choices, default=ActorScope.ORG
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "content_type", "object_id"])]

    def __str__(self):
        return f"{self.action} {self.content_type.model}#{self.object_id} by {self.created_by}"

    def save(self, *args, **kwargs):
        # Append-only, same rule as StockMovement (D-14) — the audit trail's integrity is
        # the point; a silent update would be invisible corruption of the record itself.
        if self.pk is not None:
            raise ValidationError("AuditLog is append-only — it cannot be updated.")
        super().save(*args, **kwargs)
