"""Operational Django admin configuration for catalog and order management.

The admin is intentionally optimised with filters, searches, relation loading and
inlines so staff can manage a growing catalogue without custom back-office tooling.
"""

from django.contrib import admin

from .models import (Address, Brand, Cart, CartItem, Category, Coupon, InventoryMovement, Order, OrderItem, Payment, Product, ProductImage, ProductVariant, Profile, Review, Wishlist, NewsletterSubscriber)

admin.site.site_header = "KINGS.CO operations"
admin.site.site_title = "KINGS.CO admin"
admin.site.index_title = "Store operations"

class ProductImageInline(admin.TabularInline):
    """Edit gallery images in the same workflow as the parent product."""
    model = ProductImage
    extra = 0


class VariantInline(admin.TabularInline):
    """Expose stock-bearing SKUs alongside product merchandising fields."""
    model = ProductVariant
    extra = 0
    fields = ("sku", "size", "color", "price_override", "stock_quantity", "low_stock_threshold", "is_active")


class OrderItemInline(admin.TabularInline):
    """Show immutable purchase snapshots without allowing staff to alter history."""
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_sku", "variant_description", "unit_price", "quantity")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category browse and search controls for merchandising users."""
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Brand management with active-state filtering."""
    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """High-volume catalog editor with gallery and variant inlines."""
    list_display = ("name", "sku", "category", "brand", "price", "available_stock", "is_active")
    list_filter = ("is_active", "category", "brand", "is_new_arrival", "is_top_selling", "is_featured")
    search_fields = ("name", "sku", "description")
    list_select_related = ("category", "brand")
    list_per_page = 50
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProductImageInline, VariantInline)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order operations UI; financial values are readonly after checkout."""
    list_display = ("number", "email", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("number", "email", "user__username")
    list_select_related = ("user", "coupon")
    readonly_fields = ("number", "subtotal", "discount_total", "shipping_total", "tax_total", "total", "created_at", "updated_at")
    inlines = (OrderItemInline,)
    list_per_page = 50

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Promotion management with redemption visibility."""
    list_display = ("code", "discount_type", "amount", "usage_count", "usage_limit", "is_active", "ends_at")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Review moderation queue with a bulk approval action."""
    list_display = ("product", "name", "rating", "approved", "created_at")
    list_filter = ("approved", "rating", "created_at")
    search_fields = ("product__name", "name", "comment")
    list_select_related = ("product", "user")
    actions = ("approve_reviews",)
    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        """Publish selected reviews in one query for efficient moderation."""
        queryset.update(approved=True)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Customer role, verification, and security-state visibility for support staff."""
    list_display = ("user", "role", "email_verified", "locked_until")
    list_filter = ("role", "email_verified")
    search_fields = ("user__username", "user__email")
    list_select_related = ("user",)

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    """Read-only-friendly inventory audit list for reconciliation work."""
    list_display = ("variant", "quantity_delta", "reason", "reference", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("variant__sku", "reference")
    readonly_fields = ("created_at", "updated_at")

admin.site.register((Address, Cart, CartItem, Wishlist, Payment, NewsletterSubscriber))
