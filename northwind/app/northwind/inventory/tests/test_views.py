"""Every screen of the Products and Inventory area: an anonymous user is sent to the
sign-in page, a user without the role gets 403 and a user with the role gets 200.

SCREENS is the contract's parametrize table (docs/contracts.md#feature-app-contract):
it names every rules.json object of the area with type form or report and decision
keep (the area keeps no report, so there is no PDF row), plus the other routes of
the area. The tests after it walk the screens' writes through the services.
"""

from decimal import Decimal
from http import HTTPStatus
from io import BytesIO
from typing import NamedTuple

import pytest
from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import reverse
from openpyxl import load_workbook

from northwind.core.roles import role_names
from northwind.core.roles import role_permissions
from northwind.legacy import factories as f
from northwind.legacy.models import Product
from northwind.legacy.models import ProductCategory
from northwind.legacy.models import ProductVendor
from northwind.legacy.models import PurchaseOrderDetail
from northwind.legacy.models import StockTake

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.inventory.reports.product_list_export import HEADINGS

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("fixed_codes")]


class Screen(NamedTuple):
    source: str  # the original form, or the action of the area's screens
    url_name: str
    permission: str  # the permission the view checks
    needs: str = ""  # "product", "category" or "link": what the URL takes
    query: str = ""


SCREENS = [
    Screen("frmProductList", "form_frmProductList", "legacy.view_product"),
    Screen(
        "frmProductList",
        "form_frmProductList",
        "legacy.view_product",
        query="?search=Product&discontinued=false",
    ),
    Screen("frmProductList-export", "product_export", "legacy.view_product"),
    Screen(
        "frmProductDetail",
        "form_frmProductDetail",
        "legacy.view_product",
        "product",
    ),
    Screen("frmProductDetail-new", "product_create", "legacy.add_product"),
    Screen(
        "frmProductDetail-edit",
        "product_update",
        "legacy.change_product",
        "product",
    ),
    Screen(
        "frmProductDetail-delete",
        "product_delete",
        "legacy.delete_product",
        "product",
    ),
    Screen(
        "frmProductDetail-reorder",
        "product_reorder",
        "legacy.add_purchaseorderdetail",
        "product",
    ),
    Screen(
        "sfrmProductDetail_Orders",
        "form_sfrmProductDetail_Orders",
        "legacy.view_orderdetail",
        "product",
    ),
    Screen(
        "sfrmProductDetail_PurchaseOrders",
        "form_sfrmProductDetail_PurchaseOrders",
        "legacy.view_purchaseorderdetail",
        "product",
    ),
    Screen(
        "sfrmProductDetail_StockTake",
        "form_sfrmProductDetail_StockTake",
        "legacy.view_stocktake",
        "product",
    ),
    Screen(
        "sfrmProductDetail_Vendors",
        "form_sfrmProductDetail_Vendors",
        "legacy.view_productvendor",
        "product",
    ),
    Screen(
        "sfrmProductDetail_Vendors-remove",
        "product_vendor_remove",
        "legacy.delete_productvendor",
        "link",
    ),
    Screen(
        "sfrmProductCategories",
        "form_sfrmProductCategories",
        "legacy.view_productcategory",
    ),
    Screen(
        "sfrmProductCategories-new",
        "category_create",
        "legacy.add_productcategory",
    ),
    Screen(
        "sfrmProductCategories-edit",
        "category_update",
        "legacy.change_productcategory",
        "category",
    ),
    Screen(
        "sfrmProductCategories-delete",
        "category_delete",
        "legacy.delete_productcategory",
        "category",
    ),
]


def screen_id(screen: Screen) -> str:
    return f"{screen.source}-{screen.url_name}{screen.query}"


@pytest.fixture
def link():
    """A product with a stock take, an order line, a purchase-order line and a
    vendor link."""
    product = f.ProductFactory()
    f.StockTakeFactory(product=product)
    f.OrderDetailFactory(product=product)
    f.PurchaseOrderDetailFactory(product=product)
    return f.ProductVendorFactory(product=product)


