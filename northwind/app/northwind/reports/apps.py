"""The Sales and Catalog Reports area (docs/contracts.md#feature-app-contract).

The overlay installs every app/northwind/*/apps.py package, mounts a feature app's
urls.py at /reports/ and lists nav_label in the navigation. Copy this file in last:
until it exists, the area is not installed, so a half-built area cannot break the
other areas (README.md).
"""

from django.apps import AppConfig


class AreaConfig(AppConfig):
    name = "northwind.reports"
    label = "reports"
    verbose_name = "Sales and Catalog Reports"
    feature = True
    nav_label = "Sales and Catalog Reports"
