from django.urls import path

from . import views

app_name = "tenancy"

urlpatterns = [
    path("no-access/", views.no_access, name="no_access"),
    path("organizations/switch/", views.switch_organization, name="switch_organization"),
    path("members/", views.member_list, name="member_list"),
    path("members/invite/", views.member_invite, name="member_invite"),
    path("members/<int:pk>/edit/", views.member_update, name="member_update"),
    path("departments/", views.department_list, name="department_list"),
    path("departments/new/", views.department_create, name="department_create"),
    path("departments/<int:pk>/edit/", views.department_update, name="department_update"),
    path("audit-log/", views.audit_log_list, name="audit_log_list"),
]
