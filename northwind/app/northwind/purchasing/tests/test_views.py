"""Every screen of the Purchasing and receiving area: an anonymous user is sent to the
sign-in page, a user without the role gets 403 and a user with the role gets 200 (a
PDF body starts with %PDF-).

SCREENS is the contract's parametrize table (docs/contracts.md#feature-app-contract):
it names every rules.json object of the area with type form or report and decision
keep (frmPurchaseOrderDetails, frmPurchaseOrderList, frmSelectVendorDialog,
sfrmCompanyDetail_VendorPurchaseOrders, sfrmPurchaseOrderLineItems; the area keeps
no reports). The tests after it drive the screens' actions through the views.
"""
# Expected values are worked out by hand in each test.
# ruff: noqa: PLR2004

from decimal import Decimal
from http import HTTPStatus
from typing import NamedTuple

import pytest
from django.conf import settings
from django.contrib.messages import get_messages
from django.shortcuts import resolve_url
from django.urls import reverse

from northwind.core.roles import role_names
from northwind.core.roles import role_permissions
from northwind.legacy.choices import PurchaseOrderStatusCode as Status
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ProductVendorFactory
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
def staff_client(client, user_with_role):
    client.force_login(user_with_role("staff"))
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
    assert PurchaseOrder.objects.get(pk=po.pk).status_id == Status.SUBMITTED


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
