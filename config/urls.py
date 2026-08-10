from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.tenancy.views import ForcedPasswordChangeView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Ahead of the include below: same URL and name ("password_change") as its stock entry,
    # so this one wins on dispatch (first match) without the self-service reset flow that
    # follows needing to know anything changed. See ForcedPasswordChangeView's docstring.
    path(
        "accounts/password_change/",
        ForcedPasswordChangeView.as_view(),
        name="password_change",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.tenancy.urls")),
    path("", include("apps.core.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("issuance/", include("apps.issuance.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
