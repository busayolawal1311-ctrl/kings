from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Category = apps.get_model("mainsite", "Category")
    Product = apps.get_model("mainsite", "Product")

    for model in (Category, Product):
        used_slugs = set()
        for item in model.objects.all().order_by("id"):
            base_slug = slugify(item.name) or f"{model.__name__.lower()}-{item.pk}"
            slug = base_slug
            counter = 2
            while slug in used_slugs or model.objects.filter(slug=slug).exclude(pk=item.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            item.slug = slug
            item.save(update_fields=["slug"])
            used_slugs.add(slug)


class Migration(migrations.Migration):

    dependencies = [
        ("mainsite", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="category",
            old_name="isActive",
            new_name="is_active",
        ),
        migrations.RenameField(
            model_name="product",
            old_name="ProductImage",
            new_name="image",
        ),
        migrations.RenameField(
            model_name="product",
            old_name="isActive",
            new_name="is_active",
        ),
        migrations.AddField(
            model_name="category",
            name="slug",
            field=models.SlugField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="category",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="category_images/"),
        ),
        migrations.AddField(
            model_name="product",
            name="slug",
            field=models.SlugField(blank=True, max_length=140, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="old_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="rating",
            field=models.DecimalField(decimal_places=1, default=4.5, max_digits=2),
        ),
        migrations.AddField(
            model_name="product",
            name="review_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="product",
            name="badge",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="is_new_arrival",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="product",
            name="is_top_selling",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="product",
            name="is_featured",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="product",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(blank=True, max_length=120, unique=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=models.SlugField(blank=True, max_length=140, unique=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterModelOptions(
            name="category",
            options={"ordering": ["name"], "verbose_name_plural": "Categories"},
        ),
        migrations.AlterModelOptions(
            name="product",
            options={"ordering": ["-created_at", "name"]},
        ),
    ]
