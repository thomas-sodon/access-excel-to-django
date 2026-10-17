"""Querysets of the Purchasing and receiving area, shared by the saved queries
(saved_queries.py), the services (amounts) and the screens, so that a screen shows
exactly what its equivalence unit proves.

Every figure is an ORM expression that runs on PostgreSQL and SQL Server: the
extended cost is a correlated subquery (never a SUM over a subquery, which SQL
Server refuses), and the names of the submitter and approver use the domain's full
name expression (domain/people.py).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Case
from django.db.models import CharField
from django.db.models import DecimalField
from django.db.models import ExpressionWrapper
from django.db.models import F
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import Coalesce

from northwind.domain.people import full_name_expression
from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.models import Company
from northwind.legacy.models import Product
from northwind.legacy.models import ProductVendor
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail

if TYPE_CHECKING:
    from django.db.models import QuerySet

#: An Access Currency value: four decimal places.
MONEY = DecimalField(max_digits=19, decimal_places=4)
ZERO = Value(Decimal("0.0000"), output_field=MONEY)

EXTENDED_COST = "extended_cost"
TOTAL_COST = "total_cost"
STATUS_NAME = "status_name"
SUBMITTED_BY_NAME = "submitted_by_name"
APPROVED_BY_NAME = "approved_by_name"

#: The PurchaseOrders columns in table order (PurchaseOrders.* of the original).
PURCHASE_ORDER_COLUMNS = (
    "purchase_order_id",
    "vendor_id",
    "submitted_by_id",
    "submitted_date",
    "approved_by_id",
    "approved_date",
    "status_id",
    "received_date",
    "shipping_fee",
    "tax_amount",
    "payment_date",
    "payment_amount",
    "payment_method",
    "notes",
    "added_by",
    "added_on",
    "modified_by",
    "modified_on",
)

#: The PurchaseOrderDetails columns in table order.
LINE_COLUMNS = (
    "purchase_order_detail_id",
    "purchase_order_id",
    "product_id",
    "quantity",
    "unit_cost",
    "received_date",
    "added_by",
    "added_on",
    "modified_by",
    "modified_on",
)


def line_amount_expression(prefix: str = "") -> ExpressionWrapper:
    """Quantity times unit cost of one purchase order line (R-purchasing-010)."""
    return ExpressionWrapper(
        F(f"{prefix}quantity") * F(f"{prefix}unit_cost"),
        output_field=MONEY,
    )


def extended_cost_expression(ref: str = "pk") -> Subquery:
    """Sum of quantity times unit cost over the lines of the purchase order `ref`
    points at; NULL for a purchase order without lines (R-purchasing-024)."""
    totals = (
        PurchaseOrderDetail.objects.filter(purchase_order=OuterRef(ref))
        .order_by()
        .values("purchase_order")
        .annotate(total=Sum(line_amount_expression(), output_field=MONEY))
        .values("total")
    )
    return Subquery(totals, output_field=MONEY)


def employee_name_expression(relation: str) -> Case:
    """The full name (first then last) of the employee a nullable foreign key points
    at, NULL when it is blank, as the original's left join to its employee query."""
    return Case(
        When(**{f"{relation}__isnull": True}, then=Value(None)),
        default=full_name_expression(f"{relation}__"),
        output_field=CharField(),
    )


def with_extended_cost(queryset: QuerySet) -> QuerySet:
    """Annotate `extended_cost` (R-purchasing-024)."""
    return queryset.annotate(**{EXTENDED_COST: extended_cost_expression()})


def with_total_cost(queryset: QuerySet) -> QuerySet:
    """Annotate `extended_cost` and `total_cost` = extended cost + shipping fee + tax
    amount, each missing part counted as zero (R-purchasing-025)."""
    queryset = with_extended_cost(queryset)
    total = (
        Coalesce(F(EXTENDED_COST), ZERO, output_field=MONEY)
        + Coalesce(F("shipping_fee"), ZERO, output_field=MONEY)
        + Coalesce(F("tax_amount"), ZERO, output_field=MONEY)
    )
    return queryset.annotate(
        **{TOTAL_COST: ExpressionWrapper(total, output_field=MONEY)},
    )


def with_names(queryset: QuerySet) -> QuerySet:
    """Annotate the status name and the submitter's and approver's full names."""
    return queryset.annotate(
        **{
            STATUS_NAME: F("status__status_name"),
            SUBMITTED_BY_NAME: employee_name_expression("submitted_by"),
            APPROVED_BY_NAME: employee_name_expression("approved_by"),
        },
    )


def purchase_orders() -> QuerySet:
    """Every purchase order with its status and the submitter's and approver's names
    (the purchase order screen's record source, qryPurchaseOrder)."""
    return with_names(PurchaseOrder.objects.all())


def purchase_order_list() -> QuerySet:
    """The purchase order list (R-purchasing-025): purchase orders of vendor
    companies with their names and total cost, newest number first."""
    queryset = PurchaseOrder.objects.filter(
        vendor__company_type_id=CompanyTypeCode.VENDOR,
    ).select_related("vendor", "status")
    return with_total_cost(with_names(queryset)).order_by("-purchase_order_id")


def vendor_purchase_orders(vendor: Company | int | None = None) -> QuerySet:
    """The purchase orders on a vendor's company page (R-purchasing-026): only those
    with a submitter, with names and extended cost. Without a vendor, every vendor's
    rows (the saved query); with one, only that vendor's."""
    queryset = PurchaseOrder.objects.filter(submitted_by__isnull=False)
    if vendor is not None:
        vendor_id = vendor.pk if isinstance(vendor, Company) else int(vendor)
        queryset = queryset.filter(vendor_id=vendor_id)
    return with_extended_cost(with_names(queryset.select_related("status")))


def purchase_order_lines(purchase_order: PurchaseOrder | int | None = None) -> QuerySet:
    """Purchase order lines in entry order, optionally of one purchase order."""
    queryset = PurchaseOrderDetail.objects.order_by("purchase_order_detail_id")
    if purchase_order is not None:
        po_id = (
            purchase_order.pk
            if isinstance(purchase_order, PurchaseOrder)
            else int(purchase_order)
        )
        queryset = queryset.filter(purchase_order_id=po_id)
    return queryset


def vendors() -> QuerySet:
    """The vendor choices: companies of the vendor type by name (R-purchasing-017)."""
    return Company.objects.filter(company_type_id=CompanyTypeCode.VENDOR).order_by(
        "company_name",
        "company_id",
    )


def vendor_products(vendor: Company | int | None) -> QuerySet:
    """The products a vendor supplies (the product-vendor list), by product name
    (R-purchasing-016). No vendor gives no products."""
    if vendor is None:
        return Product.objects.none()
    vendor_id = vendor.pk if isinstance(vendor, Company) else int(vendor)
    return Product.objects.filter(vendor_links__vendor_id=vendor_id).order_by(
        "product_name",
        "product_id",
    )


def product_vendors(product: Product | int) -> QuerySet:
    """The vendors that supply one product, by company name (R-purchasing-023)."""
    product_id = product.pk if isinstance(product, Product) else int(product)
    vendor_ids = ProductVendor.objects.filter(product_id=product_id).values("vendor_id")
    return Company.objects.filter(pk__in=vendor_ids).order_by(
        "company_name",
        "company_id",
    )
