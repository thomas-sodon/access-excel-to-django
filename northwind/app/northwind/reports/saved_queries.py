"""Equivalence units of the Sales and Catalog Reports area (docs/contracts.md#harness).

Registers exactly the unit ids of goldens/manifest.json whose area is reports. Each
unit is a thin wrapper over a query function that the reports and services use too,
so the screens and the units share one copy of every query. Everything is computed
from the database through the ORM and the domain functions (domain/README.md):
line amounts and order totals from domain.sales, the salesperson's full name from
domain.people. Nothing here reads golden files or depends on the dataset.

The sales units take no parameters (goldens/params.json has none for them): the
original's report parameter functions fall back to the default period when the
report selection page is closed (R-reports-003), and so do these units.

Portability: no raw SQL. Sums group the order lines (SQL Server refuses an aggregate
over the order-total subquery, domain/sales.py); dates are split with ExtractYear,
ExtractMonth and ExtractQuarter, which both databases support.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import FloatField
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.db.models.functions import ExtractQuarter
from django.db.models.functions import ExtractYear

from northwind.core import vbacompat
from northwind.core.saved_queries import saved_query
from northwind.domain.people import full_name_expression
from northwind.domain.sales import line_amount_expression
from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Product

from .period import Period
from .period import default_period

if TYPE_CHECKING:
    from decimal import Decimal


def _first_of(year: int, month: int) -> dt.datetime:
    return dt.datetime(year, month, 1)  # noqa: DTZ001 (the app runs with USE_TZ False)


@dataclass(frozen=True)
class SalesRow:
    """One row of a sales report query: a salesperson or product in one period.

    `period_key` sorts periods by year, then month or quarter; `total` is None when
    no line of the group has an amount (an order without lines, R-reports-004)."""

    series_id: int
    series_name: str
    period_key: tuple[int, int]
    period_label: str
    total: float | None

    @property
    def month_year_sort(self) -> str:
        """Format(OrderDate, "yyyy-mm") of a monthly row."""
        return vbacompat.format_(_first_of(*self.period_key), "yyyy-mm")


@dataclass(frozen=True)
class CatalogRow:
    """One product of the catalog query (R-reports-011)."""

    category_id: int
    category_name: str
    category_code: str
    product_name: str
    product_id: int
    quantity_per_unit: str | None
    unit_price: Decimal | None
    total_sales: float | None
    category_desc: str | None
    # ProductCategories.ProductCategoryImage is an attachment column, which neither
    # the models nor the datasets carry (S4.models), so it is always blank here.
    category_image: str | None = None

    def as_tuple(self) -> tuple:
        return (
            self.category_id,
            self.category_name,
            self.category_code,
            self.product_name,
            self.product_id,
            self.quantity_per_unit,
            self.unit_price,
            self.total_sales,
            self.category_desc,
            self.category_image,
        )


def month_label(year: int, month: int) -> str:
    """Format(OrderDate, "mmm-yyyy"): abbreviated month name and year."""
    return vbacompat.format_(_first_of(year, month), "mmm-yyyy")


def quarter_label(year: int, quarter: int) -> str:
    """DatePart("q", OrderDate) & "-" & Format(OrderDate, "yyyy")."""
    year_text = vbacompat.format_(_first_of(year, 3 * (quarter - 1) + 1), "yyyy")
    return f"{quarter}-{year_text}"


def _in_period(period: Period, prefix: str = "") -> dict[str, dt.datetime]:
    """Order date between the period's bounds, inclusive, full date and time."""
    return {
        f"{prefix}order_date__gte": period.start,
        f"{prefix}order_date__lte": period.end,
    }


# ------------------------------------------------------------ lifetime sales


def lifetime_sales_by_product() -> list[tuple[int, float | None]]:
    """R-reports-011: every product with order lines and the sum of its line amounts,
    no date or status filter (the original's total sales by product query)."""
    rows = (
        OrderDetail.objects.order_by()
        .values("product_id")
        .annotate(total_sales=Sum(line_amount_expression()))
        .values_list("product_id", "total_sales")
    )
    return [(product_id, total) for product_id, total in rows]


def catalog_rows() -> list[CatalogRow]:
    """R-reports-011: every product of a category with its category, name, id,
    quantity per unit, unit price and lifetime sales (blank when never sold), sorted
    as the catalog prints them: category name, then product name."""
    lifetime = (
        OrderDetail.objects.filter(product_id=OuterRef("pk"))
        .order_by()
        .values("product_id")
        .annotate(total=Sum(line_amount_expression()))
        .values("total")
    )
    rows = (
        Product.objects.annotate(
            lifetime_sales=Subquery(lifetime, output_field=FloatField()),
        )
        .order_by(
            "product_category__product_category_name",
            "product_name",
            "product_id",
        )
        .values_list(
            "product_category_id",
            "product_category__product_category_name",
            "product_category__product_category_code",
            "product_name",
            "product_id",
            "quantity_per_unit",
            "unit_price",
            "lifetime_sales",
            "product_category__product_category_desc",
        )
    )
    return [CatalogRow(*row) for row in rows]


