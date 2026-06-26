from django.urls import path
from . import views

app_name = "mainsite"

urlpatterns = [
    path("", views.index, name="index"),
    path("categories/", views.categories, name="categories"),
    path("categories/<slug:category_slug>/", views.categories, name="category_detail"),
    path("product/", views.product, name="product"),
    path("product/<slug:product_slug>/", views.product, name="product_detail"),
    path("checkout/", views.checkout, name="checkout"),
]
