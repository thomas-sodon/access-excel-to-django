"""django-tables2 tables of the Products and Inventory area."""

import django_tables2 as tables
from django.utils.html import format_html

from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Product
from northwind.legacy.models import ProductCategory
from northwind.legacy.models import PurchaseOrderDetail
from northwind.legacy.models import StockTake

from .links import other_area_url

#: hx-boost for the parts of a table. The list and the panels boost their container,
#: so the sort links (thead) and the paging links swap only the table or the panel.
#: The rows and the footer switch the boost off: a record link opens its page as a
#: normal page load, never inside the list (templates/feature-app tables.py).
UNBOOSTED_ROWS = {"tbody": {"hx-boost": "false"}, "tfoot": {"hx-boost": "false"}}

ATTRS = {"class": "table table-sm table-striped align-middle", **UNBOOSTED_ROWS}
NUMBER = {"td": {"class": "text-end"}, "th": {"class": "text-end"}}


def _linked(value, url: str | None):
    if url is None:
        return value
    return format_html('<a href="{}">{}</a>', url, value)


class ProductTable(tables.Table):
    """frmProductList: every product with its category, costs, reorder settings and
    calculated quantities (R-inventory-023). The code opens the product."""

    product_code = tables.Column(
        verbose_name="Code",
        linkify=("inventory:form_frmProductDetail", {"pk": tables.A("pk")}),
    )
    product_name = tables.Column(verbose_name="Product")
    product_category = tables.Column(
        verbose_name="Category",
        accessor="product_category__product_category_name",
        order_by="product_category__product_category_name",
    )
    standard_unit_cost = tables.Column(verbose_name="Std. cost", attrs=NUMBER)
    unit_price = tables.Column(verbose_name="Unit price", attrs=NUMBER)
    reorder_level = tables.Column(verbose_name="Reorder level", attrs=NUMBER)
    target_level = tables.Column(verbose_name="Target level", attrs=NUMBER)
    minimum_reorder_quantity = tables.Column(verbose_name="Min. reorder", attrs=NUMBER)
    product_no_stock = tables.Column(verbose_name="No stock", attrs=NUMBER)
    product_allocated = tables.Column(verbose_name="Allocated", attrs=NUMBER)
    product_to_sell = tables.Column(verbose_name="To sell", attrs=NUMBER)
    product_on_order = tables.Column(verbose_name="On order", attrs=NUMBER)
    discontinued = tables.BooleanColumn(verbose_name="Discontinued")

    class Meta:
        model = Product
        fields = (
            "product_code",
            "product_name",
            "product_category",
            "standard_unit_cost",
            "unit_price",
            "reorder_level",
            "target_level",
            "minimum_reorder_quantity",
            "product_no_stock",
            "product_allocated",
            "product_to_sell",
            "product_on_order",
            "discontinued",
        )
        order_by = ("product_name",)
        attrs = ATTRS


class ProductOrderTable(tables.Table):
    """sfrmProductDetail_Orders: the product's order lines (R-inventory-025)."""

    order_id = tables.Column(verbose_name="Order")
    order_date = tables.DateTimeColumn(
        verbose_name="Order date",
        accessor="order__order_date",
        format="Y-m-d",
    )
    quantity = tables.Column(verbose_name="Quantity", attrs=NUMBER)
    unit_price = tables.Column(verbose_name="Unit price", attrs=NUMBER)
    extended_price = tables.Column(verbose_name="Extended price", attrs=NUMBER)
    order_status = tables.Column(
        verbose_name="Order status",
        accessor="order__order_status__order_status_name",
    )
    line_status = tables.Column(
        verbose_name="Line status",
        accessor="order_detail_status__order_detail_status_name",
    )

    class Meta:
        model = OrderDetail
        fields = (
            "order_id",
            "order_date",
            "quantity",
            "unit_price",
            "extended_price",
            "order_status",
            "line_status",
        )
        orderable = False
        attrs = ATTRS

    def render_order_id(self, value):
        """The order number opens the order when the orders area is installed."""
        return _linked(value, other_area_url("orders:form_frmOrderDetails", value))


class ProductPurchaseOrderTable(tables.Table):
    """sfrmProductDetail_PurchaseOrders: the product's purchase-order lines
    (R-inventory-026)."""

    purchase_order_id = tables.Column(verbose_name="Purchase order")
    status = tables.Column(
        verbose_name="Status",
        accessor="purchase_order__status__status_name",
    )
    quantity = tables.Column(verbose_name="Quantity", attrs=NUMBER)
    unit_cost = tables.Column(verbose_name="Unit cost", attrs=NUMBER)
    extended_cost = tables.Column(verbose_name="Extended cost", attrs=NUMBER)
    vendor = tables.Column(
        verbose_name="Vendor",
        accessor="purchase_order__vendor__company_name",
    )
    submitted_date = tables.DateTimeColumn(
        verbose_name="Submitted",
        accessor="purchase_order__submitted_date",
        format="Y-m-d",
    )
    received_date = tables.DateTimeColumn(verbose_name="Received", format="Y-m-d")

    class Meta:
        model = PurchaseOrderDetail
        fields = (
            "purchase_order_id",
            "status",
            "quantity",
            "unit_cost",
            "extended_cost",
            "vendor",
            "submitted_date",
            "received_date",
        )
        orderable = False
        attrs = ATTRS

    def render_purchase_order_id(self, value):
        """The number opens the purchase order when the purchasing area is
        installed."""
        url = other_area_url("purchasing:form_frmPurchaseOrderDetails", value)
        return _linked(value, url)


class StockTakeTable(tables.Table):
    """sfrmProductDetail_StockTake: the product's stock takes, read-only
    (R-inventory-011)."""

    stock_take_date = tables.DateTimeColumn(verbose_name="Date", format="Y-m-d H:i:s")
    quantity_on_hand = tables.Column(verbose_name="Counted", attrs=NUMBER)
    expected_quantity = tables.Column(verbose_name="Expected", attrs=NUMBER)
    added_by = tables.Column(verbose_name="Counted by")

    class Meta:
        model = StockTake
        fields = (
            "stock_take_date",
            "quantity_on_hand",
            "expected_quantity",
            "added_by",
        )
        orderable = False
        attrs = ATTRS


class CategoryTable(tables.Table):
    """sfrmProductCategories: the categories; the name opens the category."""

    product_category_name = tables.Column(
        verbose_name="Category",
        linkify=("inventory:category_update", {"pk": tables.A("pk")}),
    )
    product_category_code = tables.Column(verbose_name="Code")
    product_category_desc = tables.Column(verbose_name="Description")

    class Meta:
        model = ProductCategory
        fields = (
            "product_category_name",
            "product_category_code",
            "product_category_desc",
        )
        order_by = ("product_category_name",)
        attrs = ATTRS
