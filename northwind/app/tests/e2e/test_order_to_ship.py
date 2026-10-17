"""Workflow order_to_ship: order entry to invoice (printable PDF) to shipping.

Must keep: "order entry -> invoice (printable PDF) -> shipping".

E2e rules proven here: R-orders-050 (the order list is the first screen after
signing in), R-orders-029 (a new order is started from the order list; orders open
from the order list and from a company's order list, several side by side; a line's
product links to that product's screen) and
R-orders-030 (the order moves forward one step at a time through its actions, the next
action is highlighted and an action out of turn is refused with a message).

Workflow rules shown on the way: R-orders-001 (a new order is pre-filled with the
default tax rate), R-orders-009 (a line is Allocated or No Stock), R-orders-015
(invoicing needs every line Allocated and opens the invoice), R-orders-016 (ship),
R-orders-017 (receive payment), R-orders-018 (close after confirming) and
R-orders-020 (the invoice and its PDF show the order total).

Each step is a page action followed by an assertion on what the user sees. Expected
figures are worked out from what the test entered (quantity x unit price, tax rate,
shipping fee).
"""

from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Page
from playwright.sync_api import expect

from northwind.domain import inventory as stock
from northwind.domain.system_settings import sales_tax_rate
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.choices import TaxStatusCode
from northwind.legacy.models import OrderDetailStatus
from northwind.legacy.models import OrderStatus
from northwind.legacy.models import Product
from northwind.orders import services as order_services
from tests.e2e.helpers import local_input
from tests.e2e.helpers import money
from tests.e2e.helpers import no_op
from tests.e2e.helpers import open_from_list
from tests.e2e.helpers import read_pdf

WORKFLOW = "order_to_ship"
SHIPPING_FEE = Decimal("12.50")
QUANTITY = 2
PRIMARY = re.compile(r"\bbtn-primary\b")


def order_status(code: int) -> str:
    return str(OrderStatus.objects.get(pk=code))


def line_status(code: int) -> str:
    return str(OrderDetailStatus.objects.get(pk=code))


def products_for_lines() -> tuple[Product, Product]:
    """From the line form's product list: one whose stock covers QUANTITY and one
    with nothing to sell."""
    offered = list(order_services.product_choices().order_by("product_name"))
    in_stock = next(p for p in offered if stock.product_to_sell(p) >= QUANTITY)
    short = next(p for p in offered if stock.product_to_sell(p) <= 0)
    return in_stock, short


