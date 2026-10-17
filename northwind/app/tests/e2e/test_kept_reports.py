"""Workflow kept_reports: the invoice and the four chosen reports.

Must keep: "the invoice report plus at most 4 other reports chosen at S1".

E2e rules proven here: R-reports-016 (the main menu's Reports entry opens the
selection page; Preview opens the employee report interactively and the product
reports and the catalog as print previews that save as PDF), R-reports-013 (the
catalog asks for the PDF until a table of contents exists, then lists each category
once with its starting page) and R-reports-014 (the quality and gastronomic pages and
the order form with the house company and the shipper tick-boxes).

Workflow rules shown on the way: R-orders-019 (an invoiced order's invoice opens again
as a PDF without changing the order), R-orders-020 (the invoice), R-orders-021 (an
order without lines has nothing to print), R-reports-001 (the employee report is
preselected), R-reports-002 (the default period from the latest order date; the
catalog hides the dates), R-reports-007 (the period in the report header),
R-reports-008 (a period without orders is refused), R-reports-009 (the salesperson
filter), R-reports-010 (period subtotals and a grand total) and R-reports-012 (the
catalog's category sections).
"""

from __future__ import annotations

import calendar
import re
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Count
from django.db.models import Max
from django.db.models import Min
from playwright.sync_api import Page
from playwright.sync_api import expect

from northwind.domain import inventory as stock
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.models import Order
from northwind.legacy.models import OrderStatus
from northwind.orders import queries as order_queries
from northwind.orders import services as order_services
from tests.e2e.helpers import open_from_list
from tests.e2e.helpers import pdf_text
from tests.e2e.helpers import read_pdf
from tests.e2e.helpers import scroll_to

if TYPE_CHECKING:
    import datetime as dt

WORKFLOW = "kept_reports"
EMPLOYEE_REPORT = "Monthly Orders per Employee"
PRODUCT_REPORT = "Monthly Orders per Product"
QUARTERLY_REPORT = "Quarterly Orders per Product"
CATALOG = "Fall Catalog"


def short_date(day: dt.date) -> str:
    """Access's Short Date with United States settings."""
    return f"{day.month}/{day.day}/{day.year}"


def months_before(day: dt.date, months: int) -> dt.date:
    month = day.month - months
    year = day.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return day.replace(
        year=year,
        month=month,
        day=min(day.day, calendar.monthrange(year, month)[1]),
    )


def invoiced_order() -> Order:
    """Arrange: seed 1 has no invoiced order with something to print, so one is
    entered and invoiced through the orders area's services (the screens for that are
    proven by test_order_to_ship)."""
    customer = order_queries.customers().first()
    employee = order_queries.employee_choices().first()
    product = next(
        p
        for p in order_services.product_choices().order_by("product_name")
        if stock.product_to_sell(p) >= 1
    )
    order = order_services.save_order(
        order_services.new_order(),
        {"customer": customer, "employee": employee, "shipping_fee": Decimal("10.00")},
    )
    order_services.save_order_line(
        order,
        None,
        {"product": product, "quantity": 1, "discount": 0},
    )
    return order_services.create_invoice(order)


def order_without_lines() -> Order:
    """An order past New without lines from seed 1, or, when the seed has none, a
    saved order without lines entered through the orders area's services."""
    existing = (
        Order.objects.exclude(order_status_id=OrderStatusCode.NEW)
        .annotate(line_count=Count("lines"))
        .filter(line_count=0)
        .order_by("pk")
        .first()
    )
    if existing is not None:
        return existing
    return order_services.save_order(
        order_services.new_order(),
        {
            "customer": order_queries.customers().first(),
            "employee": order_queries.employee_choices().first(),
        },
    )


def choose_report(page: Page, title: str) -> None:
    page.locator("#report-selection .list-group").get_by_role(
        "link",
        name=title,
    ).click()
    expect(page.locator("#selected-report-name")).to_have_text(title)


def report_rows(page: Page):
    return page.locator("#report-body table.report-table tbody tr").filter(
        has_not=page.locator("td[colspan]"),
    )


