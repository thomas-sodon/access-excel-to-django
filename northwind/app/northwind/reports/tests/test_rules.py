"""Rule tests of the Sales and Catalog Reports area.

One test per rule of this area (analysis/rules.json), with the rule id first in the
docstring, data from legacy/factories.py and the expected values worked out by hand
in the test. Never golden files or seed outputs. The rules with test_kind rule are
required here; the equivalence rules (R-reports-004, -005, -006, -011) are also
proven by their units, and the e2e rules (R-reports-013, -014, -016) by S5.e2e.
"""

# Expected values are worked out by hand and written as literals next to the sum.
# ruff: noqa: PLR2004

import datetime as dt
from http import HTTPStatus

import pytest
from django.apps import apps
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.urls import reverse

from northwind.core.saved_queries import run_saved_query
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import OrderStatusFactory
from northwind.legacy.factories import ProductCategoryFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ShipperFactory
from northwind.legacy.factories import StringFactory

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.reports import saved_queries
from northwind.reports import services
from northwind.reports import views
from northwind.reports.period import Period
from northwind.reports.tests.data import at
from northwind.reports.tests.data import catalog_texts
from northwind.reports.tests.data import house_company
from northwind.reports.tests.data import sale

pytestmark = pytest.mark.django_db

SELECTION = "reports:form_frmReports"


def period(start: dt.datetime, end: dt.datetime) -> Period:
    return Period(start=start, end=end)


def rows_of(report_rows) -> list[tuple]:
    return [(row.series_name, row.period_label, row.total) for row in report_rows]


@pytest.fixture
def latest_may():
    """Orders whose latest order date is 31 May 2024 at 15:00: the default period is
    29 Feb 2024 (three calendar months back, the last day of February) to 31 May
    2024, both at midnight."""
    seller = EmployeeFactory(first_name="Ada", last_name="Example")
    product = ProductFactory()
    sale(seller, at(2024, 5, 31, 15), (product, 1, "100.00", 0.0))
    sale(seller, at(2024, 2, 29), (product, 2, "10.00", 0.0))
    sale(seller, at(2024, 2, 28, 23, 59), (product, 4, "10.00", 0.0))
    sale(seller, at(2024, 4, 2, 8), (product, 1, "5.00", 0.0))
    return seller


# ---------------------------------------------------------------- selection page


def test_selection_page_opens_with_sales_per_employee(staff_client, latest_may):
    """R-reports-001: the selection page opens with the monthly sales per employee
    report chosen and its date inputs shown with their defaults, as if the user had
    chosen it."""
    response = staff_client.get(reverse(SELECTION))
    assert response.status_code == HTTPStatus.OK
    selection = response.context["selection"]
    assert selection.report.name == "rptSalesByEmployee"
    page = response.content.decode()
    assert (
        '<strong id="selected-report-name">Monthly Orders per Employee</strong>' in page
    )
    assert 'name="start" value="2024-02-29"' in page
    assert 'name="end" value="2024-05-31"' in page
    assert response.context["preview_url"] == reverse(
        "reports:report_rptSalesByEmployee",
    )


def test_choosing_a_report_sets_or_hides_the_dates(staff_client, latest_may):
    """R-reports-002: a sales report shows the start and end dates (end the date of
    the latest order, start three calendar months earlier); the catalog hides and
    clears them; the page names the chosen report."""
    for name, title in (
        ("rptSalesByProduct", "Monthly Orders per Product"),
        ("rptSalesByProductQuarterly", "Quarterly Orders per Product"),
    ):
        page = staff_client.get(reverse(SELECTION), {"report": name}).content.decode()
        assert f'id="selected-report-name">{title}</strong>' in page
        assert 'name="start" value="2024-02-29"' in page
        assert 'name="end" value="2024-05-31"' in page
    response = staff_client.get(
        reverse(SELECTION),
        {"report": "rptProductCatalog"},
        headers={"HX-Request": "true"},
    )
    page = response.content.decode()
    assert 'id="selected-report-name">Fall Catalog</strong>' in page
    assert 'name="start"' not in page
    assert 'name="end"' not in page
    assert services.report_selection("rptProductCatalog").period is None
    # the start may not come after the end
    with pytest.raises(ValidationError, match="R-reports-002"):
        services.sales_report_period(dt.date(2024, 3, 1), dt.date(2024, 2, 1))


