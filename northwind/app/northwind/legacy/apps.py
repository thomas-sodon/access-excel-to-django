"""The original Northwind tables as Django models (S4.models; no feature flag)."""

from django.apps import AppConfig


class LegacyConfig(AppConfig):
    name = "northwind.legacy"
    label = "legacy"
    verbose_name = "Northwind tables"
    default_auto_field = "django.db.models.AutoField"
