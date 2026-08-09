from django.conf import settings
from django.db import models

from .context import get_current_organization
from .exceptions import UnscopedQueryError


class TenantQuerySet(models.QuerySet):
    def for_organization(self, organization):
        return self.filter(organization=organization)

    def for_request(self, request):
        if getattr(request, "is_trust_scope", False):
            return self._unscoped()
        if request.organization is None:
            return self.none()
        return self.filter(organization=request.organization)

    def _unscoped(self):
        return self.__class__(self.model, using=self._db)._chain()


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is not None:
            return qs.filter(organization=org)
        if settings.STRICT_TENANCY:
            raise UnscopedQueryError(
                f"{self.model.__name__}.objects accessed with no active organization. "
                f"Use .for_request(request), .for_organization(org), or all_objects."
            )
        return qs

    def for_request(self, request):
        # Bypasses get_queryset()'s strict check: this is an explicit, self-scoping entry
        # point (the trust-admin path included) and must not depend on the ambient
        # contextvar. Without this override, Manager.from_queryset()'s generated wrapper
        # would call get_queryset() first and raise before .for_request()'s own
        # is_trust_scope handling ever ran. See MEMORY.md G-07.
        return TenantQuerySet(self.model, using=self._db).for_request(request)

    def for_organization(self, organization):
        return TenantQuerySet(self.model, using=self._db).for_organization(organization)
