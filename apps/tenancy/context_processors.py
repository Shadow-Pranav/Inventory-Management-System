from .models import Organization


def available_organizations(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    if user.is_trust_admin:
        orgs = Organization.objects.filter(is_active=True).order_by("name")
    else:
        orgs = (
            Organization.objects.filter(
                memberships__user=user, memberships__is_active=True, is_active=True
            )
            .distinct()
            .order_by("name")
        )
    return {"available_organizations": orgs}
