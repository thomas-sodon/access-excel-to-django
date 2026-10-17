"""Every screen of the Purchasing and receiving area: an anonymous user is sent to the
sign-in page, a user without the role gets 403 and a user with the role gets 200 (a
PDF body starts with %PDF-).

SCREENS is the contract's parametrize table (docs/contracts.md#feature-app-contract):
it names every rules.json object of the area with type form or report and decision
keep (frmPurchaseOrderDetails, frmPurchaseOrderList, frmSelectVendorDialog,
sfrmCompanyDetail_VendorPurchaseOrders, sfrmPurchaseOrderLineItems; the area keeps
no reports). The tests after it drive the screens' actions through the views. Every
list keeps its record links unboosted (LISTS), so a purchase order opens as its own
page and not inside the list.
"""
# Expected values are worked out by hand in each test.
# ruff: noqa: PLR2004

from decimal import Decimal
from html.parser import HTMLParser
from http import HTTPStatus
from typing import NamedTuple

import pytest
from django.conf import settings
from django.contrib.messages import get_messages
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.html import escape

from northwind.core.roles import role_names
from northwind.core.roles import role_permissions
from northwind.legacy.choices import PurchaseOrderStatusCode as Status
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ProductVendorFactory
from northwind.legacy.factories import PurchaseOrderDetailFactory
from northwind.legacy.factories import VendorFactory
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.purchasing import views

pytestmark = pytest.mark.django_db


class Screen(NamedTuple):
    source: str  # the original form or report
    url_name: str
    permission: str  # the permission the view checks
    # The fixture object the URL takes: po, line, product or vendor.
    key: str | None = None
    query: str = ""


SCREENS = [
    Screen("frmPurchaseOrderList", "form_frmPurchaseOrderList", views.VIEW_PO),
    Screen(
        "frmPurchaseOrderDetails",
        "form_frmPurchaseOrderDetails",
        views.VIEW_PO,
        "po",
    ),
    Screen("frmPurchaseOrderDetails", "create", views.ADD_PO),
    Screen("frmPurchaseOrderDetails", "update", views.CHANGE_PO, "po"),
    Screen("frmPurchaseOrderDetails", "print", views.VIEW_PO, "po"),
    Screen("frmPurchaseOrderDetails", "print", views.VIEW_PO, "po", "?format=pdf"),
    Screen(
        "sfrmPurchaseOrderLineItems",
        "form_sfrmPurchaseOrderLineItems",
        views.VIEW_LINE,
        "po",
    ),
    Screen("sfrmPurchaseOrderLineItems", "line_add", views.ADD_LINE, "po"),
    Screen("sfrmPurchaseOrderLineItems", "line_defaults", views.ADD_LINE, "po"),
    Screen("sfrmPurchaseOrderLineItems", "line_update", views.CHANGE_LINE, "line"),
    Screen(
        "frmSelectVendorDialog",
        "form_frmSelectVendorDialog",
        views.ADD_PO,
        "product",
    ),
    Screen(
        "sfrmCompanyDetail_VendorPurchaseOrders",
        "form_sfrmCompanyDetail_VendorPurchaseOrders",
        views.VIEW_PO,
        "vendor",
    ),
]


def screen_id(screen: Screen) -> str:
    return f"{screen.source}-{screen.url_name}{screen.query}"


@pytest.fixture
def record(po_with_line, vendor, product):
    """A New purchase order with one line; its product has two vendors, so the
    vendor dialog shows a choice."""
    po, line = po_with_line
    ProductVendorFactory(product=product, vendor=VendorFactory())
    return {"po": po, "line": line, "product": product, "vendor": vendor}


def url_of(screen: Screen, record) -> str:
    kwargs = {"pk": record[screen.key].pk} if screen.key else {}
    return reverse(f"purchasing:{screen.url_name}", kwargs=kwargs) + screen.query


