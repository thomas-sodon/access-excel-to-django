"""The Purchasing and receiving area (docs/contracts.md#feature-app-contract).

The overlay installs every app/northwind/*/apps.py package, mounts a feature app's
urls.py at /purchasing/ and lists nav_label in the navigation. Copy this file in last:
until it exists, the area is not installed, so a half-built area cannot break the
other areas (README.md).
"""

from django.apps import AppConfig


class AreaConfig(AppConfig):
    name = "northwind.purchasing"
    label = "purchasing"
    verbose_name = "Purchasing and receiving"
    feature = True
    nav_label = "Purchasing and receiving"