# ------------------------------------------------------------ sales per period


def sales_by_employee(period: Period) -> list[SalesRow]:
    """R-reports-004: per salesperson and calendar month, the sum of the order totals
    of their orders in the period; orders of every status count and an order without
    lines adds nothing (its group still appears, with no total when it has no other
    order). The orders are joined to their lines (a left join) and the line amounts
    summed per group, which equals the sum of the order totals."""
    rows = (
        Order.objects.filter(**_in_period(period))
        .annotate(
            year=ExtractYear("order_date"),
            month=ExtractMonth("order_date"),
            full_name=full_name_expression("employee__"),
        )
        .values("employee_id", "full_name", "year", "month")
        .annotate(total=Sum(line_amount_expression("lines__")))
        .order_by("year", "month", "full_name", "employee_id")
    )
    return [
        SalesRow(
            series_id=row["employee_id"],
            series_name=row["full_name"],
            period_key=(row["year"], row["month"]),
            period_label=month_label(row["year"], row["month"]),
            total=row["total"],
        )
        for row in rows
    ]


def _product_sales(period: Period, part: str) -> list[dict]:
    extract = {"month": ExtractMonth, "quarter": ExtractQuarter}[part]
    return list(
        OrderDetail.objects.filter(**_in_period(period, "order__"))
        .annotate(
            year=ExtractYear("order__order_date"),
            part=extract("order__order_date"),
        )
        .values("product__product_name", "product_id", "year", "part")
        .annotate(total=Sum(line_amount_expression()))
        .order_by("year", "part", "product__product_name", "product_id"),
    )


def sales_by_product_by_month(period: Period) -> list[SalesRow]:
    """R-reports-005: per product and calendar month, the sum of the line amounts of
    the orders in the period (every status)."""
    return [
        SalesRow(
            series_id=row["product_id"],
            series_name=row["product__product_name"],
            period_key=(row["year"], row["part"]),
            period_label=month_label(row["year"], row["part"]),
            total=row["total"],
        )
        for row in _product_sales(period, "month")
    ]


def sales_by_product_by_quarter(period: Period) -> list[SalesRow]:
    """R-reports-006: the same line amounts per product and calendar quarter,
    labelled quarter number, a dash and the year; sorted by year, then quarter
    (R-reports-010)."""
    return [
        SalesRow(
            series_id=row["product_id"],
            series_name=row["product__product_name"],
            period_key=(row["year"], row["part"]),
            period_label=quarter_label(row["year"], row["part"]),
            total=row["total"],
        )
        for row in _product_sales(period, "quarter")
    ]


# ------------------------------------------------------------ registered units


@saved_query("qryTotalSalesByProduct")
def qry_total_sales_by_product(params: dict[str, str]) -> list[tuple]:
    """ProductID, TotalSales (R-reports-011)."""
    return lifetime_sales_by_product()


@saved_query("qryrptProductCatalog")
def qryrpt_product_catalog(params: dict[str, str]) -> list[tuple]:
    """The catalog's record source (R-reports-011)."""
    return [row.as_tuple() for row in catalog_rows()]


@saved_query("qryrptSalesByEmployee")
def qryrpt_sales_by_employee(params: dict[str, str]) -> list[tuple]:
    """EmployeeID, OrderTotal, FullNameFNLN, MonthYear, MonthYearSort over the default
    period (R-reports-003, R-reports-004)."""
    return [
        (
            row.series_id,
            row.total,
            row.series_name,
            row.period_label,
            row.month_year_sort,
        )
        for row in sales_by_employee(default_period())
    ]


@saved_query("qryrptSalesByProduct_ByMonth")
def qryrpt_sales_by_product_by_month(params: dict[str, str]) -> list[tuple]:
    """ProductName, ProductID, MonthYear, MonthYearSort, OrderTotal over the default
    period (R-reports-003, R-reports-005)."""
    return [
        (
            row.series_name,
            row.series_id,
            row.period_label,
            row.month_year_sort,
            row.total,
        )
        for row in sales_by_product_by_month(default_period())
    ]


@saved_query("qryrptSalesByProduct_ByQuarter")
def qryrpt_sales_by_product_by_quarter(params: dict[str, str]) -> list[tuple]:
    """ProductName, ProductID, QuarterYear, OrderTotal over the default period
    (R-reports-003, R-reports-006)."""
    return [
        (row.series_name, row.series_id, row.period_label, row.total)
        for row in sales_by_product_by_quarter(default_period())
    ]