def role_granting(permission: str) -> str:
    """A role whose group holds the permission the screen checks."""
    return next(role for role in role_names() if permission in role_permissions(role))


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_anonymous_user_is_sent_to_sign_in(client, record, screen):
    response = client.get(url_of(screen, record))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(resolve_url(settings.LOGIN_URL))


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_without_the_role_is_refused(client, user, record, screen):
    client.force_login(user)
    response = client.get(url_of(screen, record))
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_with_the_role_gets_the_screen(client, user_with_role, record, screen):
    client.force_login(user_with_role(role_granting(screen.permission)))
    response = client.get(url_of(screen, record))
    assert response.status_code == HTTPStatus.OK
    if "format=pdf" in screen.query:
        assert response.content.startswith(b"%PDF-")


ACTIONS = ["submit", "approve", "receive", "close", "delete", "add_no_stock"]


@pytest.mark.parametrize("action", ACTIONS)
def test_actions_need_sign_in_and_role(client, user, record, action):
    url = reverse(f"purchasing:{action}", kwargs={"pk": record["po"].pk})
    response = client.post(url)
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(resolve_url(settings.LOGIN_URL))
    client.force_login(user)
    assert client.post(url).status_code == HTTPStatus.FORBIDDEN
    assert PurchaseOrder.objects.filter(pk=record["po"].pk).exists()


def messages_of(response) -> list[str]:
    return [str(message) for message in get_messages(response.wsgi_request)]


@pytest.fixture
def staff_client(client, user_with_role, employee_for):
    """A staff user whose sign-in e-mail is an employee's, so they can submit."""
    user = user_with_role("staff")
    employee_for(user)
    client.force_login(user)
    return client


def test_htmx_list_request_gets_only_the_table(staff_client, record):
    response = staff_client.get(
        reverse("purchasing:form_frmPurchaseOrderList"),
        headers={"HX-Request": "true"},
    )
    assert response.status_code == HTTPStatus.OK
    assert b'id="po-table"' in response.content
    assert b"<html" not in response.content
    assert b"Purchase orders: 1." in response.content


def test_list_search_filters_by_vendor_name(staff_client, record, make_po):
    make_po(Status.NEW, vendor=VendorFactory(company_name="Zeta Supplies"))
    url = reverse("purchasing:form_frmPurchaseOrderList")
    response = staff_client.get(url, {"search": "zeta"})
    assert response.context["po_count"] == 1
    response = staff_client.get(url)
    assert response.context["po_count"] == len(PurchaseOrder.objects.all())


def test_create_then_submit_through_the_screens(staff_client, statuses, vendor):
    response = staff_client.post(
        reverse("purchasing:create"),
        {"vendor": vendor.pk, "notes": "via screen"},
    )
    po = PurchaseOrder.objects.get()
    assert response.url == reverse(
        "purchasing:form_frmPurchaseOrderDetails",
        kwargs={"pk": po.pk},
    )
    assert po.status_id == Status.NEW
    staff_client.post(reverse("purchasing:submit", kwargs={"pk": po.pk}))
    po = PurchaseOrder.objects.select_related("submitted_by").get(pk=po.pk)
    assert po.status_id == Status.SUBMITTED
    assert (po.submitted_by.first_name, po.submitted_by.last_name) == ("Ann", "Buyer")
    response = staff_client.get(
        reverse("purchasing:form_frmPurchaseOrderDetails", kwargs={"pk": po.pk}),
    )
    assert b"Ann Buyer" in response.content


def test_submit_without_an_employee_record_is_refused_on_screen(
    client,
    user_with_role,
    record,
):
    """R-purchasing-004: a signed-in user whose e-mail is no employee's sees why
    Submit cannot record them, and the refusal names the rule; nothing changes."""
    client.force_login(user_with_role("staff"))
    po = record["po"]
    detail = reverse("purchasing:form_frmPurchaseOrderDetails", kwargs={"pk": po.pk})
    assert b'id="po-not-employee"' in client.get(detail).content
    response = client.post(reverse("purchasing:submit", kwargs={"pk": po.pk}))
    assert any("R-purchasing-004" in text for text in messages_of(response))
    po = PurchaseOrder.objects.get(pk=po.pk)
    assert (po.status_id, po.submitted_by_id, po.submitted_date) == (
        Status.NEW,
        None,
        None,
    )


