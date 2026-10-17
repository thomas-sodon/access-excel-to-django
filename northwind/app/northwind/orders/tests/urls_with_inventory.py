"""The project's URLs, plus a stand-in for the inventory area's product screen while
that area is not loaded (MP_ONLY_AREAS=orders), so the order lines' product links
(R-orders-029) can be tested. With every area loaded these are the project's URLs.
"""

from django.apps import apps
from django.http import HttpResponse
from django.urls import include
from django.urls import path

from config.urls import urlpatterns as project_urlpatterns


def product_detail_stand_in(request, pk):
    return HttpResponse()


urlpatterns = list(project_urlpatterns)
if not apps.is_installed("northwind.inventory"):
    urlpatterns.append(
        path(
            "inventory/",
            include(
                (
                    [
                        path(
                            "products/<int:pk>/",
                            product_detail_stand_in,
                            name="form_frmProductDetail",
                        ),
                    ],
                    "inventory",
                ),
            ),
        ),
    )
