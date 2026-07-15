"""Template context values shared by every storefront page."""


def cart(request):
    """Expose a safe session-cart count without issuing an extra database query."""
    values = request.session.get("cart", {}).values()
    try:
        count = sum(max(0, int(value)) for value in values)
    except (TypeError, ValueError):
        count = 0
    return {"cart_count": count}