def test_staff_cannot_approve(staff_client, record):
    po = record["po"]
    po.status_id = Status.SUBMITTED
    po.save()
    response = staff_client.post(reverse("purchasing:approve", kwargs={"pk": po.pk}))
    assert any("R-purchasing-005" in text for text in messages_of(response))
    assert PurchaseOrder.objects.get(pk=po.pk).status_id == Status.SUBMITTED


def test_receive_without_confirmation_changes_nothing(staff_client, record):
    po = record["po"]
    po.status_id = Status.APPROVED
    po.save()
    url = reverse("purchasing:receive", kwargs={"pk": po.pk})
    response = staff_client.post(url, {})
    assert any("R-purchasing-007" in text for text in messages_of(response))
    assert PurchaseOrder.objects.get(pk=po.pk).status_id == Status.APPROVED
    staff_client.post(url, {"confirm": "on"})
    assert PurchaseOrder.objects.get(pk=po.pk).status_id == Status.RECEIVED


def test_close_through_the_screen(staff_client, record, vendor_tax):
    po = record["po"]
    po.status_id = Status.RECEIVED
    po.save()
    staff_client.post(
        reverse("purchasing:close", kwargs={"pk": po.pk}),
        {"shipping_fee": "2.0000", "payment_method": "Cash"},
    )
    po = PurchaseOrder.objects.get(pk=po.pk)
    assert po.status_id == Status.CLOSED
    assert po.payment_amount == Decimal("28.2500")  # 25 + 5% of 25 + 2


def test_delete_through_the_screen(staff_client, record):
    po = record["po"]
    response = staff_client.post(reverse("purchasing:delete", kwargs={"pk": po.pk}))
    assert response.url == reverse("purchasing:form_frmPurchaseOrderList")
    assert not PurchaseOrder.objects.filter(pk=po.pk).exists()


def test_line_defaults_fill_quantity_and_cost(staff_client, record):
    po, product = record["po"], record["product"]
    response = staff_client.get(
        reverse("purchasing:line_defaults", kwargs={"pk": po.pk}),
        {"product": product.pk},
        headers={"HX-Request": "true"},
    )
    form = response.context["line_form"]
    # reorder quantity: target 20 - (stock 0 + on order 0) = 20; standard cost 2.5000
    assert form.initial["quantity"] == 20
    assert form.initial["unit_cost"] == Decimal("2.5000")


