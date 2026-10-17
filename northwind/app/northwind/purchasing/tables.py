"""django-tables2 tables of the Purchasing and receiving area."""

import django_tables2 as tables

from northwind.legacy.models import PurchaseOrder

from . import queries

#: hx-boost for the parts of a list table. list.html and
#: vendor_purchase_orders.html boost their container, so the sort links (thead) and
#: the paging links swap only the table. The rows and the footer switch the boost
#: off: a record link opens its page as a normal page load, never inside the list.
UNBOOSTED_ROWS = {"tbody": {"hx-boost": "false"}, "tfoot": {"hx-boost": "false"}}

TABLE_ATTRS = {"class": "table table-sm table-striped", **UNBOOSTED_ROWS}


class PurchaseOrderListTable(tables.Table):
    """The purchase order list (frmPurchaseOrderList, R-purchasing-025); the number
    opens the purchase order."""

    purchase_order_id = tables.Column(
        verbose_name="PO No.",
        linkify=("purchasing:form_frmPurchaseOrderDetails", {"pk": tables.A("pk")}),
    )
    status_name = tables.Column(accessor=queries.STATUS_NAME, verbose_name="Status")
    vendor = tables.Column(accessor="vendor__company_name", verbose_name="Vendor")
    total_cost = tables.Column(accessor=queries.TOTAL_COST, verbose_name="Total cost")
    submitted_by_name = tables.Column(
        accessor=queries.SUBMITTED_BY_NAME,
        verbose_name="Submitted by",
    )
    submitted_date = tables.DateTimeColumn(verbose_name="Submitted")
    approved_by_name = tables.Column(
        accessor=queries.APPROVED_BY_NAME,
        verbose_name="Approved by",
    )
    approved_date = tables.DateTimeColumn(verbose_name="Approved")
    payment_date = tables.DateTimeColumn(verbose_name="Paid")

    class Meta:
        model = PurchaseOrder
        fields = ()
        sequence = (
            "purchase_order_id",
            "status_name",
            "vendor",
            "total_cost",
            "submitted_by_name",
            "submitted_date",
            "approved_by_name",
            "approved_date",
            "payment_date",
        )
        attrs = TABLE_ATTRS
        order_by = ("-purchase_order_id",)


class VendorPurchaseOrderTable(tables.Table):
    """The purchase order tab of a vendor's company page
    (sfrmCompanyDetail_VendorPurchaseOrders, R-purchasing-026); the number opens the
    purchase order, as the original's double-click did."""

    purchase_order_id = tables.Column(
        verbose_name="PO No.",
        linkify=("purchasing:form_frmPurchaseOrderDetails", {"pk": tables.A("pk")}),
    )
    status_name = tables.Column(accessor=queries.STATUS_NAME, verbose_name="Status")
    submitted_by_name = tables.Column(
        accessor=queries.SUBMITTED_BY_NAME,
        verbose_name="Submitted by",
    )
    submitted_date = tables.DateTimeColumn(verbose_name="Submitted")
    approved_by_name = tables.Column(
        accessor=queries.APPROVED_BY_NAME,
        verbose_name="Approved by",
    )
    approved_date = tables.DateTimeColumn(verbose_name="Approved")
    received_date = tables.DateTimeColumn(verbose_name="Received")
    payment_date = tables.DateTimeColumn(verbose_name="Paid")
    payment_method = tables.Column(verbose_name="Payment method")
    payment_amount = tables.Column(verbose_name="Payment amount")
    extended_cost = tables.Column(
        accessor=queries.EXTENDED_COST,
        verbose_name="Extended cost",
    )

    class Meta:
        model = PurchaseOrder
        fields = ()
        sequence = (
            "purchase_order_id",
            "status_name",
            "submitted_by_name",
            "submitted_date",
            "approved_by_name",
            "approved_date",
            "received_date",
            "payment_date",
            "payment_method",
            "payment_amount",
            "extended_cost",
        )
        attrs = TABLE_ATTRS
        order_by = ("-purchase_order_id",)