def test_report_period_defaults_to_three_months_before_the_latest_order(latest_may):
    """R-reports-003: without the selection page the period runs from three calendar
    months before the latest order's date to that date, both at midnight; entered
    dates win; with no order there is no default."""
    assert services.sales_report_period() == period(at(2024, 2, 29), at(2024, 5, 31))
    assert services.sales_report_period(
        dt.date(2024, 1, 1),
        dt.date(2024, 1, 31),
    ) == period(at(2024, 1, 1), at(2024, 1, 31))
    # a date left out takes its default
    assert services.sales_report_period(start=dt.date(2024, 4, 1)) == period(
        at(2024, 4, 1),
        at(2024, 5, 31),
    )
    # the unit runs without the page: the default period holds the 29 Feb order (2 x
    # 10 = 20) and the 2 Apr order (5); the 31 May 15:00 order is after the end at
    # midnight and the 28 Feb order before the start
    rows = run_saved_query("qryrptSalesByEmployee", {})
    assert [(row[1], row[3]) for row in rows] == [(20.0, "Feb-2024"), (5.0, "Apr-2024")]


def test_no_orders_means_no_default_period():
    """R-reports-003: with no order in the database the default period cannot be
    derived; the refusal names the rule."""
    with pytest.raises(ValidationError, match="R-reports-003"):
        services.sales_report_period()
    selection = services.report_selection()
    assert selection.period is None
    assert "R-reports-003" in selection.problem


# ---------------------------------------------------------------- sales queries


def test_sales_per_employee_sum_order_totals_per_month():
    """R-reports-004: per salesperson and month, the sum of the order totals of the
    orders between the start and end (inclusive, against the full date and time);
    every status counts; an order without lines adds nothing."""
    ada = EmployeeFactory(first_name="Ada", last_name="Example")
    bob = EmployeeFactory(first_name="Bob", last_name="Sample")
    p1, p2 = ProductFactory(), ProductFactory()
    # January, Ada: 3 x 4 x 0.75 + 2 x 2.5 = 14, and a closed order 1 x 10 x 0.5 = 5
    sale(ada, at(2024, 1, 5, 10), (p1, 3, "4.00", 0.25), (p2, 2, "2.50", 0.0))
    sale(
        ada,
        at(2024, 1, 20),
        (p1, 1, "10.00", 0.5),
        order_status=OrderStatusFactory(order_status_id=OrderStatusCode.CLOSED),
    )
    # February, Ada: an order without lines, so the month has no total
    sale(ada, at(2024, 2, 10))
    # March, Ada: on the end date at midnight (counted) and later that day (not)
    sale(ada, at(2024, 3, 31), (p1, 1, "8.00", 0.0))
    sale(ada, at(2024, 3, 31, 9), (p1, 1, "50.00", 0.0))
    # January, Bob: 4 x 1.25 = 5
    sale(bob, at(2024, 1, 15), (p2, 4, "1.25", 0.0))
    rows = saved_queries.sales_by_employee(period(at(2024, 1, 1), at(2024, 3, 31)))
    assert rows_of(rows) == [
        ("Ada Example", "Jan-2024", 19.0),
        ("Bob Sample", "Jan-2024", 5.0),
        ("Ada Example", "Feb-2024", None),
        ("Ada Example", "Mar-2024", 8.0),
    ]
    assert [(row.series_id, row.month_year_sort) for row in rows][:2] == [
        (ada.pk, "2024-01"),
        (bob.pk, "2024-01"),
    ]