def run_order_to_ship(page: Page, sign_in, shot=no_op, pause=no_op) -> int:  # noqa: PLR0915
    """The whole workflow, signed in as staff; returns the order number."""
    in_stock, short = products_for_lines()
    heading = page.locator("h1")
    badge = heading.locator(".badge")
    actions = page.locator("#order-actions")
    lines = page.locator("#order-lines")

    # 1. Sign in and land on the order list (R-orders-050).
    page.goto("/")
    pause(page)
    sign_in(page, "staff")
    expect(page).to_have_url(re.compile(r"/orders/(start/)?$"))
    expect(page.get_by_role("heading", name="Orders", exact=True)).to_be_visible()
    expect(page.locator("#order-list-footer")).to_contain_text("orders, total")
    shot(page, f"{WORKFLOW}-01-order-list")
    shot(page, "orders-main")
    pause(page)

    # 2. Start a new order from the order list and choose the customer; the tax rate
    # is pre-filled (R-orders-029, R-orders-001).
    page.get_by_role("link", name="New order").click()
    expect(page).to_have_url(re.compile(r"/orders/new/$"))
    expect(page.locator("#id_tax_rate")).to_have_value(str(sales_tax_rate()))
    customer = page.locator("#id_customer option").nth(1).inner_text()
    page.locator("#id_customer").select_option(label=customer)
    page.wait_for_load_state("networkidle")
    page.locator("#id_employee").select_option(index=1)
    page.locator("#id_shipping_fee").fill(str(SHIPPING_FEE))
    page.locator("#id_tax_status").select_option(str(TaxStatusCode.TAXABLE))
    shot(page, f"{WORKFLOW}-02-new-order")
    pause(page)

    # 3. Save the order header: the order screen shows it as New, with Create invoice
    # highlighted as the next action (R-orders-030).
    page.get_by_role("button", name="Save").click()
    expect(page).to_have_url(re.compile(r"/orders/\d+/$"))
    order_id = int(re.search(r"/orders/(\d+)/$", page.url).group(1))
    expect(heading).to_contain_text(f"Order {order_id}")
    expect(badge).to_have_text(order_status(OrderStatusCode.NEW))
    expect(page.locator("dl").first).to_contain_text(customer)
    expect(actions.get_by_role("button", name="Create invoice")).to_have_class(PRIMARY)
    pause(page)

    # 4. Add order lines: one is Allocated, one No Stock (R-orders-009).
    lines.locator("select[name=product]").select_option(str(in_stock.pk))
    lines.locator("input[name=quantity]").fill(str(QUANTITY))
    lines.get_by_role("button", name="Add line").click()
    expect(
        lines.locator("tbody tr").filter(has_text=in_stock.product_name),
    ).to_contain_text(
        line_status(OrderDetailStatusCode.ALLOCATED),
    )
    lines.locator("select[name=product]").select_option(str(short.pk))
    lines.locator("input[name=quantity]").fill(str(QUANTITY))
    lines.get_by_role("button", name="Add line").click()
    short_row = lines.locator("tbody tr").filter(has_text=short.product_name)
    expect(short_row).to_contain_text(line_status(OrderDetailStatusCode.NO_STOCK))
    # A line's product opens that product's screen (R-orders-029).
    expect(short_row.get_by_role("link", name=short.product_name)).to_have_attribute(
        "href",
        re.compile(rf"/inventory/products/{short.pk}/$"),
    )
    shot(page, f"{WORKFLOW}-04-order-lines")
    pause(page)

    # Out of turn: shipping a New order is refused with a message (R-orders-030); a
    # No Stock line blocks the invoice (R-orders-015). The order stays New.
    page.reload()
    actions.get_by_role("button", name="Ship order").click()
    expect(page.locator(".alert").first).to_contain_text("R-orders-0")
    expect(badge).to_have_text(order_status(OrderStatusCode.NEW))
    actions.get_by_role("button", name="Create invoice").click()
    expect(page.locator(".alert").first).to_contain_text("R-orders-015")
    expect(badge).to_have_text(order_status(OrderStatusCode.NEW))
    pause(page)
    # Delete the No Stock line after confirming.
    short_row.get_by_role("link", name="Delete").click()
    page.get_by_role("button", name="Yes", exact=True).click()
    expect(page).to_have_url(re.compile(rf"/orders/{order_id}/$"))
    expect(lines.locator("tbody")).not_to_contain_text(short.product_name)
    subtotal = Decimal(str(in_stock.unit_price)) * QUANTITY
    tax = Decimal(str(sales_tax_rate())) * subtotal
    total = subtotal + tax + SHIPPING_FEE
    amounts = page.locator("#order-amounts")
    expect(amounts.locator("tr").first).to_contain_text(money(subtotal))
    expect(amounts.locator("tr").last).to_contain_text(money(total))
    pause(page)

    # 5. Create the invoice: it opens with the order's total (R-orders-015,
    # R-orders-020); the order is Invoiced and its PDF downloads.
    actions.get_by_role("button", name="Create invoice").click()
    expect(page).to_have_url(re.compile(rf"/orders/{order_id}/invoice/$"))
    expect(page.locator("#invoice-number")).to_contain_text(str(order_id))
    expect(page.locator("#invoice-totals")).to_contain_text(money(total))
    shot(page, f"{WORKFLOW}-05-invoice")
    pause(page)
    page.go_back()
    page.reload()
    expect(badge).to_have_text(order_status(OrderStatusCode.INVOICED))
    expect(lines.locator("tbody")).to_contain_text(
        line_status(OrderDetailStatusCode.INVOICED),
    )
    with page.expect_download() as download:
        page.get_by_role("link", name="Invoice PDF").click()
    read_pdf(download.value)
    pause(page)

    # 6. Ship: shipped date and shipper (the shipping fee came with the order).
    expect(actions.get_by_role("button", name="Ship order")).to_have_class(PRIMARY)
    actions.locator("input[name=shipped_date]").fill(local_input())
    actions.locator("select[name=shipper]").select_option(index=1)
    shot(page, f"{WORKFLOW}-06-ship")
    pause(page)
    actions.get_by_role("button", name="Ship order").click()
    expect(badge).to_have_text(order_status(OrderStatusCode.SHIPPED))
    expect(lines.locator("tbody")).to_contain_text(
        line_status(OrderDetailStatusCode.SHIPPED),
    )
    pause(page)

    # 7. Receive payment: payment method and paid date.
    actions.locator("select[name=payment_method]").select_option(index=1)
    actions.locator("input[name=paid_date]").fill(local_input())
    pause(page)
    actions.get_by_role("button", name="Receive payment").click()
    expect(badge).to_have_text(order_status(OrderStatusCode.PAID))
    pause(page)

    # 8. Close after confirming; nothing is editable afterwards.
    actions.locator("#confirm-close").check()
    pause(page)
    actions.get_by_role("button", name="Close order").click()
    expect(badge).to_have_text(order_status(OrderStatusCode.CLOSED))
    expect(page.get_by_role("link", name="Edit", exact=True)).to_have_count(0)
    expect(amounts.locator("tr").last).to_contain_text(money(total))
    shot(page, f"{WORKFLOW}-08-closed")
    pause(page)
    return order_id


def test_order_to_ship(page: Page, sign_in, shot):
    order_id = run_order_to_ship(page, sign_in, shot)

    # R-orders-029: the order opens from the order list ...
    page.goto("/orders/?show=all")
    open_from_list(
        page,
        page.locator("#record-table").get_by_role(
            "link",
            name=str(order_id),
            exact=True,
        ),
    )
    expect(page).to_have_url(re.compile(rf"/orders/{order_id}/$"))
    expect(page.locator("h1")).to_contain_text(f"Order {order_id}")
    # ... and from the customer's order list on the company screen ...
    page.locator("dl").first.get_by_role("link").first.click()
    expect(page).to_have_url(re.compile(r"/orders/companies/\d+/$"))
    page.locator("#customer-orders").get_by_role(
        "link",
        name=str(order_id),
        exact=True,
    ).click()
    expect(page).to_have_url(re.compile(rf"/orders/{order_id}/$"))
    # ... and another order can be open beside it.
    other = page.context.new_page()
    other.goto("/orders/?show=all")
    numbers = other.locator("#record-table tbody tr td:first-child a")
    other_id = next(n for n in numbers.all_inner_texts() if n != str(order_id))
    open_from_list(other, numbers.get_by_text(other_id, exact=True))
    expect(other.locator("h1")).to_contain_text(f"Order {other_id}")
    page.bring_to_front()
    page.reload()
    expect(page.locator("h1")).to_contain_text(f"Order {order_id}")
