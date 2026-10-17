"""Workflow purchase_order_to_stock: purchase order to receiving to stock update.

Must keep: "purchase order -> receiving -> stock update".

E2e rules proven here: R-purchasing-003 (New, Submitted, Approved, Received, Closed,
one action per step, each only from the step before; the screen marks the steps
done) and R-purchasing-008 (an Approved purchase order's quantity counts as on order;
once received it raises the product's available stock).

Workflow rules shown on the way: R-purchasing-001 (a new purchase order is New),
R-purchasing-004 (submit), R-purchasing-005 (approve, as the approver role),
R-purchasing-006 (allocation after approve and receive), R-purchasing-007 (receiving
needs the confirmation), R-purchasing-009 (close needs the shipping fee and payment
method and stores tax, payment amount and payment date), R-purchasing-010 (the
amounts), R-purchasing-012 (lines are frozen from Submitted on) and R-purchasing-019
(a line needs product, quantity and unit cost).

The vendor is the first one, by name, on the new purchase order's vendor list that
supplies a product. Expected figures come from the defaults the line form filled in
and from the product page's figures before each step.
"""

from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Page
from playwright.sync_api import expect

from northwind.domain.system_settings import vendor_tax_rate
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderStatus
from northwind.purchasing import queries as purchasing_queries
from tests.e2e.helpers import frame
from tests.e2e.helpers import levels
from tests.e2e.helpers import link_employee
from tests.e2e.helpers import number

WORKFLOW = "purchase_order_to_stock"
SHIPPING_FEE = Decimal("25.00")
TOLERANCE = Decimal("0.0001")  # the stored amounts keep four decimals


def shown(amount: Decimal) -> str:
    """An amount as the purchasing screens show it: two decimals, thousands commas
    (the area's money filter)."""
    return f"{amount:,.2f}"


def po_status(code: int) -> str:
    return str(PurchaseOrderStatus.objects.get(pk=code))


def vendor_with_products() -> tuple:
    for vendor in purchasing_queries.vendors():
        products = list(purchasing_queries.vendor_products(vendor.pk))
        if products:
            return vendor, products
    msg = "seed 1 has no vendor that supplies a product"
    raise AssertionError(msg)


def detail(page: Page, label: str) -> str:
    """The value next to a <dt> label on the purchase order screen."""
    return page.locator(f"dt:text-is('{label}') + dd").inner_text().strip()


def steps_done(page: Page) -> list[str]:
    return [
        text.replace("(done)", "").strip()
        for text in page.locator("#po-workflow .text-bg-success").all_inner_texts()
    ]


def product_levels(page: Page, product_id: int) -> dict[str, int]:
    page.goto(f"/inventory/products/{product_id}/")
    return levels(page)


