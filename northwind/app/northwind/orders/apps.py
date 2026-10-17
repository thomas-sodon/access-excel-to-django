"""The Orders, Invoicing and Shipping area (docs/contracts.md#feature-app-contract).

The overlay installs every app/northwind/*/apps.py package, mounts a feature app's
urls.py at /orders/ and lists nav_label in the navigation. Copy this file in last:
until it exists, the area is not installed, so a half-built area cannot break the
other areas (README.md).
"""

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "northwind.orders"
    label = "orders"
    verbose_name = "Orders, Invoicing and Shipping"
    feature = True
    nav_label = "Orders, Invoicing and Shipping"
