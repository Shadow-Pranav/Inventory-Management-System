from django.urls import path

from . import views

app_name = "issuance"

urlpatterns = [
    path("issue-requests/", views.issue_request_list, name="issue_request_list"),
    path("issue-requests/new/", views.issue_request_create, name="issue_request_create"),
]
