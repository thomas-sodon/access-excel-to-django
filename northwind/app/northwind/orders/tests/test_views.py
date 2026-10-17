"""Every screen of the Orders, Invoicing and Shipping area: an anonymous user is sent
to the sign-in page, a user without the role gets 403 and a user with the role gets
200 (a PDF body starts with %PDF-).

SCREENS is the contract's parametrize table (docs/contracts.md#feature-app-contract):
it names every rules.json object of the area with type form or report and decision
keep, each with the URLs that serve it. frmLogin, frmCredentials and
sfrmEmployee_Privileges are kept as foundation sign-in and roles; their URLs here are
the landing page after sign-in, the user's employee record and the privilege grants.
"""

from __future__ import annotations

from decimal import Decimal
from http import HTTPStatus
from typing import NamedTuple

import pytest
from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import reverse

from northwind.core.roles import role_names
from northwind.core.roles import role_permissions
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.factories import ContactFactory
from northwind.legacy.factories import OrderDetailFactory
from northwind.legacy.factories import OrderDetailStatusFactory
from northwind.legacy.factories import OrderStatusFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ShipperFactory
from northwind.legacy.factories import StockTakeFactory
from northwind.legacy.models import Order

pytestmark = pytest.mark.django_db


class Screen(NamedTuple):
    source: str  # the original form or report (rules.json objects[].name)
    url_name: str
    model: str  # the legacy model whose permission the view checks
    action: str  # view, add, change or delete
    key: str | None = None  # which record the URL takes: order, line, company, ...
    query: str = ""


SCREENS = [
    Screen("frmOrderList", "form_frmOrderList", "order", "view"),
    Screen("frmLogin", "form_frmLogin", "order", "view"),
    Screen("frmOrderDetails", "form_frmOrderDetails", "order", "view", "order"),
    Screen("frmOrderDetails", "order_create", "order", "add"),
    Screen("frmOrderDetails", "order_update", "order", "change", "order"),
    Screen("frmOrderDetails", "order_delete", "order", "delete", "order"),
    Screen(
        "sfrmOrderLineItems",
        "form_sfrmOrderLineItems",
        "orderdetail",
        "view",
        "order",
    ),
    Screen("sfrmOrderLineItems", "order_line_update", "orderdetail", "change", "line"),
    Screen("sfrmOrderLineItems", "order_line_delete", "orderdetail", "delete", "line"),
    Screen("rptInvoice", "report_rptInvoice", "order", "view", "order"),
    Screen("rptInvoice", "report_rptInvoice", "order", "view", "order", "?format=pdf"),
    Screen("frmCompanyList", "form_frmCompanyList", "company", "view"),
    Screen("frmCompanyDetail", "form_frmCompanyDetail", "company", "view", "company"),
    Screen("frmCompanyDetail", "company_create", "company", "add"),
    Screen("frmCompanyDetail", "company_update", "company", "change", "company"),
    Screen("frmCompanyDetail", "company_delete", "company", "delete", "company"),
    Screen(
        "sfrmCompanyDetail_Contacts",
        "form_sfrmCompanyDetail_Contacts",
        "contact",
        "view",
        "company",
    ),
    Screen(
        "sfrmCompanyDetail_Contacts",
        "contact_update",
        "contact",
        "change",
        "contact",
    ),
    Screen(
        "sfrmCompanyDetail_Contacts",
        "contact_delete",
        "contact",
        "delete",
        "contact",
    ),
    Screen(
        "sfrmCompanyDetail_CustomerOrders",
        "form_sfrmCompanyDetail_CustomerOrders",
        "order",
        "view",
        "company",
    ),
    Screen(
        "sfrmCompanyDetail_ShipperOrders",
        "form_sfrmCompanyDetail_ShipperOrders",
        "order",
        "view",
        "company",
    ),
    Screen("frmEmployeeList", "form_frmEmployeeList", "employee", "view"),
    Screen("frmEmployeeList", "employee_detail", "employee", "view", "employee"),
    Screen("frmEmployeeList", "employee_create", "employee", "add"),
    Screen("frmEmployeeList", "employee_update", "employee", "change", "employee"),
    Screen("frmEmployeeList", "employee_delete", "employee", "delete", "employee"),
    Screen(
        "sfrmOrders_MostRecent_ByEmployee",
        "form_sfrmOrders_MostRecent_ByEmployee",
        "order",
        "view",
        "employee",
    ),
    Screen(
        "sfrmEmployee_Privileges",
        "form_sfrmEmployee_Privileges",
        "employeeprivilege",
        "view",
        "employee",
    ),
    Screen("frmEmployeeTitles", "form_frmEmployeeTitles", "title", "add"),
    Screen("frmCredentials", "form_frmCredentials", "employee", "view"),
]


def screen_id(screen: Screen) -> str:
    return f"{screen.source}-{screen.url_name}{screen.query}"


