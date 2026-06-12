from django.urls import path
from . import views

urlpatterns = [
    path ("", views.index),
    path ("category/", views.Category),
    path ("product/", views.Product),
    path ("checkout/", views.checkout),
]