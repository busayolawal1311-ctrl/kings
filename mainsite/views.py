"""Template-facing storefront, cart, and account views.

All input is server-validated and state-changing endpoints require POST, preserving
Django's CSRF protections. Checkout business rules remain in ``services.py`` so a
future API can reuse the same authoritative behavior.
"""

from datetime import timedelta
from decimal import Decimal
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import LoginForm, NewsletterForm, ReviewForm, SignUpForm
from .models import Category, Product
from django.contrib import messages


def index(request):
    """Render a fast home page with bounded, relation-optimised merchandising rows."""
    new_arrivals = Product.objects.filter(is_active=True, is_new_arrival=True).select_related("category")[:4]
    top_selling = Product.objects.filter(is_active=True, is_top_selling=True).select_related("category")[:4]
    categories = Category.objects.filter(is_active=True)[:4]

    return render(request, 'mainsite/index.html', {
        "new_arrivals": new_arrivals,
        "top_selling": top_selling,
        "categories": categories,
    })


def categories(request, category_slug=None):
    """Render a filterable catalog while whitelisting supported sort expressions."""
    active_categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).select_related("category")
    selected_category = None

    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "newest")
    if category_slug:
        selected_category = get_object_or_404(active_categories, slug=category_slug)
        products = products.filter(category=selected_category)

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    products = products.order_by({"price_asc": "price", "price_desc": "-price", "name": "name", "newest": "-created_at"}.get(sort, "-created_at"))

    return render(request, 'mainsite/categories.html', {
        "categories": active_categories,
        "selected_category": selected_category,
        "products": products,
        "product_count": products.count(),
        "query": query,
        "sort": sort,
    })


def product(request, product_slug=None):
    """Render a product and accept a moderated customer review submission."""
    products = Product.objects.filter(
        is_active=True
    ).select_related("category")

    if product_slug:
        selected_product = get_object_or_404(
            products,
            slug=product_slug
        )
    else:
        selected_product = products.first()

    if not selected_product:
        return render(request, "mainsite/product.html", {"product": None})

    reviews = selected_product.reviews.filter(
        approved=True
    )

    if request.method == "POST":
        review_form = ReviewForm(request.POST)

        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = selected_product
            if request.user.is_authenticated:
                if selected_product.reviews.filter(user=request.user).exists():
                    review_form.add_error(None, "You have already reviewed this product.")
                    return render(request, "mainsite/product.html", {"product": selected_product, "related_products": [], "reviews": reviews, "review_form": review_form})
                review.user = request.user
                review.name = request.user.get_full_name() or request.user.username
                review.email = request.user.email
            review.save()

            return redirect(
                "mainsite:product_detail",
                product_slug=selected_product.slug
            )
    else:
        review_form = ReviewForm()

    related_products = Product.objects.filter(is_active=True, category=selected_product.category).exclude(pk=selected_product.pk).select_related("category")[:4]
    if not related_products:
        related_products = products.exclude(pk=selected_product.pk)[:4]

    return render(request, "mainsite/product.html", {
        "product": selected_product,
        "related_products": related_products,
        "reviews": reviews,
        "review_form": review_form,
    })

def checkout(request):
    """Render the transitional session cart and calculate totals on the server."""
    cart = request.session.get("cart", {})
    products = Product.objects.filter(pk__in=[int(pk) for pk in cart if pk.isdigit()], is_active=True).select_related("category")
    product_map = {str(item.pk): item for item in products}
    items, subtotal = [], Decimal("0")
    for product_id, quantity in cart.items():
        product = product_map.get(product_id)
        if product:
            quantity = max(1, int(quantity))
            line_total = product.price * quantity
            items.append({"product": product, "quantity": quantity, "line_total": line_total})
            subtotal += line_total
    shipping = Decimal("0") if subtotal >= Decimal("50000") or not subtotal else Decimal("2500")
    return render(request, "mainsite/checkout.html", {"cart_items": items, "subtotal": subtotal, "shipping": shipping, "total": subtotal + shipping})


