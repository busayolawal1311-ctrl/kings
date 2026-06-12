from django.shortcuts import render

# Create your views here.

def index(request):
    return render(request, 'mainsite/index.html')

def Category(request):
    return render(request, 'mainsite/category.html')

def Product(request):
    return render(request, 'mainsite/product.html')

def checkout(request):
    return render(request, 'mainsite/checkout.html')