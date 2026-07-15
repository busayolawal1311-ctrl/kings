"""Regression tests for public storefront rendering and critical commerce invariants."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from decimal import Decimal

from django.contrib.auth.models import User

from .models import Cart, CartItem, Category, Product, ProductVariant
from .services import create_order_from_cart


class StorefrontTests(TestCase):
    """Exercise routes and server-authoritative cart/order behavior."""
    def setUp(self):
        """Create the smallest valid catalog fixture shared by each isolated test."""
        category = Category.objects.create(name="Menswear")
        self.product = Product.objects.create(
            name="Essential Tee", category=category, price="12000.00",
            image=SimpleUploadedFile("tee.gif", b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;", content_type="image/gif"),
        )

    def test_core_pages_render(self):
        """Public routes should render successfully with a valid catalog record."""
        for url in (reverse("mainsite:index"), reverse("mainsite:categories"), reverse("mainsite:product_detail", args=[self.product.slug]), reverse("mainsite:checkout")):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_cart_can_add_and_update_product(self):
        """Session cart endpoints return server-confirmed item counts."""
        add_url = reverse("mainsite:cart_add", args=[self.product.pk])
        response = self.client.post(add_url, {"quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)
        response = self.client.post(reverse("mainsite:cart_update", args=[self.product.pk]), {"quantity": 1})
        self.assertEqual(response.json()["count"], 1)

    def test_checkout_service_creates_an_immutable_order_and_deducts_stock(self):
        """Checkout must atomically snapshot the sale, reduce stock, and clear the cart."""
        variant = ProductVariant.objects.create(product=self.product, sku="TEE-BLK-S", size="S", stock_quantity=3)
        user = User.objects.create_user("buyer", email="buyer@example.com", password="safe-password-123")
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, variant=variant, quantity=2)
        order = create_order_from_cart(cart=cart, user=user, email=user.email, shipping_address={"city": "Lagos"}, billing_address={"city": "Lagos"})
        variant.refresh_from_db()
        self.assertEqual(order.total, Decimal("26500"))
        self.assertEqual(variant.stock_quantity, 1)
        self.assertEqual(order.items.count(), 1)
        self.assertFalse(cart.items.exists())

# Create your tests here.
