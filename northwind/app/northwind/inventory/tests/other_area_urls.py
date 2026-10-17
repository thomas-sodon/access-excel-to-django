"""The project's URLs plus stand-ins for the other areas' screens this area links to.

Acceptance runs this area alone (MP_ONLY_AREAS=inventory), so the orders and
purchasing screens are not installed and the links to them are left out
(links.other_area_url). Tests that check those links use this URLconf: a namespace
that is installed keeps its real URLs, and a missing one gets a stand-in that only
answers 200, so the link renders with the same URL name and arguments.
"""

from django.http import HttpResponse
from django.urls import get_resolver
from django.urls import include
from django.urls import path

from config import urls as project_urls

#: The project's URLconf (config/settings ROOT_URLCONF). Named here rather than read
#: from settings, because a test that uses this module sets ROOT_URLCONF to it.
PROJECT_URLCONF = "config.urls"


def stand_in(request, pk):
    return HttpResponse(f"stand-in {pk}")


STAND_INS = {
    "orders": [
        path("<int:pk>/", stand_in, name="form_frmOrderDetails"),
    ],
    "purchasing": [
        path("<int:pk>/", stand_in, name="form_frmPurchaseOrderDetails"),
        path(
            "select-vendor/<int:pk>/",
            stand_in,
            name="form_frmSelectVendorDialog",
        ),
    ],
}

installed = get_resolver(PROJECT_URLCONF).namespace_dict

urlpatterns = [*project_urls.urlpatterns]
urlpatterns += [
    path(f"stand-in/{namespace}/", include((patterns, namespace)))
    for namespace, patterns in STAND_INS.items()
    if namespace not in installed
]
