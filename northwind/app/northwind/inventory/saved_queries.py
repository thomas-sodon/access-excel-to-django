"""Equivalence units of the Products and Inventory area (docs/contracts.md#harness).

One function per unit of goldens/manifest.json whose area is inventory, registered
with @saved_query("<unit id>"). Each takes the unit's parameters (goldens/params.json)
as canonical strings and returns one tuple per row with the manifest's columns in
order. The rows come from the database through queries.py (the querysets the screens
use too) and the domain's stock figures; nothing here reads golden files or depends
on the dataset. core.apps imports this module when Django starts.
"""

from __future__ import annotations

from northwind.core.saved_queries import saved_query

from . import queries

#: The category parameter of qrycboProducts (the order line's category filter).
CATEGORY_PARAM = "Form!cboProductCategories"


def _int_param(params: dict[str, str], name: str) -> int | None:
    """A long integer parameter; None when blank or missing (Access: = Null)."""
    raw = (params.get(name) or "").strip()
    if not raw or raw == "\\N":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@saved_query("qryPOProducts_ByStatus")
def qry_po_products_by_status(params: dict[str, str]) -> list[tuple]:
    """StatusID, ProductID, Quantity: purchase-order quantity per status and product
    (R-inventory-004)."""
    return list(
        queries.purchase_order_quantities_by_status().values_list(
            "purchase_order__status_id",
            "product_id",
            "total_quantity",
        ),
    )


@saved_query("qryProductCategories")
def qry_product_categories(params: dict[str, str]) -> list[tuple]:
    """Every column of the categories. The category image is an attachment the new
    app does not carry over (legacy.models), so it is always blank."""
    rows = queries.categories_by_name().values_list(
        "product_category_id",
        "product_category_name",
        "product_category_code",
        "product_category_desc",
        "added_by",
        "added_on",
        "modified_by",
        "modified_on",
    )
    return [(*row[:4], None, *row[4:]) for row in rows]


@saved_query("qryProductDetail")
def qry_product_detail(params: dict[str, str]) -> list[tuple]:
    """Every column of the products (the product page's record source)."""
    return list(
        queries.all_products_by_name().values_list(
            "product_id",
            "product_code",
            "product_name",
            "product_description",
            "standard_unit_cost",
            "unit_price",
            "reorder_level",
            "target_level",
            "quantity_per_unit",
            "discontinued",
            "minimum_reorder_quantity",
            "product_category_id",
            "added_by",
            "added_on",
            "modified_by",
            "modified_on",
        ),
    )


@saved_query("qryProductList")
def qry_product_list(params: dict[str, str]) -> list[tuple]:
    """The product list with its calculated quantities (R-inventory-023)."""
    return list(
        queries.product_list().values_list(
            "product_id",
            "product_category__product_category_name",
            "product_code",
            "product_name",
            "product_description",
            "standard_unit_cost",
            "product_no_stock",
            "product_allocated",
            "product_to_sell",
            "product_on_order",
            "minimum_reorder_quantity",
            "unit_price",
            "reorder_level",
            "target_level",
            "quantity_per_unit",
            "discontinued",
            "product_category_id",
            "added_by",
            "added_on",
            "modified_by",
            "modified_on",
        ),
    )


def product_list_export_rows() -> list[tuple]:
    """The rows of the product list export, sorted by product name
    (R-inventory-024); the xlsx download (reports/) writes exactly these."""
    rows = queries.product_list_export().values_list(
        "product_id",
        "product_code",
        "product_name",
        "product_allocated",
        "product_to_sell",
        "product_on_order",
        "reorder_level",
        "target_level",
        "minimum_reorder_quantity",
        "discontinued",
    )
    # The original converts the allocated quantity to a double.
    return [(*row[:3], float(row[3]), *row[4:]) for row in rows]


@saved_query("qryProductList_Export")
def qry_product_list_export(params: dict[str, str]) -> list[tuple]:
    """Product ID, Product Code, Product, Allocated Inventory, Inventory To Sell, Qty
    On Order, Reorder Level, Target Level, Min Reorder Qty, Discontinued
    (R-inventory-024)."""
    return product_list_export_rows()


@saved_query("qryProductOrders")
def qry_product_orders(params: dict[str, str]) -> list[tuple]:
    """Each order line with order number and date, quantity, unit price, extended
    price and the order and line status names (R-inventory-025)."""
    return list(
        queries.product_orders().values_list(
            "order_id",
            "product_id",
            "order__order_date",
            "quantity",
            "unit_price",
            "extended_price",
            "order__order_status__order_status_name",
            "order_detail_status__order_detail_status_name",
        ),
    )


@saved_query("qryProductPurchaseOrder")
def qry_product_purchase_order(params: dict[str, str]) -> list[tuple]:
    """Each purchase-order line with its status, quantity, unit and extended cost,
    vendor name, submitted and received dates (R-inventory-026)."""
    return list(
        queries.product_purchase_orders().values_list(
            "product_id",
            "purchase_order_id",
            "purchase_order__status_id",
            "purchase_order__status__status_name",
            "purchase_order__status__sort_order",
            "quantity",
            "unit_cost",
            "extended_cost",
            "purchase_order__vendor__company_name",
            "purchase_order__submitted_date",
            "received_date",
        ),
    )


@saved_query("qryProductVendors")
def qry_product_vendors(params: dict[str, str]) -> list[tuple]:
    """Every column of the product-vendor links (R-inventory-029)."""
    return list(
        queries.product_vendors().values_list(
            "product_vendor_id",
            "product_id",
            "vendor_id",
            "added_by",
            "added_on",
            "modified_by",
            "modified_on",
        ),
    )


@saved_query("qryStockTake")
def qry_stock_take(params: dict[str, str]) -> list[tuple]:
    """The stock takes (R-inventory-009)."""
    return list(
        queries.stock_takes().values_list(
            "stock_take_id",
            "stock_take_date",
            "product_id",
            "quantity_on_hand",
            "expected_quantity",
        ),
    )


@saved_query("qrycboProductCategories")
def qrycbo_product_categories(params: dict[str, str]) -> list[tuple]:
    """theClause, ProductCategoryID, ProductCategoryName: 'all categories' first,
    then every category by name (R-inventory-027)."""
    return queries.category_filter_choices()


@saved_query("qrycboProductCategory")
def qrycbo_product_category(params: dict[str, str]) -> list[tuple]:
    """ProductCategoryID, ProductCategoryName sorted by name."""
    return list(
        queries.categories_by_name().values_list(
            "product_category_id",
            "product_category_name",
        ),
    )


PRODUCT_CHOICE_COLUMNS = (
    "product_id",
    "product_name",
    "unit_price",
    "product_category_id",
)


@saved_query("qrycboProducts")
def qrycbo_products(params: dict[str, str]) -> list[tuple]:
    """The products of the category chosen in the order line's category filter,
    sorted by name, discontinued ones included (R-inventory-027)."""
    category_id = _int_param(params, CATEGORY_PARAM)
    return list(
        queries.products_in_category(category_id).values_list(
            *PRODUCT_CHOICE_COLUMNS,
        ),
    )


@saved_query("qrycboProducts_All")
def qrycbo_products_all(params: dict[str, str]) -> list[tuple]:
    """Every product sorted by name, discontinued ones included (R-inventory-027)."""
    return list(queries.all_products_by_name().values_list(*PRODUCT_CHOICE_COLUMNS))