def test_sales_per_product_per_month():
    """R-reports-005: per product and month, the sum of quantity x unit price x (1 -
    discount) of the lines of the orders in the period; a line without a discount
    has no amount."""
    seller = EmployeeFactory()
    apple = ProductFactory(product_name="Apple")
    pear = ProductFactory(product_name="Pear")
    # January: Apple 2 x 10 x 0.75 = 15 and 1 x 10 = 10, so 25; Pear 1 x 4 = 4
    sale(seller, at(2024, 1, 3), (apple, 2, "10.00", 0.25), (pear, 1, "4.00", 0.0))
    sale(seller, at(2024, 1, 30, 17), (apple, 1, "10.00", 0.0))
    # February: Apple 3 x 10 x 0.5 = 15; Pear with a blank discount
    sale(seller, at(2024, 2, 1), (apple, 3, "10.00", 0.5), (pear, 1, "4.00", None))
    # March is outside the period
    sale(seller, at(2024, 3, 1), (apple, 5, "10.00", 0.0))
    rows = saved_queries.sales_by_product_by_month(
        period(at(2024, 1, 1), at(2024, 2, 29)),
    )
    assert rows_of(rows) == [
        ("Apple", "Jan-2024", 25.0),
        ("Pear", "Jan-2024", 4.0),
        ("Apple", "Feb-2024", 15.0),
        ("Pear", "Feb-2024", None),
    ]
    assert rows[0].month_year_sort == "2024-01"


def test_sales_per_product_per_quarter():
    """R-reports-006: the same line amounts per product and calendar quarter,
    labelled quarter number, a dash and the year."""
    seller = EmployeeFactory()
    apple = ProductFactory(product_name="Apple")
    # Q4 2023: 1 x 10 + 2 x 10 = 30; Q1 2024: 10; Q2 2024: 1 x 10 x 0.5 = 5
    sale(seller, at(2023, 11, 10), (apple, 1, "10.00", 0.0))
    sale(seller, at(2023, 12, 1), (apple, 2, "10.00", 0.0))
    sale(seller, at(2024, 2, 1), (apple, 1, "10.00", 0.0))
    sale(seller, at(2024, 4, 15), (apple, 1, "10.00", 0.5))
    rows = saved_queries.sales_by_product_by_quarter(
        period(at(2023, 11, 1), at(2024, 4, 30)),
    )
    assert rows_of(rows) == [
        ("Apple", "4-2023", 30.0),
        ("Apple", "1-2024", 10.0),
        ("Apple", "2-2024", 5.0),
    ]


# ---------------------------------------------------------------- sales reports


def test_sales_reports_print_their_period(staff_client, latest_may):
    """R-reports-007: each sales report prints the order-date range of the start and
    end dates chosen on the selection page in its header."""
    query = {"start": "2024-01-01", "end": "2024-04-30"}
    for name in services.SALES_REPORTS:
        response = staff_client.get(reverse(f"reports:report_{name}"), query)
        assert response.status_code == HTTPStatus.OK
        assert "Order dates between 1/1/2024 and 4/30/2024" in response.content.decode()
    report = services.sales_report(
        "rptSalesByProduct",
        services.sales_report_period(dt.date(2024, 1, 1), dt.date(2024, 4, 30)),
    )
    assert report.period.caption == "Order dates between 1/1/2024 and 4/30/2024"


def test_sales_report_without_data_does_not_open(staff_client, latest_may):
    """R-reports-008: a sales report with no order in the period tells the user it
    has no data and does not open."""
    StringFactory(string_id=services.NO_DATA_TEXT, string_data="Nothing to show.")
    empty = period(at(2020, 1, 1), at(2020, 12, 31))
    for name in services.SALES_REPORTS:
        with pytest.raises(ValidationError, match=r"R-reports-008: Nothing to show\."):
            services.sales_report(name, empty)
        response = staff_client.get(
            reverse(f"reports:report_{name}"),
            {"start": "2020-01-01", "end": "2020-12-31"},
            follow=True,
        )
        assert response.redirect_chain[0][0].startswith(reverse(SELECTION))
        assert "R-reports-008: Nothing to show." in response.content.decode()
        # back on the selection page, with the same report chosen
        assert response.context["selection"].report.name == name