@pytest.fixture
def records():
    """An order of a customer with one allocated line, the customer's contact and
    the order's salesperson."""
    line = OrderDetailFactory(
        quantity=2,
        unit_price=Decimal("4.0000"),
        order_detail_status__order_detail_status_id=OrderDetailStatusCode.ALLOCATED,
    )
    StockTakeFactory(product=line.product, quantity_on_hand=10, expected_quantity=10)
    order = line.order
    return {
        "order": {"pk": order.pk},
        "line": {"pk": order.pk, "line": line.pk},
        "company": {"pk": order.customer_id},
        "contact": {"pk": ContactFactory(company=order.customer).pk},
        "employee": {"pk": order.employee_id},
    }


def url_of(screen: Screen, records) -> str:
    kwargs = records[screen.key] if screen.key else {}
    return reverse(f"orders:{screen.url_name}", kwargs=kwargs) + screen.query


def role_granting(model: str, action: str) -> str:
    """A role whose group holds the permission the screen checks."""
    permission = f"legacy.{action}_{model}"
    return next(role for role in role_names() if permission in role_permissions(role))


def test_the_table_names_every_kept_form_and_report():
    """Each kept form and report of the area has a row (contract check)."""
    kept = {
        "frmCompanyDetail",
        "frmCompanyList",
        "frmCredentials",
        "frmEmployeeList",
        "frmEmployeeTitles",
        "frmLogin",
        "frmOrderDetails",
        "frmOrderList",
        "sfrmCompanyDetail_Contacts",
        "sfrmCompanyDetail_CustomerOrders",
        "sfrmCompanyDetail_ShipperOrders",
        "sfrmEmployee_Privileges",
        "sfrmOrderLineItems",
        "sfrmOrders_MostRecent_ByEmployee",
        "rptInvoice",
    }
    assert {screen.source for screen in SCREENS} == kept


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_anonymous_user_is_sent_to_sign_in(client, records, screen):
    response = client.get(url_of(screen, records))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(resolve_url(settings.LOGIN_URL))


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_without_the_role_is_refused(client, user, records, screen):
    client.force_login(user)
    response = client.get(url_of(screen, records))
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_with_the_role_gets_the_screen(client, user_with_role, records, screen):
    client.force_login(user_with_role(role_granting(screen.model, screen.action)))
    response = client.get(url_of(screen, records))
    assert response.status_code == HTTPStatus.OK
    if "format=pdf" in screen.query:
        assert response.content.startswith(b"%PDF-")


def test_htmx_list_request_gets_only_the_table(client, user_with_role, records):
    client.force_login(user_with_role(role_granting("order", "view")))
    response = client.get(
        reverse("orders:form_frmOrderList"),
        headers={"HX-Request": "true"},
    )
    assert response.status_code == HTTPStatus.OK
    assert b'id="record-table"' in response.content
    assert b"<html" not in response.content


def test_htmx_line_request_gets_only_the_lines(client, user_with_role, records):
    client.force_login(user_with_role(role_granting("orderdetail", "view")))
    url = reverse("orders:form_sfrmOrderLineItems", kwargs=records["order"])
    response = client.get(url, headers={"HX-Request": "true"})
    assert response.status_code == HTTPStatus.OK
    assert b'id="order-lines"' in response.content
    assert b"<html" not in response.content


def test_category_narrows_the_line_products(client, user_with_role, records):
    """Choosing a category re-renders the line form with that category's products
    only (R-orders-008, an HTMX swap)."""
    client.force_login(user_with_role(role_granting("orderdetail", "view")))
    listed = ProductFactory(product_name="Listed Tea")
    other = ProductFactory(product_name="Other Jam")
    url = reverse("orders:form_sfrmOrderLineItems", kwargs=records["order"])
    query = f"?category={listed.product_category_id}&quantity=4"
    response = client.get(url + query, headers={"HX-Request": "true"})
    assert response.status_code == HTTPStatus.OK
    option = f'<option value="{listed.pk}">Listed Tea</option>'
    assert option.encode() in response.content
    assert other.product_name.encode() not in response.content
    assert b'name="quantity" value="4"' in response.content


def test_order_workflow_through_the_screens(client, user_with_role, records):
    """The order screen's actions walk an order from New to Closed (the services'
    rules are in test_rules.py)."""
    for code in OrderStatusCode:
        OrderStatusFactory(order_status_id=code)
    for code in OrderDetailStatusCode:
        OrderDetailStatusFactory(order_detail_status_id=code)
    client.force_login(user_with_role(role_granting("order", "change")))
    order = Order.objects.get(pk=records["order"]["pk"])
    order.shipping_fee = Decimal(0)
    order.save()
    steps = [
        ("invoice", {}),
        ("ship", {"shipped_date": "2024-02-01T10:00", "shipper": ShipperFactory().pk}),
        ("pay", {"payment_method": "Cash", "paid_date": "2024-02-02T10:00"}),
        ("close", {"confirmed": "yes"}),
    ]
    for verb, data in steps:
        url = reverse("orders:order_action", kwargs={"pk": order.pk, "verb": verb})
        assert client.post(url, data).status_code == HTTPStatus.FOUND
    order.refresh_from_db()
    assert order.order_status_id == OrderStatusCode.CLOSED