def url_of(screen: Screen, link: ProductVendor) -> str:
    kwargs = {
        "product": {"pk": link.product_id},
        "category": {"pk": link.product.product_category_id},
        "link": {"pk": link.product_id, "link": link.pk},
    }.get(screen.needs, {})
    return reverse(f"inventory:{screen.url_name}", kwargs=kwargs) + screen.query


def role_granting(permission: str) -> str:
    """A role whose group holds the permission the screen checks."""
    return next(role for role in role_names() if permission in role_permissions(role))


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_anonymous_user_is_sent_to_sign_in(client, link, screen):
    response = client.get(url_of(screen, link))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(resolve_url(settings.LOGIN_URL))


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_without_the_role_is_refused(client, user, link, screen):
    client.force_login(user)
    response = client.get(url_of(screen, link))
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize("screen", SCREENS, ids=screen_id)
def test_user_with_the_role_gets_the_screen(client, user_with_role, link, screen):
    client.force_login(user_with_role(role_granting(screen.permission)))
    response = client.get(url_of(screen, link))
    assert response.status_code == HTTPStatus.OK


@pytest.fixture
def staff_client(client, user_with_role):
    client.force_login(user_with_role("staff"))
    return client


def test_htmx_list_request_gets_only_the_table(staff_client, link):
    response = staff_client.get(
        reverse("inventory:form_frmProductList"),
        headers={"HX-Request": "true"},
    )
    assert response.status_code == HTTPStatus.OK
    assert b'id="product-table"' in response.content
    assert b"<html" not in response.content


def test_htmx_panel_request_gets_only_the_panel(staff_client, link):
    url = reverse("inventory:form_sfrmProductDetail_StockTake", args=[link.product_id])
    response = staff_client.get(url, headers={"HX-Request": "true"})
    assert b'id="panel-stock-takes"' in response.content
    assert b"<html" not in response.content


def test_product_list_shows_the_calculated_quantities(staff_client):
    """R-inventory-023: the list carries the stock figures of each product."""
    product = f.ProductFactory(product_name="Listed product")
    f.StockTakeFactory(product=product, quantity_on_hand=7)
    response = staff_client.get(reverse("inventory:form_frmProductList"))
    table = response.context["table"]
    row = next(row for row in table.rows if row.record.pk == product.pk)
    assert row.record.product_to_sell == 7  # noqa: PLR2004
    assert row.record.product_on_order == 0


def test_export_is_an_xlsx_of_the_product_list_by_name(staff_client):
    """R-inventory-024: the .xlsx download lists the products sorted by name with the
    export's columns."""
    later = f.ProductFactory(product_name="Zeta product")
    earlier = f.ProductFactory(product_name="Alpha product")
    response = staff_client.get(reverse("inventory:product_export"))
    assert response["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml",
    )
    sheet = load_workbook(BytesIO(response.content)).active
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0] == HEADINGS
    assert [row[0] for row in rows[1:]] == [earlier.pk, later.pk]


def test_create_product_through_the_form(staff_client):
    """R-inventory-013: the new product gets its built code and an opening stock
    take (R-inventory-002)."""
    category = f.ProductCategoryFactory(product_category_code="WEB")
    response = staff_client.post(
        reverse("inventory:product_create"),
        {
            "product_name": "Web product",
            "product_category": category.pk,
            "standard_unit_cost": "1.50",
            "unit_price": "3.00",
            "reorder_level": "0",
        },
    )
    product = Product.objects.get(product_name="Web product")
    assert response.status_code == HTTPStatus.FOUND
    assert product.product_code == f"NWTWEB-{product.pk}"
    assert StockTake.objects.filter(product=product, quantity_on_hand=0).exists()


