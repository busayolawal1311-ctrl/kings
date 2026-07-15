"""Signals that provision least-privilege account state after user creation."""

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def provision_customer_profile(sender, instance, created, **kwargs):
    """Create profile/group records and mirror Django staff/superuser capabilities."""
    profile, _ = Profile.objects.get_or_create(user=instance)
    if created and not instance.is_staff and not instance.is_superuser:
        group, _ = Group.objects.get_or_create(name="Customer")
        instance.groups.add(group)
    if instance.is_superuser:
        profile.role = Profile.Role.SUPER_ADMIN
        profile.save(update_fields=["role", "updated_at"])
    elif instance.is_staff and profile.role == Profile.Role.CUSTOMER:
        profile.role = Profile.Role.STAFF
        profile.save(update_fields=["role", "updated_at"])