def test_purchase_order_to_stock(page: Page, sign_in, shot):  # noqa: PLR0915
    vendor, products = vendor_with_products()
    product = products[0]
    # The approver signs in as an employee, who is recorded as submitter and
    # approver (R-purchasing-004, R-purchasing-005).
    approver = link_employee("approver")
    sign_in(page, "approver")
    before = product_levels(page, product.pk)

    # 1. Open the purchase order list and start a new purchase order.
    page.get_by_role("link", name="Purchasing and receiving").click()
    expect(page.get_by_role("heading", name="Purchase orders")).to_be_visible()
    shot(page, "purchasing-main")
    shot(page, f"{WORKFLOW}-01-purchase-order-list")
    page.get_by_role("link", name="New purchase order").click()
    expect(page.get_by_role("heading", name="New purchase order")).to_be_visible()

    # 2. Choose the vendor and save: the purchase order is New (R-purchasing-001).
    page.locator("select[name=vendor]").select_option(label=vendor.company_name)
    page.get_by_role("button", name="Save").click()
    expect(page).to_have_url(re.compile(r"/purchasing/\d+/$"))
    po_number = int(re.search(r"/purchasing/(\d+)/$", page.url).group(1))
    expect(page.locator("h1")).to_contain_text(f"Purchase order {po_number}")
    assert detail(page, "Vendor") == vendor.company_name
    assert detail(page, "Status") == po_status(PurchaseOrderStatusCode.NEW)
    assert steps_done(page) == []

    # 3. Add a line for one of the vendor's products: choosing it fills in the
    # reorder quantity and the standard unit cost (R-purchasing-018).
    lines = page.locator("#po-lines")
    lines.locator("select[name=product]").select_option(str(product.pk))
    expect(lines.locator("input[name=unit_cost]")).not_to_have_value("")
    quantity = int(lines.locator("input[name=quantity]").input_value())
    unit_cost = number(lines.locator("input[name=unit_cost]").input_value())
    assert unit_cost == Decimal(str(product.standard_unit_cost))
    lines.get_by_role("button", name="Add line").click()
    row = lines.locator("tbody tr").filter(has_text=product.product_name)
    expect(row.locator("td").nth(2)).to_have_text(str(quantity))
    subtotal = unit_cost * quantity
    expect(page.locator("#po-subtotal")).to_have_text(shown(subtotal))

    # 4. Submit: Submitted, the first step done, the lines frozen (R-purchasing-004,
    # R-purchasing-012).
    actions = page.locator("#po-actions")
    actions.get_by_role("button", name="Submit").click()
    status = page.locator("dt:text-is('Status') + dd")
    expect(status).to_have_text(po_status(PurchaseOrderStatusCode.SUBMITTED))
    assert steps_done(page) == ["Submitted"]
    assert approver.last_name in detail(page, "Submitted by")
    expect(
        page.locator("#po-lines").get_by_role("button", name="Add line"),
    ).to_have_count(0)
    # The heading, vendor, status and the frozen line items with their subtotal.
    frame(page, page.locator("h1"), status, page.locator("#po-subtotal"))
    shot(page, f"{WORKFLOW}-04-submitted")

    # 5. Approve as the approver: Approved, and the quantity counts as on order
    # (R-purchasing-005, R-purchasing-008).
    actions.get_by_role("button", name="Approve").click()
    expect(page.locator("dt:text-is('Status') + dd")).to_have_text(
        po_status(PurchaseOrderStatusCode.APPROVED),
    )
    assert steps_done(page) == ["Submitted", "Approved"]
    assert approver.last_name in detail(page, "Approved by")
    shot(page, f"{WORKFLOW}-05-approved")
    approved = product_levels(page, product.pk)
    assert approved["on_order"] == before["on_order"] + quantity
    page.goto(f"/purchasing/{po_number}/")

    # 6. Receive: refused until the posting is confirmed, then Received
    # (R-purchasing-007).
    actions.get_by_role("button", name="Receive purchase order").click()
    expect(page.locator("dt:text-is('Status') + dd")).to_have_text(
        po_status(PurchaseOrderStatusCode.APPROVED),
    )
    expect(page.locator(".alert").first).to_contain_text("R-purchasing-007")
    actions.locator("input[name=confirm]").check()
    actions.get_by_role("button", name="Receive purchase order").click()
    expect(page.locator("dt:text-is('Status') + dd")).to_have_text(
        po_status(PurchaseOrderStatusCode.RECEIVED),
    )
    assert steps_done(page) == ["Submitted", "Approved", "Received"]
    expect(row.locator("td").nth(5)).not_to_have_text("")

    # 7. The product page: the received quantity is in stock, no longer on order
    # (R-purchasing-008).
    received = product_levels(page, product.pk)
    assert received["on_order"] == before["on_order"]
    assert (
        received["to_sell"] + received["allocated"]
        == before["to_sell"] + before["allocated"] + quantity
    )
    shot(page, f"{WORKFLOW}-07-stock-updated")

    # 8. Close with the shipping fee and payment method: Closed, with the tax,
    # payment amount and payment date stored (R-purchasing-009, R-purchasing-010).
    page.goto(f"/purchasing/{po_number}/")
    actions.locator("input[name=shipping_fee]").fill("")
    actions.get_by_role("button", name="Close purchase order").click()
    expect(page.locator("dt:text-is('Status') + dd")).to_have_text(
        po_status(PurchaseOrderStatusCode.RECEIVED),
    )
    actions.locator("input[name=shipping_fee]").fill(str(SHIPPING_FEE))
    actions.locator("select[name=payment_method]").select_option(index=1)
    actions.get_by_role("button", name="Close purchase order").click()
    expect(page.locator("dt:text-is('Status') + dd")).to_have_text(
        po_status(PurchaseOrderStatusCode.CLOSED),
    )
    assert steps_done(page) == ["Submitted", "Approved", "Received", "Closed"]
    tax = Decimal(str(vendor_tax_rate())) * subtotal
    total = subtotal + tax + SHIPPING_FEE
    stored = PurchaseOrder.objects.get(pk=po_number)
    assert abs(stored.tax_amount - tax) <= TOLERANCE
    assert abs(stored.payment_amount - total) <= TOLERANCE
    assert stored.payment_date is not None
    assert detail(page, "Tax") == shown(stored.tax_amount)
    assert detail(page, "Total") == shown(stored.payment_amount)
    assert detail(page, "Payment date")
    shot(page, f"{WORKFLOW}-08-closed")
