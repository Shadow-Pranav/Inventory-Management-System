from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from apps.core.context import (
    clear_current_actor,
    clear_current_organization,
    set_current_actor,
    set_current_organization,
)

from .models import Membership, Organization


class OrganizationMiddleware:
    """Attach request.organization and request.membership. Never trust user input."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.membership = None
        request.is_trust_scope = False

        if request.user.is_authenticated:
            if request.user.is_trust_admin:
                # Trust admin may pin a view to one org via an explicit,
                # server-validated session key set by a dedicated switcher view.
                pinned = request.session.get("active_organization_id")
                if pinned:
                    request.organization = Organization.objects.filter(
                        pk=pinned, is_active=True
                    ).first()
                request.is_trust_scope = request.organization is None
            else:
                membership = self._resolve_membership(request)
                if membership:
                    request.membership = membership
                    request.organization = membership.organization

        set_current_organization(request.organization)
        # actor_scope="TRUST" marks every write a trust admin makes, in or out of a pinned
        # org — apps/core/audit.py's receivers use it per context 02 §4 ("every trust-admin
        # write against another org's data writes an AuditLog row with actor_scope=TRUST").
        set_current_actor(
            request.user if request.user.is_authenticated else None,
            "TRUST" if getattr(request.user, "is_trust_admin", False) else "ORG",
        )
        try:
            return self.get_response(request)
        finally:
            clear_current_organization()
            clear_current_actor()

    def _resolve_membership(self, request):
        base_qs = Membership.objects.select_related("organization", "department").filter(
            user=request.user, is_active=True, organization__is_active=True
        )
        pinned = request.session.get("active_organization_id")
        if pinned:
            pinned_membership = base_qs.filter(organization_id=pinned).first()
            if pinned_membership:
                return pinned_membership
        if request.user.default_organization_id:
            default_membership = base_qs.filter(
                organization_id=request.user.default_organization_id
            ).first()
            if default_membership:
                return default_membership
        return base_qs.first()


class ForcePasswordChangeMiddleware:
    """Redirects any request from a `must_change_password=True` user (seed_demo accounts,
    which share a public password) to the password-change form — everywhere except that
    form itself and logout, so the user isn't trapped unable to leave the page."""

    EXEMPT_URL_NAMES = {"password_change", "password_change_done", "logout"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.must_change_password:
            try:
                url_name = resolve(request.path).url_name
            except Resolver404:
                url_name = None
            if url_name not in self.EXEMPT_URL_NAMES:
                return redirect("password_change")
        return self.get_response(request)
