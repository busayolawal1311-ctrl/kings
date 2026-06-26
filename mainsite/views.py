from django.shortcuts import get_object_or_404, render
from .models import Category, Product


def index(request):
    new_arrivals = Product.objects.filter(is_active=True, is_new_arrival=True).select_related("category")[:4]
    top_selling = Product.objects.filter(is_active=True, is_top_selling=True).select_related("category")[:4]
    categories = Category.objects.filter(is_active=True)[:4]

    return render(request, 'mainsite/index.html', {
        "new_arrivals": new_arrivals,
        "top_selling": top_selling,
        "categories": categories,
    })


def categories(request, category_slug=None):
    active_categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).select_related("category")
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(active_categories, slug=category_slug)
        products = products.filter(category=selected_category)

    return render(request, 'mainsite/categories.html', {
        "categories": active_categories,
        "selected_category": selected_category,
        "products": products,
        "product_count": products.count(),
    })


def product(request, product_slug=None):
    products = Product.objects.filter(is_active=True).select_related("category")

    if product_slug:
        selected_product = get_object_or_404(products, slug=product_slug)
    else:
        selected_product = products.first()

    related_products = Product.objects.filter(is_active=True).exclude(
        pk=selected_product.pk if selected_product else None
    ).select_related("category")[:4]

    return render(request, 'mainsite/product.html', {
        "product": selected_product,
        "related_products": related_products,
    })

def checkout(request):
    return render(request, 'mainsite/checkout.html')