def test_refused_product_save_shows_the_rule(staff_client):
    """R-inventory-012: a zero standard unit cost is refused with the rule id."""
    category = f.ProductCategoryFactory()
    response = staff_client.post(
        reverse("inventory:product_create"),
        {
            "product_name": "Free product",
            "product_category": category.pk,
            "standard_unit_cost": "0",
            "unit_price": "3.00",
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert b"R-inventory-012" in response.content
    assert not Product.objects.filter(product_name="Free product").exists()


def test_stock_take_confirmation_flow(staff_client, link):
    """R-inventory-010: a differing count is shown with both figures and saved only
    after confirmation."""
    url = reverse("inventory:form_sfrmProductDetail_StockTake", args=[link.product_id])
    count = StockTake.objects.count()
    response = staff_client.post(url, {"quantity_on_hand": "3"})
    assert response.status_code == HTTPStatus.OK
    assert b'id="stock-take-mismatch"' in response.content
    assert StockTake.objects.count() == count
    response = staff_client.post(
        url,
        {"quantity_on_hand": "3", "confirmed_quantity": "3"},
    )
    assert response.status_code == HTTPStatus.FOUND
    assert StockTake.objects.count() == count + 1


def test_reorder_through_the_screen(staff_client):
    """R-inventory-020: the reorder screen puts the product on a New purchase
    order."""
    product = f.ProductFactory(target_level=8, minimum_reorder_quantity=1)
    f.StockTakeFactory(product=product, quantity_on_hand=0)
    f.ProductVendorFactory(product=product)
    response = staff_client.post(
        reverse("inventory:product_reorder", args=[product.pk]),
    )
    assert response.status_code == HTTPStatus.FOUND
    line = PurchaseOrderDetail.objects.get(product=product)
    assert (line.quantity, line.unit_cost) == (8, Decimal("2.5000"))


def test_vendor_link_and_removal_through_the_screens(staff_client):
    """R-inventory-029: link a vendor, then remove the link."""
    product = f.ProductFactory()
    vendor = f.VendorFactory()
    url = reverse("inventory:form_sfrmProductDetail_Vendors", args=[product.pk])
    assert staff_client.post(url, {"vendor": vendor.pk}).status_code == HTTPStatus.FOUND
    link = ProductVendor.objects.get(product=product, vendor=vendor)
    again = staff_client.post(url, {"vendor": vendor.pk})
    assert b"R-inventory-029" in again.content
    remove = reverse("inventory:product_vendor_remove", args=[product.pk, link.pk])
    staff_client.post(remove, {"confirmed": "on"})
    assert not ProductVendor.objects.filter(pk=link.pk).exists()


def test_delete_screens(staff_client, link):
    """R-inventory-016 and R-inventory-015 through the screens."""
    blocked = reverse("inventory:product_delete", args=[link.product_id])
    response = staff_client.post(blocked, {"confirmed": "on"})
    assert b"R-inventory-016" in response.content
    free = f.ProductFactory()
    response = staff_client.post(
        reverse("inventory:product_delete", args=[free.pk]),
        {"confirmed": "on"},
    )
    assert response.status_code == HTTPStatus.FOUND
    assert not Product.objects.filter(pk=free.pk).exists()
    category = link.product.product_category
    response = staff_client.post(
        reverse("inventory:category_delete", args=[category.pk]),
        {"confirmed": "on"},
    )
    assert b"R-inventory-015" in response.content
    assert ProductCategory.objects.filter(pk=category.pk).exists()


def test_detail_page_states(staff_client):
    """R-inventory-021 and R-inventory-022: a discontinued product is marked and has
    no reorder action; the levels are shown."""
    product = f.ProductFactory(discontinued=True)
    response = staff_client.get(
        reverse("inventory:form_frmProductDetail", args=[product.pk]),
    )
    assert b'id="discontinued"' in response.content
    assert b'id="reorder"' not in response.content
    assert b'id="product-levels"' in response.content
    jump = staff_client.get(
        reverse("inventory:form_frmProductDetail", args=[product.pk]),
        {"find": str(product.pk)},
    )
    assert jump.status_code == HTTPStatus.FOUND
