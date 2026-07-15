"""Commerce business rules that are shared by HTML views and future API endpoints.

Keeping pricing and checkout outside views prevents separate presentation layers from
implementing inconsistent totals or unsafe inventory updates.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from .models import Cart, Coupon, InventoryMovement, Order, OrderItem, ProductVariant

# Values are centralised so a future settings-backed shipping policy has one seam.
FREE_SHIPPING_THRESHOLD = Decimal("50000")
STANDARD_SHIPPING = Decimal("2500")


@dataclass(frozen=True)
class Totals:
    """An immutable monetary breakdown used when a cart becomes an order."""

    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    tax: Decimal

    @property
    def total(self):
        """Return the payable total without allowing downstream mutation."""
        return self.subtotal - self.discount + self.shipping + self.tax


def calculate_totals(cart: Cart, coupon: Coupon | None = None, tax_rate=Decimal("0")) -> Totals:
    """Calculate server-authoritative totals for a persisted cart.

    Product prices are always read from the variant at calculation time; client-side
    prices are deliberately never accepted. Invalid or expired promotions are ignored
    here and rejected explicitly at checkout to avoid accidental discount application.
    """
    items = cart.items.select_related("variant__product")
    subtotal = sum((item.line_total for item in items), Decimal("0"))
    coupon = coupon or cart.coupon
    discount = coupon.discount_for(subtotal) if coupon and coupon.is_valid_for(subtotal) else Decimal("0")
    shipping = Decimal("0") if subtotal >= FREE_SHIPPING_THRESHOLD or not subtotal else STANDARD_SHIPPING
    tax = (subtotal - discount) * tax_rate
    return Totals(subtotal=subtotal, discount=discount, shipping=shipping, tax=tax)


@transaction.atomic
def create_order_from_cart(*, cart: Cart, email: str, shipping_address: dict, billing_address: dict, user=None, tax_rate=Decimal("0")) -> Order:
    """Create an order and deduct stock atomically.

    Row locks prevent two concurrent checkout requests from overselling the same
    variant. Order items snapshot names, SKUs and prices so historic orders remain
    correct if catalog data changes. Any validation error rolls back all writes.
    """
    items = list(cart.items.select_related("variant__product"))
    if not items:
        raise ValidationError("Cannot checkout an empty cart.")

    totals = calculate_totals(cart, tax_rate=tax_rate)
    if cart.coupon and not cart.coupon.is_valid_for(totals.subtotal):
        raise ValidationError("The coupon is no longer valid.")

    order = Order.objects.create(
        user=user,
        email=email,
        coupon=cart.coupon,
        subtotal=totals.subtotal,
        discount_total=totals.discount,
        shipping_total=totals.shipping,
        tax_total=totals.tax,
        total=totals.total,
        shipping_address=shipping_address,
        billing_address=billing_address,
    )

    for item in items:
        # Re-read under a lock because the cart's earlier stock value may be stale.
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
        if not variant.is_active or variant.stock_quantity < item.quantity:
            raise ValidationError(f"{variant.product.name} no longer has enough stock.")

        ProductVariant.objects.filter(pk=variant.pk).update(stock_quantity=F("stock_quantity") - item.quantity)
        InventoryMovement.objects.create(
            variant=variant,
            quantity_delta=-item.quantity,
            reason=InventoryMovement.Reason.SALE,
            reference=order.number,
            created_by=user,
        )
        OrderItem.objects.create(
            order=order,
            product_name=variant.product.name,
            variant_sku=variant.sku,
            variant_description=" / ".join(value for value in (variant.size, variant.color) if value),
            unit_price=variant.price,
            quantity=item.quantity,
        )

    if cart.coupon:
        Coupon.objects.filter(pk=cart.coupon_id).update(usage_count=F("usage_count") + 1)

    # A completed checkout must not be replayed from the same persisted cart.
    cart.items.all().delete()
    cart.coupon = None
    cart.save(update_fields=["coupon", "updated_at"])
    return order
