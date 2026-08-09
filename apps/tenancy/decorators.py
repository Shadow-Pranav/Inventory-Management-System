from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect


def require_org_context(view_func):
    """Any authenticated user with an active membership (or the trust admin)."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.organization is None and not request.is_trust_scope:
            return redirect("tenancy:no_access")
        return view_func(request, *args, **kwargs)

    return wrapper


def require_trust_admin(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_trust_admin:
            raise PermissionDenied("Trust admin access required.")
        return view_func(request, *args, **kwargs)

    return wrapper


def require_role(*roles, write=False):
    """`is_trust_admin` satisfies every role check. AUDITOR is read-only regardless of
    the role list — pass write=True on any view that mutates data."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_trust_admin:
                return view_func(request, *args, **kwargs)
            if request.membership is None:
                return redirect("tenancy:no_access")
            if write and request.membership.role == "AUDITOR":
                raise PermissionDenied("Auditors have read-only access.")
            if request.membership.role not in roles:
                raise PermissionDenied("You do not have the required role for this action.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_tenant_object(model, request, pk):
    return get_object_or_404(model.objects.for_request(request), pk=pk)