def test_sales_per_employee_filters_by_salesperson(staff_client):
    """R-reports-009: the interactive report lists the salespeople of the report plus
    the all-employees entry; picking one limits the rows, totals and chart, and the
    all-employees entry removes the limit."""
    ada = EmployeeFactory(first_name="Ada", last_name="Example")
    bob = EmployeeFactory(first_name="Bob", last_name="Sample")
    EmployeeFactory(first_name="Cy", last_name="Absent")  # no orders in the period
    product = ProductFactory()
    sale(ada, at(2024, 1, 5), (product, 1, "10.00", 0.0))
    sale(bob, at(2024, 1, 6), (product, 2, "10.00", 0.0))
    sale(bob, at(2024, 2, 6), (product, 3, "10.00", 0.0))
    span = period(at(2024, 1, 1), at(2024, 2, 29))
    everyone = services.sales_report("rptSalesByEmployee", span)
    assert everyone.employees == [
        (0, "<All Employees>"),
        (ada.pk, "Ada Example"),
        (bob.pk, "Bob Sample"),
    ]
    assert everyone.grand_total == 60.0
    assert [dataset["label"] for dataset in everyone.chart["datasets"]] == [
        "Ada Example",
        "Bob Sample",
    ]
    only_bob = services.sales_report("rptSalesByEmployee", span, employee_id=bob.pk)
    assert [row.series_name for row in only_bob.rows] == ["Bob Sample", "Bob Sample"]
    assert only_bob.grand_total == 50.0
    assert [group.subtotal for group in only_bob.groups] == [20.0, 30.0]
    assert only_bob.chart["datasets"] == [{"label": "Bob Sample", "data": [20.0, 30.0]}]
    assert only_bob.employees == everyone.employees
    all_again = services.sales_report("rptSalesByEmployee", span, employee_id=0)
    assert all_again.grand_total == 60.0
    # the screen: the list and the filtered body
    response = staff_client.get(
        reverse("reports:report_rptSalesByEmployee"),
        {"start": "2024-01-01", "end": "2024-02-29", "employee": bob.pk},
    )
    page = response.content.decode()
    assert "&lt;All Employees&gt;" in page
    assert f'<option value="{bob.pk}" selected>Bob Sample</option>' in page
    assert "Ada Example</td>" not in page


def test_product_reports_total_each_period_and_chart_monthly(staff_client):
    """R-reports-010: the product reports show each product's sales per period, a
    subtotal per month or quarter, a grand total and a chart; the quarterly report
    sorts quarters by year, then quarter, and charts the monthly figures; every
    sales report shows when it was produced and page n of m."""
    seller = EmployeeFactory()
    apple = ProductFactory(product_name="Apple")
    pear = ProductFactory(product_name="Pear")
    sale(seller, at(2023, 11, 10), (apple, 1, "10.00", 0.0), (pear, 2, "5.00", 0.0))
    sale(seller, at(2023, 12, 1), (apple, 2, "10.00", 0.0))
    sale(seller, at(2024, 2, 1), (pear, 1, "4.00", 0.0))
    span = period(at(2023, 11, 1), at(2024, 2, 29))
    monthly = services.sales_report("rptSalesByProduct", span)
    # Nov: 10 + 10 = 20; Dec: 20; Feb: 4; in all 44
    assert [(group.label, group.subtotal) for group in monthly.groups] == [
        ("Nov-2023", 20.0),
        ("Dec-2023", 20.0),
        ("Feb-2024", 4.0),
    ]
    assert monthly.grand_total == 44.0
    assert monthly.chart == {
        "labels": ["Nov-2023", "Dec-2023", "Feb-2024"],
        "datasets": [
            {"label": "Apple", "data": [10.0, 20.0, None]},
            {"label": "Pear", "data": [10.0, None, 4.0]},
        ],
    }
    quarterly = services.sales_report("rptSalesByProductQuarterly", span)
    # Q4 2023 comes before Q1 2024, although its label sorts after it
    assert [(group.label, group.subtotal) for group in quarterly.groups] == [
        ("4-2023", 40.0),
        ("1-2024", 4.0),
    ]
    assert quarterly.grand_total == 44.0
    assert quarterly.chart == monthly.chart
    # produced time on the page, page n of m in the page footer of print and PDF
    response = staff_client.get(
        reverse("reports:report_rptSalesByProductQuarterly"),
        {"start": "2023-11-01", "end": "2024-02-29"},
    )
    page = response.content.decode()
    assert "Total Orders for 4-2023" in page
    assert "Grand Total" in page
    assert 'data-chart="sales-chart-data"' in page
    assert '<p class="report-footer">Produced ' in page
    stylesheet = finders.find("reports/reports.css")
    with open(stylesheet, encoding="utf-8") as css:  # noqa: PTH123
        assert 'content: "Page " counter(page) " of " counter(pages);' in css.read()
    pdf = staff_client.get(
        reverse("reports:report_rptSalesByProduct"),
        {"start": "2023-11-01", "end": "2024-02-29", "format": "pdf"},
    )
    assert pdf.content.startswith(b"%PDF-")


