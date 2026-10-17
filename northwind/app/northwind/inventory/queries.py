"""Querysets behind the area's saved queries, shared by saved_queries.py (the
equivalence units), the screens (views.py) and the export (reports/).

Each function returns a queryset; the saved query unit takes the manifest's columns
from it with values_list, and a screen filters it to one product. So a screen and its
unit always agree, and no screen keeps its own copy of the query. The stock figures
come from domain.inventory (R-inventory-001 to R-inventory-006).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import DecimalField
from django.db.models import ExpressionWrapper
from django.db.models import F
from django.db.models import Sum

from northwind.domain import inventory as stock
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Product
from northwind.legacy.models import ProductCategory
from northwind.legacy.models import ProductVendor
from northwind.legacy.models import PurchaseOrderDetail
from northwind.legacy.models import StockTake

if TYPE_CHECKING:
    from django.db.models import QuerySet

MONEY = DecimalField(max_digits=19, decimal_places=4)

#: The first row of the category filter on order lines (R-inventory-027).
ALL_CATEGORIES_ID = 0
ALL_CATEGORIES_LABEL = "<All>"


def _money_product(quantity: str, amount: str) -> ExpressionWrapper:
    """quantity x amount, computed in the database as a Currency value."""
    return ExpressionWrapper(F(quantity) * F(amount), output_field=MONEY)


def product_list(queryset: QuerySet | None = None) -> QuerySet:
    """qryProductList: every product with its category and its calculated no-stock,
    allocated, to-sell and on-order quantities (R-inventory-023); also carries the
    suggested reorder quantity for the screens (R-inventory-006)."""
    if queryset is None:
        queryset = Product.objects.all()
    return stock.with_stock_levels(queryset.select_related("product_category"))


def product_list_export() -> QuerySet:
    """qryProductList_Export: the product list's export columns, sorted by name
    (R-inventory-024)."""
    return product_list().order_by("product_name", "product_id")


def product_orders(product: Product | int | None = None) -> QuerySet:
    """qryProductOrders: order lines with order number and date, quantity, unit
    price, extended price and the order and line status names (R-inventory-025)."""
    rows = OrderDetail.objects.select_related(
        "order",
        "order__order_status",
        "order_detail_status",
    ).annotate(extended_price=_money_product("quantity", "unit_price"))
    if product is not None:
        rows = rows.filter(product=product)
    return rows.order_by("-order__order_date", "-order_id")


def product_purchase_orders(product: Product | int | None = None) -> QuerySet:
    """qryProductPurchaseOrder: purchase-order lines with number, status, quantity,
    unit cost, extended cost, vendor, submitted and received dates, ordered by the
    status's sort order and then the submitted date (R-inventory-026)."""
    rows = PurchaseOrderDetail.objects.select_related(
        "purchase_order",
        "purchase_order__status",
        "purchase_order__vendor",
    ).annotate(extended_cost=_money_product("quantity", "unit_cost"))
    if product is not None:
        rows = rows.filter(product=product)
    return rows.order_by(
        "purchase_order__status__sort_order",
        F("purchase_order__submitted_date").asc(nulls_first=True),
        "purchase_order_id",
    )


def purchase_order_quantities_by_status() -> QuerySet:
    """qryPOProducts_ByStatus: total quantity per purchase order status and product
    (the on-order figure takes the Approved rows, R-inventory-004)."""
    return (
        PurchaseOrderDetail.objects.values("purchase_order__status_id", "product_id")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("purchase_order__status_id", "product_id")
    )


def product_vendors(product: Product | int | None = None) -> QuerySet:
    """qryProductVendors: a product's vendor links (R-inventory-029)."""
    rows = ProductVendor.objects.select_related("vendor")
    if product is not None:
        rows = rows.filter(product=product)
    return rows.order_by("vendor__company_name", "product_vendor_id")


def stock_takes(product: Product | int | None = None) -> QuerySet:
    """qryStockTake: a product's stock takes, latest first (R-inventory-009)."""
    rows = StockTake.objects.all()
    if product is not None:
        rows = rows.filter(product=product)
    return rows.order_by("-stock_take_date", "-stock_take_id")


def categories_by_name() -> QuerySet:
    """qrycboProductCategory: the category choices sorted by name."""
    return ProductCategory.objects.order_by("product_category_name", "pk")


def category_filter_choices() -> list[tuple[int, int, str]]:
    """qrycboProductCategories: an 'all categories' entry first, then every category
    by name, as (clause, category id, name) (R-inventory-027). The 'all' entry is
    there only when at least one category exists, as in the original."""
    categories = list(categories_by_name().values_list("pk", "product_category_name"))
    if not categories:
        return []
    return [
        (1, ALL_CATEGORIES_ID, ALL_CATEGORIES_LABEL),
        *((2, pk, name) for pk, name in categories),
    ]


def all_products_by_name() -> QuerySet:
    """qrycboProducts_All: every product sorted by name, discontinued ones included
    (R-inventory-027)."""
    return Product.objects.order_by("product_name", "pk")


def products_in_category(category_id: int | None) -> QuerySet:
    """qrycboProducts: the products of one category sorted by name; none for a blank
    category (R-inventory-027)."""
    if category_id is None:
        return Product.objects.none()
    return all_products_by_name().filter(product_category_id=category_id)


def product_choices(category_id: int | None = ALL_CATEGORIES_ID) -> QuerySet:
    """The product choices of an order line: every product for the 'all' entry,
    otherwise that category's products (R-inventory-027)."""
    if category_id == ALL_CATEGORIES_ID:
        return all_products_by_name()
    return products_in_category(category_id)
