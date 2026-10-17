"""Every screen of the Orders, Invoicing and Shipping area: an anonymous user is sent
to the sign-in page, a user without the role gets 403 and a user with the role gets
200 (a PDF body starts with %PDF-). Every list keeps its record links unboosted, so a
record opens as its own page and not inside the list.

SCREENS is the contract's parametrize table (docs/contracts.md#feature-app-contract):
it names every rules.json object of the area with type form or report and decision
keep, each with the URLs that serve it. frmLogin, frmCredentials and
sfrmEmployee_Privileges are kept as foundation sign-in and roles; their URLs here are
the landing page after sign-in, the user's employee record and the privilege grants.
"""

from __future__ import annotations

from decimal import Decimal
from html.parser import HTMLParser
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
from northwind.legacy.models import OrderDetail

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


def test_adding_a_line_by_htmx_updates_the_amounts(client, user_with_role, records):
    """R-orders-022: the HTMX add-line swap also sends the order's amounts out of
    band, so Subtotal and Total follow the lines: 2 x 4.00 already on the order plus
    3 x 10.00 added = 38.00; with tax rate 0 and a 5.00 fee the total is 43.00."""
    for code in OrderStatusCode:
        OrderStatusFactory(order_status_id=code)
    for code in OrderDetailStatusCode:
        OrderDetailStatusFactory(order_detail_status_id=code)
    order = Order.objects.get(pk=records["order"]["pk"])
    order.order_status_id = OrderStatusCode.NEW
    order.shipping_fee = Decimal("5.0000")
    order.save()
    product = ProductFactory(unit_price=Decimal("10.0000"))
    client.force_login(user_with_role(role_granting("orderdetail", "add")))
    detail = client.get(reverse("orders:form_frmOrderDetails", kwargs=records["order"]))
    assert b'id="order-amounts"' in detail.content
    assert b"hx-swap-oob" not in detail.content
    url = reverse("orders:form_sfrmOrderLineItems", kwargs=records["order"])
    response = client.post(
        url,
        {"product": product.pk, "quantity": 3, "discount": 0},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == HTTPStatus.OK
    lines, _, amounts = response.content.partition(b'id="order-amounts"')
    assert b'id="order-lines"' in lines
    assert b'hx-swap-oob="true"' in amounts
    assert b"38.00" in amounts
    assert b"43.00" in amounts


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


#: Every list and list panel of the area that links to records: the screen, the url
#: name of the page its record links open, which record that page takes, and whether
#: the list is a sortable table inside a boosted #record-table container.
class Listing(NamedTuple):
    screen: Screen
    opens: str  # the kind of record its links open (RECORD_PAGES)
    sortable: bool


LIST_ROWS = [
    (Screen("frmOrderList", "form_frmOrderList", "order", "view"), "order", True),
    (
        Screen("frmCompanyList", "form_frmCompanyList", "company", "view"),
        "company",
        True,
    ),
    (
        Screen("frmEmployeeList", "form_frmEmployeeList", "employee", "view"),
        "employee",
        True,
    ),
    (
        Screen(
            "sfrmCompanyDetail_CustomerOrders",
            "form_sfrmCompanyDetail_CustomerOrders",
            "order",
            "view",
            "company",
        ),
        "order",
        False,
    ),
    (
        Screen(
            "frmCompanyDetail",
            "form_frmCompanyDetail",
            "company",
            "view",
            "company",
        ),
        "order",
        False,
    ),
    (
        Screen(
            "sfrmOrders_MostRecent_ByEmployee",
            "form_sfrmOrders_MostRecent_ByEmployee",
            "order",
            "view",
            "employee",
        ),
        "order",
        False,
    ),
    (
        Screen("frmEmployeeList", "employee_detail", "employee", "view", "employee"),
        "order",
        False,
    ),
]
LISTS = [Listing(*row) for row in LIST_ROWS]

#: The page a record link opens, for each kind of record a list links to.
RECORD_PAGES = {
    "order": "orders:form_frmOrderDetails",
    "company": "orders:form_frmCompanyDetail",
    "employee": "orders:employee_detail",
}

VOID_ELEMENTS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta"}
    | {"source", "track", "wbr"},
)


class LinkBoosts(HTMLParser):
    """The hx-boost value in force on each link: its own, else the nearest ancestor's.

    htmx inherits hx-boost, so a link inside a boosted container loads with HTMX into
    the container's hx-target unless a closer element says hx-boost="false".
    """

    def __init__(self) -> None:
        super().__init__()
        self.open: list[tuple[str, str | None]] = []
        self.boosts: dict[str, set[str | None]] = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        inherited = self.open[-1][1] if self.open else None
        boost = attributes.get("hx-boost", inherited)
        if tag == "a" and attributes.get("href"):
            self.boosts.setdefault(attributes["href"], set()).add(boost)
        if tag not in VOID_ELEMENTS:
            self.open.append((tag, boost))

    def handle_endtag(self, tag):
        for depth in range(len(self.open) - 1, -1, -1):
            if self.open[depth][0] == tag:
                del self.open[depth:]
                return


def link_boosts(content: bytes) -> dict[str, set[str | None]]:
    """Each link's href, with the hx-boost values in force where it appears."""
    parser = LinkBoosts()
    parser.feed(content.decode())
    parser.close()
    return parser.boosts


@pytest.mark.parametrize(
    "listing",
    LISTS,
    ids=[screen_id(listing.screen) for listing in LISTS],
)
def test_record_links_of_a_list_are_not_boosted(
    client,
    user_with_role,
    records,
    listing,
):
    """A record link opens its page normally (R-orders-029); a sortable list's sort
    links stay boosted and swap only the table."""
    screen, opens, sortable = listing
    client.force_login(user_with_role(role_granting(screen.model, screen.action)))
    response = client.get(url_of(screen, records))
    assert response.status_code == HTTPStatus.OK
    boosts = link_boosts(response.content)
    record_url = reverse(RECORD_PAGES[opens], kwargs={"pk": records[opens]["pk"]})
    assert record_url in boosts, "the list shows no link to the record"
    assert "true" not in boosts[record_url]
    sort_links = [href for href in boosts if "sort=" in href]
    if sortable:
        assert sort_links, "the list table has no sort link"
        assert all(boosts[href] == {"true"} for href in sort_links)


@pytest.mark.urls("northwind.orders.tests.urls_with_inventory")
def test_a_line_product_links_to_its_product_screen(client, user_with_role, records):
    """An order line's product opens the inventory area's product screen as a page of
    its own (R-orders-029)."""
    client.force_login(user_with_role(role_granting("order", "view")))
    response = client.get(
        url_of(Screen("", "form_frmOrderDetails", "", "", "order"), records),
    )
    assert response.status_code == HTTPStatus.OK
    line = OrderDetail.objects.get(order_id=records["order"]["pk"])
    product_url = reverse(
        "inventory:form_frmProductDetail",
        kwargs={"pk": line.product_id},
    )
    boosts = link_boosts(response.content)
    assert product_url in boosts, "the order line shows no link to its product"
    assert "true" not in boosts[product_url]
