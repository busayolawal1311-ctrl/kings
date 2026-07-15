"""Application configuration and startup hooks for the commerce domain."""

from django.apps import AppConfig


class MainsiteConfig(AppConfig):
    name = 'mainsite'

    def ready(self):
        """Register signal receivers after Django's app registry is fully populated."""
        from . import signals  # noqa: F401