def test_htmx_line_add_returns_the_lines_partial(staff_client, record, vendor):
    po = record["po"]
    other = ProductFactory(minimum_reorder_quantity=1)
    ProductVendorFactory(product=other, vendor=vendor)
    response = staff_client.post(
        reverse("purchasing:line_add", kwargs={"pk": po.pk}),
        {"product": other.pk, "quantity": "30", "unit_cost": "1.5000"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == HTTPStatus.OK
    assert b'id="po-lines"' in response.content
    assert b"<html" not in response.content
    assert PurchaseOrderDetail.objects.filter(purchase_order=po).count() == 2


def test_line_add_refusal_is_shown(staff_client, record):
    po, product = record["po"], record["product"]
    response = staff_client.post(
        reverse("purchasing:line_add", kwargs={"pk": po.pk}),
        {"product": product.pk, "quantity": "2", "unit_cost": "1"},
        headers={"HX-Request": "true"},
    )
    assert b"R-purchasing-019" in response.content


def test_htmx_line_delete(staff_client, record):
    line = record["line"]
    response = staff_client.post(
        reverse("purchasing:line_delete", kwargs={"pk": line.pk}),
        headers={"HX-Request": "true"},
    )
    assert b'id="po-lines"' in response.content
    assert not PurchaseOrderDetail.objects.filter(pk=line.pk).exists()


def test_amounts_show_two_decimals_with_separators(staff_client, record):
    """Money on the purchase order, its lines and the list shows two decimals and
    thousands separators, as in the orders area; the stored values keep four."""
    po = record["po"]
    PurchaseOrderDetailFactory(
        purchase_order=po,
        product=ProductFactory(),
        quantity=1000,
        unit_cost=Decimal("1234.5678"),
    )
    detail = staff_client.get(
        reverse("purchasing:form_frmPurchaseOrderDetails", kwargs={"pk": po.pk}),
    ).content
    assert b"1,234.57" in detail  # the unit cost
    assert b"1,234,567.80" in detail  # 1000 x 1234.5678
    assert b"1,234,592.80" in detail  # subtotal: 25.00 + 1,234,567.80
    assert b"1234567.8000" not in detail
    printed = staff_client.get(reverse("purchasing:print", kwargs={"pk": po.pk}))
    assert b"1,234,592.80" in printed.content
    listed = staff_client.get(reverse("purchasing:form_frmPurchaseOrderList"))
    assert b"1,234,592.80" in listed.content
    assert b"1234592.8000" not in listed.content


def test_a_message_shows_once_on_the_purchase_order_page(
    staff_client,
    record,
    vendor,
):
    """base.html shows the messages on a full page, so the line items partial
    inside the page does not repeat them; an HTMX swap of the partial shows its
    own (here the R-purchasing-019 warning of a line saved below the target
    level)."""
    po = record["po"]
    response = staff_client.post(
        reverse("purchasing:submit", kwargs={"pk": po.pk}),
        follow=True,
    )
    texts = [str(message) for message in response.context["messages"]]
    assert texts
    for text in texts:
        assert response.content.count(escape(text).encode()) == 1, text
    po.status_id = Status.NEW
    po.save()
    other = ProductFactory(minimum_reorder_quantity=10, target_level=20)
    ProductVendorFactory(product=other, vendor=vendor)
    response = staff_client.post(
        reverse("purchasing:line_add", kwargs={"pk": po.pk}),
        {"product": other.pk, "quantity": "10", "unit_cost": "1"},
        headers={"HX-Request": "true"},
    )
    # minimum 10 is met; 0 in stock + 10 stays 10 below the target level of 20
    assert PurchaseOrderDetail.objects.filter(product=other).exists()
    assert b"<html" not in response.content
    assert b"alert-warning" in response.content
    assert b"R-purchasing-019" in response.content


def test_vendor_dialog(staff_client, record):
    product = record["product"]
    url = reverse("purchasing:form_frmSelectVendorDialog", kwargs={"pk": product.pk})
    response = staff_client.post(url, {"next": "/purchasing/"})
    assert response.status_code == HTTPStatus.OK
    assert b"select a vendor" in response.content.lower()
    response = staff_client.post(url, {"next": "/purchasing/", "cancel": "1"})
    assert response.url == "/purchasing/"
    vendor = record["vendor"]
    response = staff_client.post(url, {"next": "/purchasing/", "vendor": vendor.pk})
    assert response.url == f"/purchasing/?product={product.pk}&vendor={vendor.pk}"
    assert PurchaseOrder.objects.count() == 1


def test_vendor_dialog_skipped_for_one_vendor(staff_client, statuses, vendor):
    product = ProductFactory()
    ProductVendorFactory(product=product, vendor=vendor)
    response = staff_client.get(
        reverse("purchasing:form_frmSelectVendorDialog", kwargs={"pk": product.pk}),
        {"next": "/elsewhere/"},
    )
    assert response.url == f"/elsewhere/?product={product.pk}&vendor={vendor.pk}"


def test_vendor_tab_lists_only_submitted(staff_client, record, make_po, vendor):
    make_po(Status.SUBMITTED, vendor=vendor, submitted_by=None)
    from northwind.legacy.factories import EmployeeFactory  # noqa: PLC0415

    shown = make_po(Status.SUBMITTED, vendor=vendor, submitted_by=EmployeeFactory())
    response = staff_client.get(
        reverse(
            "purchasing:form_sfrmCompanyDetail_VendorPurchaseOrders",
            kwargs={"pk": vendor.pk},
        ),
    )
    assert response.context["po_count"] == 1
    assert [row.record.pk for row in response.context["table"].rows] == [shown.pk]


# --------------------------------------------------------------- HTMX boost

#: Every list and list panel of the area that links to purchase orders, with the url
#: name of the page its record links open.
LISTS = [
    (SCREENS[0], "form_frmPurchaseOrderDetails"),
    (SCREENS[-1], "form_frmPurchaseOrderDetails"),
]

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
    ("screen", "opens"),
    LISTS,
    ids=[screen_id(screen) for screen, _ in LISTS],
)
def test_record_links_of_a_list_are_not_boosted(staff_client, record, screen, opens):
    """A purchase order link opens its page normally; the sort links swap only the
    table."""
    from northwind.legacy.factories import EmployeeFactory  # noqa: PLC0415

    po = record["po"]
    po.submitted_by = EmployeeFactory()  # the vendor tab lists submitted ones only
    po.save()
    boosts = link_boosts(staff_client.get(url_of(screen, record)).content)
    record_url = reverse(f"purchasing:{opens}", kwargs={"pk": po.pk})
    assert record_url in boosts, "the list shows no link to the purchase order"
    assert "true" not in boosts[record_url]
    sort_links = [href for href in boosts if "sort=" in href]
    assert sort_links, "the list table has no sort link"
    assert all(boosts[href] == {"true"} for href in sort_links)


class ChoiceContainers(HTMLParser):
    """For each radio of the vendor dialog: the classes of its enclosing elements,
    and the label ids that sit in the same .form-check container."""

    def __init__(self) -> None:
        super().__init__()
        self.open: list[tuple[str, str]] = []
        self.radios: dict[str, int] = {}  # radio id -> depth of its .form-check
        self.labels: dict[str, int] = {}  # label for -> depth of its .form-check

    def container_depth(self) -> int:
        for depth in range(len(self.open) - 1, -1, -1):
            if "form-check" in self.open[depth][1].split():
                return depth
        return -1

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("type") == "radio":
            self.radios[attributes.get("id") or ""] = self.container_depth()
        if tag == "label" and attributes.get("for"):
            self.labels[attributes["for"]] = self.container_depth()
        if tag not in VOID_ELEMENTS:
            self.open.append((tag, attributes.get("class") or ""))

    def handle_endtag(self, tag):
        for depth in range(len(self.open) - 1, -1, -1):
            if self.open[depth][0] == tag:
                del self.open[depth:]
                return


def test_vendor_dialog_double_click_reaches_the_label(staff_client, record):
    """R-purchasing-023: a double-click on a vendor confirms it. The handler sits on
    each choice's .form-check container, which holds both the radio and the label
    beside it (crispy-bootstrap5 renders the label next to the input, not around it),
    so a double-click on the vendor's name reaches it."""
    url = reverse(
        "purchasing:form_frmSelectVendorDialog",
        kwargs={"pk": record["product"].pk},
    )
    content = staff_client.get(url, {"next": "/purchasing/"}).content
    parser = ChoiceContainers()
    parser.feed(content.decode())
    parser.close()
    assert len(parser.radios) == 2  # the product's two vendors
    for radio_id, depth in parser.radios.items():
        assert radio_id, "each vendor radio has an id"
        assert depth >= 0, "each vendor radio sits in a .form-check container"
        assert parser.labels.get(radio_id) == depth, "its label is in that container"
    assert b'radio.closest(".form-check")' in content
    assert b'addEventListener("dblclick"' in content
