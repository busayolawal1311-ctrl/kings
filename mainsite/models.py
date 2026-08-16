"""Normalized database models for catalog, customer, order, and inventory data.

Models retain relationships and validation close to the database boundary so all
entry points—admin, templates, services, and a future API—share the same rules.
"""

from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Q
from django.utils import timezone
from django.utils.text import slugify


def unique_slug_for(instance, source):
    """Generate a stable, collision-free slug for models that expose public URLs."""
    base = slugify(source) or "item"
    slug, counter, model = base, 2, instance.__class__
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


class TimeStampedModel(models.Model):
    """Reusable audit fields for records whose creation and modification matter."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Profile(TimeStampedModel):
    """Account state separate from Django's user table, including RBAC and lockout."""
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        STAFF = "staff", "Staff / admin"
        SUPER_ADMIN = "super_admin", "Super admin"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER, db_index=True)
    email_verified = models.BooleanField(default=False)
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    @property
    def is_locked(self):
        """Return whether a temporary brute-force protection window is still active."""
        return bool(self.locked_until and self.locked_until > timezone.now())

    def __str__(self):
        return self.user.get_username()


class Brand(TimeStampedModel):
    """A merchandisable brand that may be associated with many products."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="brand_logos/", blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        """Populate a public URL slug only when an editor has not supplied one."""
        if not self.slug:
            self.slug = unique_slug_for(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    """A browseable catalog grouping; product deletion is not cascaded from it."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    image = models.ImageField(upload_to="category_images/", blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug_for(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    """The parent catalog record; sellable stock lives on its variants."""
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to="product_images/")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])
    badge = models.CharField(max_length=30, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name="products", null=True, blank=True)
    is_new_arrival = models.BooleanField(default=False, db_index=True)
    is_top_selling = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "name")
        indexes = [models.Index(fields=("is_active", "category", "-created_at")), models.Index(fields=("is_active", "price"))]
        constraints = [models.CheckConstraint(condition=Q(price__gte=0), name="product_price_non_negative"), models.CheckConstraint(check=Q(old_price__isnull=True) | Q(old_price__gte=0), name="product_old_price_non_negative")]

    def clean(self):
        """Reject misleading sale pricing before an editor can save it."""
        if self.old_price is not None and self.old_price < self.price:
            raise ValidationError({"old_price": "Original price must be greater than or equal to the selling price."})

    def save(self, *args, **kwargs):
        """Assign a discoverable slug for new products while preserving edited slugs."""
        if not self.slug:
            self.slug = unique_slug_for(self, self.name)
        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        """Aggregate only moderated reviews so unapproved content never affects trust."""
        return round(self.reviews.filter(approved=True).aggregate(value=Avg("rating"))["value"] or 0, 1)

    @property
    def total_reviews(self):
        """Return the number of public reviews for storefront presentation."""
        return self.reviews.filter(approved=True).count()

    @property
    def available_stock(self):
        """Sum variant stock instead of duplicating inventory on the product record."""
        return self.variants.aggregate(total=models.Sum("stock_quantity"))["total"] or 0

    def __str__(self):
        return self.name


class ProductImage(TimeStampedModel):
    """Additional product imagery ordered for galleries and API consumers."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.ImageField(upload_to="product_images/gallery/")
    alt_text = models.CharField(max_length=160, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position", "pk")


class ProductVariant(TimeStampedModel):
    """The sellable SKU with option values, optional price override, and stock."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    size = models.CharField(max_length=32, blank=True)
    color = models.CharField(max_length=48, blank=True)
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("product", "size", "color"), name="unique_product_variant_option")]
        indexes = [models.Index(fields=("product", "is_active")), models.Index(fields=("stock_quantity",))]

    @property
    def price(self):
        """Use variant pricing only when merchandising explicitly overrides the parent."""
        return self.price_override if self.price_override is not None else self.product.price

    @property
    def is_low_stock(self):
        """Expose a simple stock alert predicate for admin/reporting surfaces."""
        return self.stock_quantity <= self.low_stock_threshold

    def __str__(self):
        return f"{self.product} · {self.size or 'One size'} {self.color}".strip()


class InventoryMovement(TimeStampedModel):
    """Append-only inventory audit trail for sales, returns, and manual corrections."""
    class Reason(models.TextChoices):
        SALE = "sale", "Sale"
        RETURN = "return", "Return"
        ADJUSTMENT = "adjustment", "Manual adjustment"
        RESTOCK = "restock", "Restock"

    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="inventory_movements")
    quantity_delta = models.IntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("variant", "-created_at"))]


class Address(TimeStampedModel):
    """A customer-owned address, retained separately from immutable order snapshots."""
    class Kind(models.TextChoices):
        SHIPPING = "shipping", "Shipping"
        BILLING = "billing", "Billing"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=50, default="Home")
    recipient_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=32)
    line_1 = models.CharField(max_length=160)
    line_2 = models.CharField(max_length=160, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=24, blank=True)
    country = models.CharField(max_length=2, default="NG")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.SHIPPING)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_default", "-updated_at")
        indexes = [models.Index(fields=("user", "kind", "is_default"))]


class Cart(TimeStampedModel):
    """Persistent cart owned by either an authenticated user or anonymous session."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="cart")
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    coupon = models.ForeignKey("Coupon", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(user__isnull=False) | ~Q(session_key=""), name="cart_has_owner")]


