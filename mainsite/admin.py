from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_new_arrival", "is_top_selling", "is_active")
    list_filter = ("category", "is_new_arrival", "is_top_selling", "is_featured", "is_active")
    list_editable = ("price", "is_new_arrival", "is_top_selling", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
