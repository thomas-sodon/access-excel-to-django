"""Every screen of the Sales and Catalog Reports area: an anonymous user is sent to the
sign-in page, a user without the role gets 403 and a user with the role gets 200 (a
report's ?format=pdf body starts with %PDF-).

One parametrize table names every rules.json object of the area with type form or
report and decision keep (docs/contracts.md#feature-app-contract).
"""

from http import HTTPStatus
from typing import NamedTuple

import pytest
from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import reverse

from northwind.core.roles import role_names
from northwind.core.roles import role_permissions

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.reports import views

pytestmark = pytest.mark.django_db


class Screen(NamedTuple):
    source: str  # the original form or report
    url_name: str
    permission: str  # the permission the view checks
    query: str = ""


SALES = views.SALES_PERMISSION
CATALOG = views.CATALOG_PERMISSION

SCREENS = [
    Screen("frmReports", "form_frmReports", SALES),
    Screen("rptSalesByEmployee", "report_rptSalesByEmployee", SALES),
    Screen("rptSalesByEmployee", "report_rptSalesByEmployee", SALES, "?format=pdf"),
    Screen("rptSalesByProduct", "report_rptSalesByProduct", SALES),
    Screen("rptSalesByProduct", "report_rptSalesByProduct", SALES, "?format=pdf"),
    Screen("rptSalesByProductQuarterly", "report_rptSalesByProductQuarterly", SALES),
    Screen(
        "rptSalesByProductQuarterly",
        "report_rptSalesByProductQuarterly",
        SALES,
        "?format=pdf",
    ),
    Screen("rptProductCatalog", "report_rptProductCatalog", CATALOG),
    Screen("rptProductCatalog", "report_rptProductCatalog", CATALOG, "?format=pdf"),
    Screen(
        "srptCatalog_TableOfContents",
        "report_srptCatalog_TableOfContents",
        CATALOG,
    ),
    Screen(
        "srptCatalog_TableOfContents",
        "report_srptCatalog_TableOfContents",
        CATALOG,
        "?format=pdf",
    ),
    Screen("srptGastronomic", "report_srptGastronomic", CATALOG),
    Screen("srptGastronomic", "report_srptGastronomic", CATALOG, "?format=pdf"),
    Screen("srptOrderForm", "report_srptOrderForm", CATALOG),
    Screen("srptOrderForm", "report_srptOrderForm", CATALOG, "?format=pdf"),
    Screen("srptQuality", "report_srptQuality", CATALOG),
    Screen("srptQuality", "report_srptQuality", CATALOG, "?format=pdf"),
    Screen("srptShipVia", "report_srptShipVia", CATALOG),
    Screen("srptShipVia", "report_srptShipVia", CATALOG, "?format=pdf"),
]


def screen_id(screen: Screen) -> str:
    return f"{screen.source}{screen.query}"


def url_of(screen: Screen) -> str:
    return reverse(f"reports:{screen.url_name}") + screen.query


def role_granting(permission: str) -> str:
    """A role whose group holds the permission the screen checks."""
    return next(role for role in role_names() if permission in role_permissions(role))


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_anonymous_user_is_sent_to_sign_in(client, screen_data, screen):
    response = client.get(url_of(screen))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(resolve_url(settings.LOGIN_URL))


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_without_the_role_is_refused(client, user, screen_data, screen):
    client.force_login(user)
    response = client.get(url_of(screen))
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_with_the_role_gets_the_screen(
    client,
    user_with_role,
    screen_data,
    screen,
):
    client.force_login(user_with_role(role_granting(screen.permission)))
    response = client.get(url_of(screen))
    assert response.status_code == HTTPStatus.OK
    if "format=pdf" in screen.query:
        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")
    else:
        assert b"<html" in response.content


def test_htmx_report_choice_gets_only_the_selection(staff_client, screen_data):
    response = staff_client.get(
        reverse("reports:form_frmReports") + "?report=rptSalesByProduct",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == HTTPStatus.OK
    assert b'id="report-selection"' in response.content
    assert b"<html" not in response.content


def test_htmx_employee_filter_gets_only_the_report_body(staff_client, screen_data):
    seller = screen_data["seller"]
    response = staff_client.get(
        reverse("reports:report_rptSalesByEmployee") + f"?employee={seller.pk}",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == HTTPStatus.OK
    assert b'id="report-body"' in response.content
    assert b"<html" not in response.content


def test_unknown_report_choice_is_not_found(staff_client, screen_data):
    response = staff_client.get(reverse("reports:form_frmReports") + "?report=rptNone")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_dates_that_are_not_dates_go_back_to_the_selection(staff_client, screen_data):
    response = staff_client.get(
        reverse("reports:report_rptSalesByProduct") + "?start=someday",
    )
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("reports:form_frmReports"))