class CartItem(TimeStampedModel):
    """One quantity per cart/variant pair; the unique constraint prevents duplicates."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(99)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=("cart", "variant"), name="unique_cart_variant")]

    @property
    def line_total(self):
        """Calculate from server-side variant pricing; never trust a client total."""
        return self.variant.price * self.quantity


class Wishlist(TimeStampedModel):
    """A saved product relationship unique to a customer."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "product"), name="unique_wishlist_product")]


class Coupon(TimeStampedModel):
    """A time-bounded promotion with a server-enforced usage limit."""
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed amount"

    code = models.CharField(max_length=32, unique=True)
    discount_type = models.CharField(max_length=12, choices=DiscountType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    minimum_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    def clean(self):
        """Validate discount semantics that database types alone cannot express."""
        if self.discount_type == self.DiscountType.PERCENTAGE and self.amount > 100:
            raise ValidationError({"amount": "Percentage discounts cannot exceed 100."})
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "End date must be after start date."})

    def is_valid_for(self, subtotal, now=None):
        """Evaluate all promotion eligibility checks in one reusable place."""
        now = now or timezone.now()
        return self.is_active and subtotal >= self.minimum_order_amount and (not self.starts_at or self.starts_at <= now) and (not self.ends_at or self.ends_at >= now) and (self.usage_limit is None or self.usage_count < self.usage_limit)

    def discount_for(self, subtotal):
        """Return a capped discount so fixed codes can never make an order negative."""
        return min(subtotal, subtotal * self.amount / 100 if self.discount_type == self.DiscountType.PERCENTAGE else self.amount)

    def __str__(self):
        return self.code


class Order(TimeStampedModel):
    """Immutable commercial record created from a cart before payment completion."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")
    email = models.EmailField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    shipping_address = models.JSONField(default=dict)
    billing_address = models.JSONField(default=dict)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "-created_at")), models.Index(fields=("status", "-created_at"))]

    def save(self, *args, **kwargs):
        """Generate an opaque human-supportable order number once, at creation time."""
        if not self.number:
            self.number = f"KNG-{timezone.now():%Y%m%d}-{uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number


class OrderItem(TimeStampedModel):
    """Historical snapshot of a purchased variant, independent of later catalog edits."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=150)
    variant_sku = models.CharField(max_length=64)
    variant_description = models.CharField(max_length=120, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        indexes = [models.Index(fields=("order",))]

    @property
    def line_total(self):
        """Compute the historical line price from the snapshot values."""
        return self.unit_price * self.quantity


class Payment(TimeStampedModel):
    """Provider-agnostic payment attempt and callback payload storage."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=40)
    provider_reference = models.CharField(max_length=128, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    provider_payload = models.JSONField(default=dict, blank=True)


class Review(TimeStampedModel):
    """Customer product feedback, held for moderation before public display."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews")
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    rating = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=120, blank=True)
    comment = models.TextField()
    approved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=("product", "user"), condition=Q(user__isnull=False), name="one_review_per_customer_product")]

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class NewsletterSubscriber(models.Model):
    """Consent-based email subscription identified by a unique address."""
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
