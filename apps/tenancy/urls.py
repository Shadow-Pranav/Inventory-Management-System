from django.urls import path

from . import views

app_name = "tenancy"

urlpatterns = [
    path("no-access/", views.no_access, name="no_access"),
    path("organizations/switch/", views.switch_organization, name="switch_organization"),
]