# ---------------------------------------------------------------- the catalog


def test_catalog_lists_every_product_with_lifetime_sales():
    """R-reports-011: lifetime sales are the sum of all of a product's line amounts,
    whatever the date or status; the catalog lists every product of a category with
    its category, name, id, quantity per unit, unit price and lifetime sales, and a
    product never sold has none."""
    seller = EmployeeFactory()
    drinks = ProductCategoryFactory(product_category_name="Drinks")
    tea = ProductFactory(
        product_name="Tea",
        product_category=drinks,
        quantity_per_unit="20 bags",
    )
    water = ProductFactory(product_name="Water", product_category=drinks)
    # Tea: 2 x 4 in 2020 (closed) and 3 x 4 x 0.5 in 2024: 8 + 6 = 14
    sale(
        seller,
        at(2020, 6, 1),
        (tea, 2, "4.00", 0.0),
        order_status=OrderStatusFactory(order_status_id=OrderStatusCode.CLOSED),
    )
    sale(seller, at(2024, 6, 1), (tea, 3, "4.00", 0.5))
    assert saved_queries.lifetime_sales_by_product() == [(tea.pk, 14.0)]
    rows = saved_queries.catalog_rows()
    assert [(r.category_name, r.product_name, r.total_sales) for r in rows] == [
        ("Drinks", "Tea", 14.0),
        ("Drinks", "Water", None),
    ]
    unit = sorted(run_saved_query("qryrptProductCatalog", {}), key=lambda row: row[4])
    assert unit[0][:5] == (
        drinks.pk,
        "Drinks",
        drinks.product_category_code,
        "Tea",
        tea.pk,
    )
    assert unit[0][5:8] == ("20 bags", tea.unit_price, 14.0)
    assert unit[1][4] == water.pk
    assert unit[1][7] is None


def test_catalog_category_header_figures():
    """R-reports-012: each category section shows its description, an image, the
    number of priced items, the lowest and highest unit price and the total
    lifetime sales of its products, then the product list."""
    seller = EmployeeFactory()
    drinks = ProductCategoryFactory(
        product_category_name="Drinks",
        product_category_desc="Things to drink",
    )
    tea = ProductFactory(product_name="Tea", product_category=drinks, unit_price="4.00")
    coffee = ProductFactory(
        product_name="Coffee",
        product_category=drinks,
        unit_price="6.50",
    )
    ProductFactory(product_name="Water", product_category=drinks, unit_price="1.25")
    # Tea 2 x 4 = 8, Coffee 1 x 6.5 = 6.5, Water never sold: 14.5
    sale(seller, at(2024, 1, 2), (tea, 2, "4.00", 0.0), (coffee, 1, "6.50", 0.0))
    catalog = services.product_catalog()
    (section,) = catalog.sections
    assert section.name == "Drinks"
    assert section.description == "Things to drink"
    assert section.item_count == 3
    assert str(section.lowest_price) == "1.2500"
    assert str(section.highest_price) == "6.5000"
    assert section.total_sales == 14.5
    assert [product.product_name for product in section.products] == [
        "Coffee",
        "Tea",
        "Water",
    ]


