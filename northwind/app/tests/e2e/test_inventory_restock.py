"""Workflow inventory_restock: inventory levels and restocking.

Must keep: "inventory levels and restocking".

E2e rules proven here: R-inventory-030 (open the product list, open a product short
of its target, see its levels and suggested reorder quantity, reorder it from a linked
vendor, find the New purchase order on the product's purchase-order history; once it
is approved the quantity shows as on order, once received the stock rises and waiting
order lines are allocated), R-inventory-010 (a count that differs from the expected
quantity shows both figures and must be confirmed; declining saves nothing) and
R-purchasing-023 (the vendor dialog lists only the product's vendors by name, refuses
OK without a choice, cancels without creating anything and confirms on a
double-click).

Workflow rules shown on the way: R-inventory-001 (physical stock from the last stock
take), R-inventory-006 (the suggested reorder quantity), R-inventory-008 (a stock take
re-runs the allocation), R-inventory-009 (the stock take is dated by the system and
stores the expected quantity), R-inventory-011 (the stock take is added to the list),
R-inventory-017, R-inventory-018, R-inventory-019, R-inventory-020 and
R-inventory-021 (the reorder), R-inventory-022 (the product page's figures),
R-purchasing-001 (the reorder's purchase order starts New), R-purchasing-018 and
R-purchasing-020 (the line takes the reorder quantity and the standard cost, one line
per product).

The product is the first one, by name, that is not discontinued, has several vendors,
nothing on order and order lines waiting for stock, with less to sell than its target
level. Expected figures are worked out from the figures the screens showed before each
step.
"""

from __future__ import annotations

import datetime as dt
import re

from playwright.sync_api import Page
from playwright.sync_api import expect

from northwind.domain import inventory as stock
from northwind.inventory import services as inventory_services
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.models import Product
from northwind.legacy.models import PurchaseOrderStatus
from tests.e2e.helpers import levels
from tests.e2e.helpers import link_employee
from tests.e2e.helpers import number
from tests.e2e.helpers import open_from_list
from tests.e2e.helpers import scroll_to
from tests.e2e.helpers import sign_out

WORKFLOW = "inventory_restock"
COUNT_DIFFERENCE = 10


def restock_candidate() -> Product:
    for product in Product.objects.filter(discontinued=False).order_by("product_name"):
        figures = stock.stock_levels(product)
        if (
            len(inventory_services.linked_vendors(product)) > 1
            and figures.on_order == 0
            and figures.no_stock > 0
            and figures.to_sell < (product.target_level or 0)
            and inventory_services.outstanding_purchase_order(product) is None
        ):
            return product
    msg = "seed 1 has no product short of its target with several vendors"
    raise AssertionError(msg)


def po_status(code: int) -> str:
    return str(PurchaseOrderStatus.objects.get(pk=code))


def open_product_from_list(page: Page, product: Product) -> None:
    page.goto("/inventory/")
    row = page.locator("table tbody tr").filter(has_text=product.product_code)
    open_from_list(page, row.get_by_role("link").first)
    expect(page.locator("h1")).to_contain_text(product.product_name)


def purchase_order_history(page: Page):
    """The history panel loads when it scrolls into view."""
    page.get_by_role(
        "heading",
        name="Purchase order history",
    ).scroll_into_view_if_needed()
    panel = page.locator("#panel-purchase-orders")
    expect(panel).to_be_visible()
    return panel


