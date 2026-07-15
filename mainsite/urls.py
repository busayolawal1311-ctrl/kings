"""Public URL contract for storefront and account workflows."""

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
    # AJAX endpoints intentionally use integer IDs and POST-only views to mutate cart state.
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("subscribe/", views.subscribe_newsletter, name="subscribe"),
    path("login/", views.sign_in, name="login"),
    path("signup/", views.signup, name="signup"),
    path("account/", views.account, name="account"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),

]