def cart_add(request, product_id):
    """Add a valid active product to the session cart and return its item count.

    This compatibility endpoint keeps the existing template cart operational while
    the persistent ``Cart``/``CartItem`` checkout service is available to new flows.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "POST required."}, status=405)
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except (TypeError, ValueError):
        quantity = 1
    cart = request.session.get("cart", {})
    key = str(product.pk)
    cart[key] = min(int(cart.get(key, 0)) + quantity, 99)
    request.session["cart"] = cart
    request.session.modified = True
    return JsonResponse({"message": f"{product.name} added to your bag.", "count": sum(cart.values())})


def cart_update(request, product_id):
    """Set a session-cart quantity; zero removes the line rather than storing it."""
    if request.method != "POST":
        return JsonResponse({"detail": "POST required."}, status=405)
    cart = request.session.get("cart", {})
    try:
        quantity = int(request.POST.get("quantity", 0))
    except (TypeError, ValueError):
        quantity = 0
    key = str(product_id)
    if quantity > 0:
        cart[key] = min(quantity, 99)
    else:
        cart.pop(key, None)
    request.session["cart"] = cart
    request.session.modified = True
    return JsonResponse({"message": "Your bag has been updated.", "count": sum(cart.values())})


def subscribe_newsletter(request):
    """Validate and persist newsletter consent, then safely return to the referrer."""
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            # Add a success message
            messages.success(request, "Thanks for subscribing!")
        else:
            messages.error(request, "Invalid email or you are already subscribed.")

    # Redirect back to the page the user was just on, or home if unknown
    return redirect(request.META.get('HTTP_REFERER', 'mainsite:index'))

def signup(request):
    """Create a customer account, trigger verification, and begin an authenticated session."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            _send_verification_email(request, user)
            login(request, user)
            messages.success(request, "Your account is ready. Check your email to verify it.")
            return redirect('mainsite:index')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def sign_in(request):
    """Authenticate a user with optional persistent session and lockout protection."""
    if request.user.is_authenticated:
        return redirect('mainsite:index')
    form = LoginForm(request, data=request.POST or None)
    username = request.POST.get("username", "")
    candidate = User.objects.filter(username__iexact=username).select_related("profile").first()
    profile = candidate and candidate.profile if candidate and hasattr(candidate, "profile") else None
    if candidate and profile is None:
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=candidate)
    if candidate and profile.is_locked:
        form.add_error(None, "This account is temporarily locked. Try again later or reset your password.")
    elif request.method == "POST" and form.is_valid():
        user = form.get_user()
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.failed_login_count = 0
        profile.locked_until = None
        profile.save(update_fields=["failed_login_count", "locked_until", "updated_at"])
        login(request, user)
        request.session.set_expiry(60 * 60 * 24 * 30 if form.cleaned_data["remember_me"] else 0)
        return redirect(request.POST.get("next") or request.GET.get("next") or "mainsite:index")
    elif request.method == "POST" and candidate:
        profile = profile
        profile.failed_login_count += 1
        if profile.failed_login_count >= 5:
            profile.locked_until = timezone.now() + timedelta(minutes=15)
            profile.failed_login_count = 0
        profile.save(update_fields=["failed_login_count", "locked_until", "updated_at"])
    return render(request, "registration/login.html", {"form": form})


def _send_verification_email(request, user):
    """Send a one-time Django token rather than exposing a predictable verification ID."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    url = request.build_absolute_uri(reverse("mainsite:verify_email", args=[uid, token]))
    send_mail("Verify your KINGS.CO email", f"Verify your account: {url}", None, [user.email], fail_silently=False)


def verify_email(request, uidb64, token):
    """Validate an opaque email token and mark only the matching profile verified."""
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user and default_token_generator.check_token(user, token):
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified", "updated_at"])
        messages.success(request, "Your email address has been verified.")
    else:
        messages.error(request, "That verification link is invalid or has expired.")
    return redirect("mainsite:index")


@login_required
def account(request):
    """Show only the authenticated customer's own order and address records."""
    return render(request, "registration/account.html", {"orders": request.user.orders.prefetch_related("items")[:10], "addresses": request.user.addresses.all()})
