from django.db import models
from django.utils.text import slugify


def unique_slug_for(instance, source):
    slug = slugify(source) or "item"
    model = instance.__class__
    unique_slug = slug
    counter = 2

    while model.objects.filter(slug=unique_slug).exclude(pk=instance.pk).exists():
        unique_slug = f"{slug}-{counter}"
        counter += 1

    return unique_slug


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.CharField(max_length=400, null=True, blank=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug_for(self, self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    image = models.ImageField(upload_to='product_images/')
    description = models.CharField(max_length=400, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=4.5)
    review_count = models.PositiveIntegerField(default=0)
    badge = models.CharField(max_length=30, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    is_new_arrival = models.BooleanField(default=False)
    is_top_selling = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug_for(self, self.name)
        super().save(*args, **kwargs)
