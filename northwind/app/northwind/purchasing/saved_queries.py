"""Equivalence units of the Purchasing and receiving area (docs/contracts.md#harness).

Exactly the unit ids of goldens/manifest.json whose area is purchasing (all of kind
saved_query; the area has no formula_output or document units). core.apps imports
this module when Django starts. Every function computes from the database through
the ORM querysets of queries.py and the domain functions; none reads golden files or
branches on the dataset, a seed or row ids. Rows are tuples in the manifest's column
order.
"""

from __future__ import annotations

from northwind.core.saved_queries import saved_query
from northwind.legacy.models import PurchaseOrder

from . import queries

#: The output columns of each unit, in the manifest's order (the tests compare them
#: with goldens/manifest.json).
COLUMNS: dict[str, tuple[str, ...]] = {
    "qryPurchaseOrder": (
        "PurchaseOrderID",
        "VendorID",
        "SubmittedByID",
        "SubmittedDate",
        "ApprovedByID",
        "ApprovedDate",
        "StatusID",
        "ReceivedDate",
        "ShippingFee",
        "TaxAmount",
        "PaymentDate",
        "PaymentAmount",
        "PaymentMethod",
        "Notes",
        "AddedBy",
        "AddedOn",
        "ModifiedBy",
        "ModifiedOn",
        "StatusName",
        "SubmittedBy",
        "ApprovedBy",
    ),
    "qryPurchaseOrderCost": ("PurchaseOrderID", "ExtendedCost"),
    "qryPurchaseOrderLineItems": (
        "PurchaseOrderDetailID",
        "PurchaseOrderID",
        "ProductID",
        "Quantity",
        "UnitCost",
        "ReceivedDate",
        "AddedBy",
        "AddedOn",
        "ModifiedBy",
        "ModifiedOn",
    ),
    "qryPurchaseOrderList": (
        "PurchaseOrderID",
        "StatusName",
        "CompanyName",
        "TotalCost",
        "Submitter",
        "SubmittedDate",
        "Approver",
        "ApprovedDate",
        "PaymentDate",
    ),
    "qryVendorPurchaseOrderList": (
        "myCompanyID",
        "PurchaseOrderID",
        "SubmittedByID",
        "SubmittedDate",
        "ApprovedByID",
        "ApprovedDate",
        "StatusID",
        "ReceivedDate",
        "ShippingFee",
        "TaxAmount",
        "PaymentDate",
        "PaymentAmount",
        "PaymentMethod",
        "Notes",
        "AddedBy",
        "AddedOn",
        "ModifiedBy",
        "ModifiedOn",
        "SubmittedBy",
        "ApprovedBy",
        "StatusName",
        "ExtendedCost",
    ),
    "qrycboProducts_PO": ("ProductID", "ProductName", "StandardUnitCost"),
    "qrycboVendors": ("CompanyID", "CompanyName"),
}

#: The form control qrycboProducts_PO reads: the purchase order's vendor.
VENDOR_PARAM = "Parent!VendorID"


@saved_query("qryPurchaseOrder")
def qry_purchase_order(params: dict[str, str]) -> list[tuple]:
    """Every purchase order with its status name and the submitter's and approver's
    full names (the purchase order screen's record source)."""
    rows = queries.purchase_orders().order_by("purchase_order_id")
    return list(
        rows.values_list(
            *queries.PURCHASE_ORDER_COLUMNS,
            queries.STATUS_NAME,
            queries.SUBMITTED_BY_NAME,
            queries.APPROVED_BY_NAME,
        ),
    )


@saved_query("qryPurchaseOrderCost")
def qry_purchase_order_cost(params: dict[str, str]) -> list[tuple]:
    """R-purchasing-024: each purchase order's extended cost, NULL without lines."""
    rows = queries.with_extended_cost(PurchaseOrder.objects.all())
    return list(
        rows.order_by("purchase_order_id").values_list(
            "purchase_order_id",
            queries.EXTENDED_COST,
        ),
    )


@saved_query("qryPurchaseOrderLineItems")
def qry_purchase_order_line_items(params: dict[str, str]) -> list[tuple]:
    """Every purchase order line in entry order (the line items' record source)."""
    return list(queries.purchase_order_lines().values_list(*queries.LINE_COLUMNS))


@saved_query("qryPurchaseOrderList")
def qry_purchase_order_list(params: dict[str, str]) -> list[tuple]:
    """R-purchasing-025: the purchase order list, newest number first."""
    return list(
        queries.purchase_order_list().values_list(
            "purchase_order_id",
            queries.STATUS_NAME,
            "vendor__company_name",
            queries.TOTAL_COST,
            queries.SUBMITTED_BY_NAME,
            "submitted_date",
            queries.APPROVED_BY_NAME,
            "approved_date",
            "payment_date",
        ),
    )


@saved_query("qryVendorPurchaseOrderList")
def qry_vendor_purchase_order_list(params: dict[str, str]) -> list[tuple]:
    """R-purchasing-026: purchase orders that have a submitter, with the vendor key
    the company page filters on, names and extended cost."""
    columns = [name for name in queries.PURCHASE_ORDER_COLUMNS if name != "vendor_id"]
    rows = queries.vendor_purchase_orders().order_by("purchase_order_id")
    return list(
        rows.values_list(
            "vendor_id",
            *columns,
            queries.SUBMITTED_BY_NAME,
            queries.APPROVED_BY_NAME,
            queries.STATUS_NAME,
            queries.EXTENDED_COST,
        ),
    )


@saved_query("qrycboProducts_PO")
def qrycbo_products_po(params: dict[str, str]) -> list[tuple]:
    """R-purchasing-016: the products the purchase order's vendor supplies, by name,
    with their standard unit cost."""
    vendor = params.get(VENDOR_PARAM)
    vendor_id = int(vendor) if vendor not in (None, "") else None
    return list(
        queries.vendor_products(vendor_id).values_list(
            "product_id",
            "product_name",
            "standard_unit_cost",
        ),
    )


@saved_query("qrycboVendors")
def qrycbo_vendors(params: dict[str, str]) -> list[tuple]:
    """R-purchasing-017: the vendor companies by name."""
    return list(queries.vendors().values_list("company_id", "company_name"))
