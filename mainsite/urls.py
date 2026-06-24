from django.urls import path
from . import views

app_name = "mainsite"

urlpatterns = [
    path("", views.index, name="index"),
    path("category/", views.category, name="category"),
    path("product/", views.product, name="product"),
    path("checkout/", views.checkout, name="checkout"),
]
