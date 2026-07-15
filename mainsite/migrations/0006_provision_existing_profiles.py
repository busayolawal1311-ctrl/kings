from django.db import migrations


def provision_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("mainsite", "Profile")
    Group = apps.get_model("auth", "Group")
    customer_group, _ = Group.objects.get_or_create(name="Customer")
    for user in User.objects.all().iterator():
        role = "super_admin" if user.is_superuser else "staff" if user.is_staff else "customer"
        Profile.objects.get_or_create(user_id=user.pk, defaults={"role": role})
        if not user.is_staff and not user.is_superuser:
            user.groups.add(customer_group)


class Migration(migrations.Migration):
    dependencies = [("mainsite", "0005_address_brand_cart_cartitem_coupon_inventorymovement_and_more")]
    operations = [migrations.RunPython(provision_profiles, migrations.RunPython.noop)]
