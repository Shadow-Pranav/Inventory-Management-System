from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("stock/", views.stock_level_list, name="stock_level_list"),
    path("stock/adjust/", views.stock_adjustment_create, name="stock_adjustment_create"),
]