def test_catalog_pdf_builds_its_table_of_contents(staff_client):
    """R-reports-013: the catalog is rendered in full to PDF to record the page on
    which each category starts, then rendered again with that table of contents;
    until a PDF has been generated the preview shows a note asking for it."""
    catalog_texts()
    house_company()
    for name in ("Beverages", "Condiments"):
        category = ProductCategoryFactory(product_category_name=name)
        ProductFactory(product_category=category)
    result = services.product_catalog_pdf()
    assert result.pdf.startswith(b"%PDF-")
    assert [entry.title for entry in result.toc] == ["Beverages", "Condiments"]
    first, second = (entry.page for entry in result.toc)
    # cover, gastronomic page and contents come first; each category starts a page
    assert first >= 4
    assert second == first + 1
    url = reverse("reports:report_rptProductCatalog")
    before = staff_client.get(url).content.decode()
    assert 'id="toc-note"' in before
    assert staff_client.get(url, {"format": "pdf"}).content.startswith(b"%PDF-")
    after = staff_client.get(url).content.decode()
    assert 'id="toc-note"' not in after
    assert f'<td class="toc-page">{first}</td>' in after


def test_catalog_fixed_pages_and_order_form(staff_client):
    """R-reports-014: the catalog has the quality statement and the gastronomic
    introduction from the maintained texts, and an order form with the house
    company's address and business phone and a tick-box list of the shippers."""
    catalog_texts()
    house_company()
    ShipperFactory(company_name="Fast Freight")
    ShipperFactory(company_name="Air Cargo")
    ProductFactory()
    catalog = services.product_catalog()
    assert (catalog.quality_header, catalog.quality_text) == (
        "Quality header",
        "Quality text",
    )
    assert (catalog.gastronomic_header, catalog.gastronomic_text) == (
        "Gastronomic header",
        "Gastronomic text",
    )
    assert catalog.how_to_order == "How to order text"
    (company,) = catalog.house_companies
    assert company.address == "1 Main Street, Sampletown, WA  98000"
    assert company.business_phone == "(555) 555-0100"
    assert catalog.shippers == ["Air Cargo", "Fast Freight"]
    page = staff_client.get(reverse("reports:report_srptOrderForm")).content.decode()
    assert "1 Main Street, Sampletown, WA  98000" in page
    assert '<span class="tick-box"></span>Fast Freight' in page


def test_catalog_without_products_still_opens(staff_client):
    """R-reports-015: a catalog without rows tells the user that it has no data but
    still opens."""
    catalog = services.product_catalog()
    assert catalog.sections == []
    assert catalog.no_data.startswith("R-reports-015")
    response = staff_client.get(reverse("reports:report_rptProductCatalog"))
    assert response.status_code == HTTPStatus.OK
    assert "R-reports-015" in response.content.decode()
    pdf = staff_client.get(
        reverse("reports:report_rptProductCatalog"),
        {"format": "pdf"},
    )
    assert pdf.content.startswith(b"%PDF-")


def test_reports_menu_entry_and_preview(staff_client, latest_may):
    """R-reports-016: the main menu has a Reports entry that opens the selection page;
    Preview opens the sales per employee report in its interactive view and the
    other reports as print previews that can be saved as PDF."""
    config = apps.get_app_config("reports")
    assert config.feature is True
    assert config.nav_label == "Sales and Catalog Reports"
    assert reverse(SELECTION) == "/reports/"
    page = staff_client.get("/reports/").content.decode()
    assert 'action="/reports/sales-by-employee/"' in page
    assert 'name="format" value="pdf"' not in page  # interactive: no PDF button
    for name in (
        "rptSalesByProduct",
        "rptSalesByProductQuarterly",
        "rptProductCatalog",
    ):
        page = staff_client.get("/reports/", {"report": name}).content.decode()
        assert f'action="{views.report_url(name)}"' in page
        assert 'name="format" value="pdf"' in page
    response = staff_client.get(views.report_url("rptSalesByEmployee"))
    assert response.status_code == HTTPStatus.OK
    assert 'id="id_employee"' in response.content.decode()
