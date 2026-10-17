"""Services of the Sales and Catalog Reports area: one function per services[] entry of
analysis/interfaces.md for this area (sales_report_period, sales_report,
product_catalog_pdf), plus the read-only helpers the screens share.

The area only reads: it writes no table, so it has no write services and no data
macro side effects (the S4.models notes list none). A refused action raises
ValidationError with a plain message that names the rule id. The figures come from
the area's query functions (saved_queries.py), which use the domain functions for
line amounts, order totals and full names.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

from northwind.core import vbacompat
from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.models import Company
from northwind.legacy.models import String

from . import saved_queries
from .period import Period
from .period import as_midnight
from .period import default_period
from .reports import catalog as catalog_pdf

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable
    from decimal import Decimal

    from .saved_queries import CatalogRow
    from .saved_queries import SalesRow

# ------------------------------------------------------------ the report choices

SALES_BY_EMPLOYEE = "rptSalesByEmployee"
SALES_BY_PRODUCT = "rptSalesByProduct"
SALES_BY_PRODUCT_QUARTERLY = "rptSalesByProductQuarterly"
PRODUCT_CATALOG = "rptProductCatalog"

#: The report the selection page opens with (R-reports-001).
DEFAULT_REPORT = SALES_BY_EMPLOYEE

#: Strings table keys of the texts the reports print (the original's string enum).
NO_DATA_TEXT = 11
GASTRONOMIC_HEADER = 43
GASTRONOMIC_TEXT = 44
QUALITY_HEADER = 45
QUALITY_TEXT = 46
HOW_TO_ORDER_TEXT = 47

ALL_EMPLOYEES = (0, "<All Employees>")


@dataclass(frozen=True)
class ReportKind:
    """One report of the selection page (the original's report buttons)."""

    name: str
    title: str
    #: Whether the report takes the start and end dates (R-reports-002).
    takes_period: bool
    #: Opens in the interactive view (filter by salesperson, R-reports-009) rather
    #: than as a print preview (R-reports-016).
    interactive: bool
    #: Heading of the series column: the salesperson or the product.
    series_title: str = ""
    #: Heading of the period column.
    period_title: str = ""
    query: Callable[[Period], list[SalesRow]] | None = None
    #: The query that feeds the chart (the quarterly report charts the monthly
    #: figures, Q-reports-004).
    chart_query: Callable[[Period], list[SalesRow]] | None = None


REPORTS: dict[str, ReportKind] = {
    kind.name: kind
    for kind in (
        ReportKind(
            SALES_BY_EMPLOYEE,
            "Monthly Orders per Employee",
            takes_period=True,
            interactive=True,
            series_title="Employee",
            period_title="Month",
            query=saved_queries.sales_by_employee,
            chart_query=saved_queries.sales_by_employee,
        ),
        ReportKind(
            SALES_BY_PRODUCT,
            "Monthly Orders per Product",
            takes_period=True,
            interactive=False,
            series_title="Product",
            period_title="Month",
            query=saved_queries.sales_by_product_by_month,
            chart_query=saved_queries.sales_by_product_by_month,
        ),
        ReportKind(
            SALES_BY_PRODUCT_QUARTERLY,
            "Quarterly Orders per Product",
            takes_period=True,
            interactive=False,
            series_title="Product",
            period_title="Quarter",
            query=saved_queries.sales_by_product_by_quarter,
            chart_query=saved_queries.sales_by_product_by_month,
        ),
        ReportKind(
            PRODUCT_CATALOG,
            "Fall Catalog",
            takes_period=False,
            interactive=False,
        ),
    )
}
SALES_REPORTS = tuple(name for name, kind in REPORTS.items() if kind.takes_period)


def report_kind(name: str | None) -> ReportKind:
    """The report of that name; the default report when no name is given."""
    kind = REPORTS.get(name or DEFAULT_REPORT)
    if kind is None:
        msg = f"R-reports-016: there is no report called {name!r}."
        raise ValidationError(msg, code="R-reports-016")
    return kind


def maintained_text(string_id: int) -> str:
    """One of the application's maintained texts (the Strings table), blank when it
    is missing, as the original's GetString."""
    text = (
        String.objects.filter(pk=string_id)
        .values_list("string_data", flat=True)
        .first()
    )
    return text or ""


def sum_of(values: list[float | None]) -> float | None:
    """Access Sum(): blank values add nothing; no value at all gives a blank."""
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def produced_at() -> str:
    """The time a report was produced (=Now() in the report footer), as Access
    prints a date and time."""
    return vbacompat.format_(vbacompat.now(), "General Date")


# ------------------------------------------------------------ sales_report_period


def sales_report_period(
    start: dt.date | dt.datetime | None = None,
    end: dt.date | dt.datetime | None = None,
) -> Period:
    """R-reports-002, R-reports-003: the period of a sales report. A date entered on
    the selection page is used as its calendar date; a date left out takes the
    default: the end the date of the latest order, the start three calendar months
    before it. Refused when a default is needed but there is no order, or when the
    start is after the end."""
    default = default_period() if start is None or end is None else None
    first = as_midnight(start) if start is not None else default.start
    last = as_midnight(end) if end is not None else default.end
    if first > last:
        msg = "R-reports-002: the start date must not be after the end date."
        raise ValidationError(msg, code="R-reports-002")
    return Period(start=first, end=last)


@dataclass(frozen=True)
class Selection:
    """What the report selection page shows (R-reports-001, R-reports-002)."""

    report: ReportKind
    #: The date inputs and their values; None when the report takes no dates (the
    #: inputs are hidden and cleared) or when no default can be derived.
    period: Period | None
    #: Why the dates could not be filled in, if they could not.
    problem: str = ""


def report_selection(name: str | None = None) -> Selection:
    """The selection page for one report, as if the user had chosen it: a sales
    report shows the dates with their defaults, the catalog hides and clears them."""
    report = report_kind(name)
    if not report.takes_period:
        return Selection(report=report, period=None)
    try:
        return Selection(report=report, period=sales_report_period())
    except ValidationError as error:
        return Selection(report=report, period=None, problem=" ".join(error.messages))


# ------------------------------------------------------------ sales_report


@dataclass(frozen=True)
class PeriodGroup:
    """One month or quarter of a sales report with its subtotal (R-reports-010)."""

    label: str
    key: tuple[int, int]
    rows: list[SalesRow]
    subtotal: float | None


@dataclass(frozen=True)
class SeriesTotal:
    """A salesperson's or product's total over the period, for the printed chart."""

    name: str
    total: float | None
    share: float  # percent of the largest total, for the bar width


@dataclass(frozen=True)
class SalesReport:
    report: ReportKind
    period: Period
    rows: list[SalesRow]
    groups: list[PeriodGroup]
    grand_total: float | None
    #: Chart.js data: {"labels": [...], "datasets": [{"label", "data"}]}.
    chart: dict
    series_totals: list[SeriesTotal]
    #: The salesperson list of the interactive view, the all-employees entry first
    #: (R-reports-009); empty for the product reports.
    employees: list[tuple[int, str]] = field(default_factory=list)
    employee_id: int = 0
    produced_at: str = ""


def no_data_message(rule: str) -> str:
    """The original's no-data message (a maintained text), naming the rule."""
    text = maintained_text(NO_DATA_TEXT) or "There is no data for this report."
    return f"{rule}: {text}"


def _groups(rows: list[SalesRow]) -> list[PeriodGroup]:
    groups: dict[tuple[int, int], list[SalesRow]] = {}
    for row in rows:
        groups.setdefault(row.period_key, []).append(row)
    return [
        PeriodGroup(
            label=members[0].period_label,
            key=key,
            rows=members,
            subtotal=sum_of([row.total for row in members]),
        )
        for key, members in sorted(groups.items())
    ]


def _chart(rows: list[SalesRow]) -> dict:
    """Periods along the axis, one data set per salesperson or product."""
    periods = sorted({row.period_key: row.period_label for row in rows}.items())
    names = sorted({(row.series_name, row.series_id) for row in rows})
    values = {(row.series_id, row.period_key): row.total for row in rows}
    return {
        "labels": [label for _key, label in periods],
        "datasets": [
            {
                "label": name,
                "data": [values.get((series_id, key)) for key, _label in periods],
            }
            for name, series_id in names
        ],
    }


def _series_totals(rows: list[SalesRow]) -> list[SeriesTotal]:
    totals: dict[tuple[str, int], list[float | None]] = {}
    for row in rows:
        totals.setdefault((row.series_name, row.series_id), []).append(row.total)
    sums = {key: sum_of(values) for key, values in sorted(totals.items())}
    largest = max((abs(value) for value in sums.values() if value), default=0.0)
    return [
        SeriesTotal(
            name=name,
            total=total,
            share=round(100 * abs(total) / largest, 1) if total and largest else 0.0,
        )
        for (name, _series_id), total in sums.items()
    ]


def sales_report(
    name: str,
    period: Period,
    employee_id: int | None = None,
) -> SalesReport:
    """R-reports-004 to R-reports-010: the rows of one sales report for the period,
    grouped by month or quarter with subtotals, the grand total and the chart.

    The sales per employee report can be limited to one salesperson (R-reports-009):
    the list offers the salespeople of the report plus the all-employees entry (id
    0, no limit), and the limit applies to the rows, totals and chart. Refused, and
    the report not opened, when the period has no rows (R-reports-008)."""
    report = report_kind(name)
    if not report.takes_period or report.query is None:
        msg = f"R-reports-016: {report.title} is not a sales report."
        raise ValidationError(msg, code="R-reports-016")
    rows = report.query(period)
    if not rows:
        raise ValidationError(no_data_message("R-reports-008"), code="R-reports-008")
    chart_rows = (
        rows if report.chart_query is report.query else report.chart_query(period)
    )
    employees: list[tuple[int, str]] = []
    chosen = 0
    if report.interactive:
        people = sorted({(row.series_name, row.series_id) for row in rows})
        employees = [ALL_EMPLOYEES, *((pk, person) for person, pk in people)]
        chosen = int(employee_id or 0)
        if chosen:
            rows = [row for row in rows if row.series_id == chosen]
            chart_rows = [row for row in chart_rows if row.series_id == chosen]
    return SalesReport(
        report=report,
        period=period,
        rows=rows,
        groups=_groups(rows),
        grand_total=sum_of([row.total for row in rows]),
        chart=_chart(chart_rows),
        series_totals=_series_totals(chart_rows),
        employees=employees,
        employee_id=chosen,
        produced_at=produced_at(),
    )


# ------------------------------------------------------------ product_catalog_pdf


@dataclass(frozen=True)
class CategorySection:
    """One category of the catalog with its header figures (R-reports-012)."""

    category_id: int
    name: str
    description: str | None
    #: The category's stored image; the attachment column is not carried over
    #: (S4.models), so the section shows a placeholder.
    image: str | None
    item_count: int
    lowest_price: Decimal | None
    highest_price: Decimal | None
    total_sales: float | None
    products: list[CatalogRow]

    @property
    def anchor(self) -> str:
        return f"category-{self.category_id}"


@dataclass(frozen=True)
class HouseCompany:
    """The selling company of the order form (R-reports-014)."""

    name: str
    address: str
    business_phone: str | None


@dataclass(frozen=True)
class TocEntry:
    title: str
    page: int | None


@dataclass(frozen=True)
class Catalog:
    sections: list[CategorySection]
    quality_header: str
    quality_text: str
    gastronomic_header: str
    gastronomic_text: str
    how_to_order: str
    house_companies: list[HouseCompany]
    shippers: list[str]
    #: The table of contents of the last full generation; None when none has been
    #: generated yet (R-reports-013).
    toc: list[TocEntry] | None
    #: The no-data warning (R-reports-015); blank when the catalog has rows.
    no_data: str = ""
    produced_at: str = ""

    @property
    def title(self) -> str:
        names = [company.name for company in self.house_companies]
        return f"{names[0]} - Fall Catalog" if names else "Fall Catalog"


def _sections(rows: list[CatalogRow]) -> list[CategorySection]:
    by_category: dict[int, list[CatalogRow]] = {}
    for row in rows:
        by_category.setdefault(row.category_id, []).append(row)
    sections = []
    for category_id, products in by_category.items():
        first = products[0]
        prices = [row.unit_price for row in products if row.unit_price is not None]
        sections.append(
            CategorySection(
                category_id=category_id,
                name=first.category_name,
                description=first.category_desc,
                image=first.category_image,
                item_count=len(prices),
                lowest_price=min(prices) if prices else None,
                highest_price=max(prices) if prices else None,
                total_sales=sum_of([row.total_sales for row in products]),
                products=products,
            ),
        )
    return sections


def house_companies() -> list[HouseCompany]:
    """R-reports-014: the selling company, the company whose type is the house
    company type, with its address line and business phone."""
    companies = Company.objects.filter(
        company_type_id=CompanyTypeCode.OWN_COMPANY,
    ).order_by("company_id")
    return [
        HouseCompany(
            name=company.company_name,
            address=(
                f"{company.address or ''}, {company.city or ''}, "
                f"{company.state_id or ''}  {company.zip or ''}"
            ),
            business_phone=company.business_phone,
        )
        for company in companies
    ]


def shippers() -> list[str]:
    """R-reports-014: the shippers a customer can tick on the order form."""
    return list(
        Company.objects.filter(company_type_id=CompanyTypeCode.SHIPPER)
        .order_by("company_name", "company_id")
        .values_list("company_name", flat=True),
    )


def product_catalog(toc: list[TocEntry] | None = None) -> Catalog:
    """R-reports-011 to R-reports-015: the catalog's pages: the quality statement,
    the gastronomic introduction, the table of contents (`toc`, None when none has
    been generated), one section per category and the order form. A catalog
    without products still opens, with the no-data warning (R-reports-015)."""
    rows = saved_queries.catalog_rows()
    return Catalog(
        sections=_sections(rows),
        quality_header=maintained_text(QUALITY_HEADER),
        quality_text=maintained_text(QUALITY_TEXT),
        gastronomic_header=maintained_text(GASTRONOMIC_HEADER),
        gastronomic_text=maintained_text(GASTRONOMIC_TEXT),
        how_to_order=maintained_text(HOW_TO_ORDER_TEXT),
        house_companies=house_companies(),
        shippers=shippers(),
        toc=toc,
        no_data="" if rows else no_data_message("R-reports-015"),
        produced_at=produced_at(),
    )


@dataclass(frozen=True)
class CatalogPdf:
    pdf: bytes
    toc: list[TocEntry]
    no_data: str


def product_catalog_pdf() -> CatalogPdf:
    """R-reports-013: the catalog as an A4 PDF with a correct table of contents.

    Every generation starts without a table of contents (the previous one is
    discarded), renders the whole catalog once to find the page on which each
    category's section starts, then renders it again with those pages in the table
    of contents. The first pass lists the categories with blank pages, so both
    passes lay out the same pages. Nothing is stored (Q-reports-005); the caller
    may keep the returned table of contents for the HTML preview."""
    catalog = product_catalog(toc=None)
    placeholders = [TocEntry(section.name, None) for section in catalog.sections]
    first = catalog_pdf.render_document(replace(catalog, toc=placeholders))
    pages = catalog_pdf.anchor_pages(first)
    toc = [
        TocEntry(section.name, pages.get(section.anchor))
        for section in catalog.sections
    ]
    final = catalog_pdf.render_document(replace(catalog, toc=toc))
    return CatalogPdf(pdf=final.write_pdf(), toc=toc, no_data=catalog.no_data)
