"""The Products and Inventory area (docs/contracts.md#feature-app-contract).

The overlay installs every app/northwind/*/apps.py package, mounts a feature app's
urls.py at /inventory/ and lists nav_label in the navigation. Copy this file in last:
until it exists, the area is not installed, so a half-built area cannot break the
other areas (README.md).
"""

from django.apps import AppConfig


class AreaConfig(AppConfig):
    name = "northwind.inventory"
    label = "inventory"
    verbose_name = "Products and Inventory"
    feature = True
    nav_label = "Products and Inventory"