def test_kept_reports(page: Page, sign_in, shot, htmx_ready):  # noqa: PLR0915
    invoiced = invoiced_order()
    status = str(OrderStatus.objects.get(pk=invoiced.order_status_id))
    dates = Order.objects.aggregate(first=Min("order_date"), last=Max("order_date"))
    latest = dates["last"].date()
    sign_in(page, "staff")

    # 1. Open an invoiced order from the order list and open its invoice again as a
    # PDF; the order does not change (R-orders-019).
    page.goto("/orders/?show=all")
    open_from_list(
        page,
        page.locator("#record-table").get_by_role(
            "link",
            name=str(invoiced.pk),
            exact=True,
        ),
    )
    expect(page.locator("h1 .badge")).to_have_text(status)
    with page.expect_download() as download:
        page.get_by_role("link", name="Invoice PDF").click()
    reprint = pdf_text(read_pdf(download.value)).splitlines()
    assert f"Invoice # {invoiced.pk}" in reprint
    page.get_by_role("link", name="Invoice", exact=True).click()
    expect(page.locator("#invoice-number")).to_contain_text(str(invoiced.pk))
    shot(page, f"{WORKFLOW}-01-invoice")
    page.goto(f"/orders/{invoiced.pk}/")
    expect(page.locator("h1 .badge")).to_have_text(status)
    # An order without lines has nothing to print, on the page and as a PDF
    # (R-orders-021).
    empty = order_without_lines()
    page.goto(f"/orders/{empty.pk}/invoice/")
    expect(page.locator("#nothing-to-print")).to_contain_text("R-orders-021")
    expect(page.locator("#invoice-lines")).to_have_count(0)
    page.goto(f"/orders/{empty.pk}/invoice/?format=pdf")
    expect(page).to_have_url(re.compile(rf"/orders/{empty.pk}/$"))
    expect(page.locator(".alert", has_text="R-orders-021")).to_be_visible()

    # 2. Reports from the main menu: the employee report is preselected with the
    # default period (R-reports-016, R-reports-001, R-reports-002).
    page.goto(f"/orders/{invoiced.pk}/")
    page.get_by_role("link", name="Sales and Catalog Reports").click()
    expect(page.get_by_role("heading", name="Reports", exact=True)).to_be_visible()
    expect(page.locator("#selected-report-name")).to_have_text(EMPLOYEE_REPORT)
    expect(page.locator("input[name=end]")).to_have_value(latest.isoformat())
    expect(page.locator("input[name=start]")).to_have_value(
        months_before(latest, 3).isoformat(),
    )
    shot(page, "reports-main")
    shot(page, f"{WORKFLOW}-02-report-selection")

    # A period without orders is refused (R-reports-008).
    page.locator("input[name=start]").fill("1900-01-01")
    page.locator("input[name=end]").fill("1900-01-31")
    page.get_by_role("button", name="Preview").click()
    expect(page.locator("body")).to_contain_text("R-reports-008")

    # 3. Change the dates to cover every order, preview the interactive report and
    # filter it to one salesperson (R-reports-007, R-reports-009).
    first = dates["first"].date()
    page.goto("/reports/")
    page.locator("input[name=start]").fill(first.isoformat())
    page.locator("input[name=end]").fill(latest.isoformat())
    page.get_by_role("button", name="Preview").click()
    expect(page.get_by_role("heading", name=EMPLOYEE_REPORT)).to_be_visible()
    expect(page.locator("#report-criteria")).to_have_text(
        f"Order dates between {short_date(first)} and {short_date(latest)}",
    )
    expect(page.locator("tr.grand-total")).to_be_visible()
    all_rows = report_rows(page).count()
    salesperson = page.locator("#id_employee option").nth(1).inner_text().strip()
    htmx_ready(page, "form[hx-trigger=change]")
    page.locator("#id_employee").select_option(index=1)
    expect(page).to_have_url(re.compile(r"employee=\d+"))
    names = {
        row.locator("td").nth(1).inner_text().strip() for row in report_rows(page).all()
    }
    assert names == {salesperson}
    assert report_rows(page).count() <= all_rows
    shot(page, f"{WORKFLOW}-03-sales-by-employee")

    # 4. Monthly and quarterly sales per product: period subtotals and a grand total
    # (R-reports-010).
    for title in (PRODUCT_REPORT, QUARTERLY_REPORT):
        page.goto("/reports/")
        choose_report(page, title)
        page.locator("input[name=start]").fill(first.isoformat())
        page.locator("input[name=end]").fill(latest.isoformat())
        page.get_by_role("button", name="Preview", exact=True).click()
        expect(page.get_by_role("heading", name=title)).to_be_visible()
        expect(page.locator("tr.subtotal").first).to_contain_text("Total Orders for")
        expect(page.locator("tr.grand-total")).to_contain_text("Grand Total")
    shot(page, f"{WORKFLOW}-04-sales-by-product-quarterly")

    # 5. Save the sales report as PDF.
    with page.expect_download() as download:
        page.locator("#report-body").get_by_role("link", name="PDF").click()
    read_pdf(download.value)

    # 6. Choose the product catalog: the date inputs are hidden; the preview asks for
    # the PDF to build the table of contents (R-reports-002, R-reports-013).
    page.goto("/reports/")
    choose_report(page, CATALOG)
    expect(page.locator("input[name=start]")).to_have_count(0)
    expect(page.locator("input[name=end]")).to_have_count(0)
    page.get_by_role("button", name="Preview", exact=True).click()
    expect(page.get_by_role("heading", name=CATALOG)).to_be_visible()
    expect(page.locator("#toc-note")).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role("link", name="Generate PDF").click()
    read_pdf(download.value)

    # 7. The table of contents lists each category once with its starting page; the
    # fixed pages and the order form with the shipper list follow (R-reports-013,
    # R-reports-014, R-reports-012).
    page.reload()
    expect(page.locator("#toc-note")).to_have_count(0)
    titles = page.locator("table.toc td.toc-title").all_inner_texts()
    pages = page.locator("table.toc td.toc-page").all_inner_texts()
    assert titles, "the table of contents is empty"
    assert len(titles) == len(set(titles))
    assert all(p.strip().isdigit() for p in pages)
    sections = page.locator("section.catalog-section h2").all_inner_texts()
    assert sorted(titles) == sorted(sections)
    expect(page.locator(".catalog-quality h2")).to_be_visible()
    expect(page.locator(".catalog-gastronomic h2")).to_be_visible()
    order_form = page.locator(".catalog-order-form")
    expect(order_form.get_by_role("heading", name="Order Form")).to_be_visible()
    expect(order_form.locator(".house-company").first).to_be_visible()
    expect(order_form.locator(".catalog-ship-via li").first).to_be_visible()
    scroll_to(page.locator(".catalog-toc"))
    shot(page, f"{WORKFLOW}-07-catalog-contents")

    # 8. Save the catalog as PDF from the selection page.
    page.goto("/reports/")
    choose_report(page, CATALOG)
    with page.expect_download() as download:
        page.locator("#report-criteria").get_by_role("button", name="PDF").click()
    read_pdf(download.value)