def test_inventory_restock(page: Page, sign_in, shot):  # noqa: PLR0915
    product = restock_candidate()
    vendors = [v.company_name for v in inventory_services.linked_vendors(product)]
    sign_in(page, "staff")

    # The product list is the area's main screen.
    page.get_by_role("link", name="Products and Inventory").click()
    expect(page.get_by_role("heading", name="Products")).to_be_visible()
    shot(page, "inventory-main")

    # 1. Open the product's stock takes and enter a count that differs from the
    # expected quantity: both figures are shown and Cancel saves nothing
    # (R-inventory-010).
    open_product_from_list(page, product)
    before = levels(page)
    expected = before["to_sell"] + before["allocated"]
    counted = expected + COUNT_DIFFERENCE
    panel = page.locator("#panel-stock-takes")
    expect(panel).to_be_visible()
    rows_before = panel.locator("tbody tr").count()
    panel.locator("input[name=quantity_on_hand]").fill(str(counted))
    panel.get_by_role("button", name="Record stock take").click()
    mismatch = page.locator("#stock-take-mismatch")
    expect(mismatch).to_contain_text(f"({counted})")
    expect(mismatch).to_contain_text(f"({expected})")
    scroll_to(page.get_by_role("heading", name="Stock takes"))
    shot(page, f"{WORKFLOW}-01-count-differs")
    panel.get_by_role("link", name="Cancel").click()
    expect(mismatch).to_have_count(0)
    expect(panel.locator("tbody tr")).to_have_count(rows_before)

    # 2. Enter it again and confirm the count.
    panel.locator("input[name=quantity_on_hand]").fill(str(counted))
    panel.get_by_role("button", name="Record stock take").click()
    expect(mismatch).to_be_visible()
    panel.get_by_role("button", name="Confirm count").click()
    expect(mismatch).to_have_count(0)

    # 3. The stock take is listed with today's date, the count and the expected
    # quantity (R-inventory-009); the figures follow the count and the waiting lines
    # are re-allocated (R-inventory-001, R-inventory-008).
    newest = panel.locator("tbody tr").filter(has_text=dt.date.today().isoformat())  # noqa: DTZ011
    expect(newest).to_have_count(1)
    cells = newest.locator("td")
    expect(cells.nth(1)).to_have_text(str(counted))
    expect(cells.nth(2)).to_have_text(str(expected))
    page.reload()
    counted_levels = levels(page)
    assert counted_levels["to_sell"] + counted_levels["allocated"] == counted
    assert (
        counted_levels["allocated"] + counted_levels["no_stock"]
        == before["allocated"] + before["no_stock"]
    )
    expect(panel).to_be_visible()
    scroll_to(page.locator("#product-levels"))
    shot(page, f"{WORKFLOW}-03-stock-take-saved")

    # 4. The product list shows each product's figures, this one's as on its page.
    page.goto("/inventory/")
    row = page.locator("table tbody tr").filter(has_text=product.product_code)
    headers = [h.strip() for h in page.locator("table thead th").all_inner_texts()]
    values = row.locator("td").all_inner_texts()
    shown = dict(zip(headers, values, strict=False))
    assert int(number(shown["To sell"])) == counted_levels["to_sell"]
    assert int(number(shown["No stock"])) == counted_levels["no_stock"]
    assert int(number(shown["Allocated"])) == counted_levels["allocated"]
    assert int(number(shown["On order"])) == counted_levels["on_order"]
    shot(page, f"{WORKFLOW}-04-product-list")

    # 5. Open the product: less to sell than its target, so the suggested reorder
    # quantity is the shortfall, highlighted (R-inventory-006, R-inventory-021).
    open_product_from_list(page, product)
    target = product.target_level or 0
    minimum = product.minimum_reorder_quantity or 1
    shortfall = target + counted_levels["no_stock"] - counted_levels["to_sell"]
    suggested = max(shortfall, minimum)
    assert counted_levels["to_sell"] < target
    assert levels(page)["reorder"] == suggested
    expect(page.locator("#product-levels tr.table-warning")).to_contain_text(
        str(suggested),
    )
    shot(page, f"{WORKFLOW}-05-product-short")

    # 6a. Reorder opens the vendor dialog, which lists only the product's vendors by
    # name; OK without a choice is refused, Cancel creates nothing (R-purchasing-023).
    reorder_url = f"/inventory/products/{product.pk}/reorder/"
    page.locator("#reorder").click()
    expect(page).to_have_url(re.compile(rf"/purchasing/select-vendor/{product.pk}/"))
    dialog = page.locator("#vendor-dialog")
    expect(dialog.locator("label.form-check-label")).to_have_text(vendors)
    dialog.get_by_role("button", name="OK").click()
    expect(page.locator("#vendor-dialog")).to_be_visible()
    expect(page.locator(".invalid-feedback, .alert").first).to_be_visible()
    shot(page, f"{WORKFLOW}-06-vendor-dialog")
    page.locator("#vendor-dialog").get_by_role("button", name="Cancel").click()
    expect(page).to_have_url(re.compile(rf"{reorder_url}$"))
    expect(page.locator(".alert").first).to_contain_text("nothing was created")

    # 6b. On the reorder screen the vendor must be chosen among several
    # (R-inventory-018).
    vendor_select = page.locator("select[name=vendor]")
    expect(vendor_select.locator("option")).to_have_text(["---------", *vendors])
    page.get_by_role("button", name="Reorder").click()
    expect(page.locator("body")).to_contain_text("R-inventory-018")

    # 6c. Reorder again from the product page: a double-click on a vendor confirms
    # it, and the reorder screen opens with that vendor chosen.
    open_product_from_list(page, product)
    page.locator("#reorder").click()
    page.locator("#vendor-dialog label.form-check-label").filter(
        has_text=vendors[0],
    ).first.dblclick()
    expect(page).to_have_url(
        re.compile(rf"{reorder_url}\?product={product.pk}&vendor=\d+"),
    )
    expect(vendor_select.locator("option:checked")).to_have_text(vendors[0])
    page.get_by_role("button", name="Reorder").click()
    expect(page).to_have_url(re.compile(r"/purchasing/\d+/$"))
    po_number = int(re.search(r"/purchasing/(\d+)/$", page.url).group(1))
    expect(page.locator(".alert").first).to_contain_text(
        f"Added {suggested} to purchase order {po_number}",
    )
    line = page.locator("#po-lines tbody tr").filter(has_text=product.product_name)
    expect(line.locator("td").nth(2)).to_have_text(str(suggested))
    expect(page.locator("dl").first).to_contain_text(
        po_status(PurchaseOrderStatusCode.NEW),
    )
    expect(page.locator("dl").first).to_contain_text(vendors[0])

    # 7. The product's purchase-order history shows that New purchase order.
    page.goto(f"/inventory/products/{product.pk}/")
    history = purchase_order_history(page)
    expect(history.locator("tbody tr").filter(has_text=str(po_number))).to_contain_text(
        po_status(PurchaseOrderStatusCode.NEW),
    )
    scroll_to(page.get_by_role("heading", name="Purchase order history"))
    shot(page, f"{WORKFLOW}-07-purchase-order-history")

    # 8. An approver submits and approves it: the quantity is on order; then receives
    # it: the stock rises and the waiting lines are allocated (R-inventory-030). The
    # approver signs in as an employee, who is recorded as submitter and approver
    # (R-purchasing-004, R-purchasing-005).
    sign_out(page)
    link_employee("approver")
    sign_in(page, "approver")
    page.goto(f"/purchasing/{po_number}/")
    page.locator("#po-actions").get_by_role("button", name="Submit").click()
    page.locator("#po-actions").get_by_role("button", name="Approve").click()
    expect(page.locator("dl").first).to_contain_text(
        po_status(PurchaseOrderStatusCode.APPROVED),
    )
    page.goto(f"/inventory/products/{product.pk}/")
    approved = levels(page)
    assert approved["on_order"] == counted_levels["on_order"] + suggested
    page.goto(f"/purchasing/{po_number}/")
    page.locator("#po-actions input[name=confirm]").check()
    page.locator("#po-actions").get_by_role(
        "button",
        name="Receive purchase order",
    ).click()
    expect(page.locator("dl").first).to_contain_text(
        po_status(PurchaseOrderStatusCode.RECEIVED),
    )
    page.goto(f"/inventory/products/{product.pk}/")
    received = levels(page)
    assert received["on_order"] == counted_levels["on_order"]
    assert received["to_sell"] + received["allocated"] == counted + suggested
    assert received["no_stock"] == 0
    assert (
        received["allocated"]
        == counted_levels["allocated"] + counted_levels["no_stock"]
    )
    shot(page, f"{WORKFLOW}-08-received")
