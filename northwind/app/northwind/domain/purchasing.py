"""Adding products to purchase orders (the original's purchase order module).

Used by the purchasing area (new purchase orders, line items, the add-all-no-stock
action) and the inventory area (reordering a product from its page). The callers
validate first (the area's own rules, such as R-purchasing-012 lines only while New
or R-purchasing-019 the minimum reorder quantity) and wrap the call in
transaction.atomic() and domain.people.acting_for(request.user).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.models import Company
from northwind.legacy.models import Product
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail

if TYPE_CHECKING:
    from decimal import Decimal
    from typing import Any

NEW = PurchaseOrderStatusCode.NEW


def start_purchase_order(vendor: Company | int, **fields: Any) -> PurchaseOrder:
    """A new purchase order for the vendor, always in status New, whether entered by
    hand or created by a reorder (R-purchasing-001). `fields` sets other columns
    (notes, say); a status among them is ignored."""
    fields.pop("status", None)
    fields.pop("status_id", None)
    vendor_id = vendor.pk if isinstance(vendor, Company) else int(vendor)
    return PurchaseOrder.objects.create(vendor_id=vendor_id, status_id=NEW, **fields)


def add_purchase_order_line(
    purchase_order: PurchaseOrder | int,
    product: Product | int,
    quantity: int,
    unit_cost: Decimal,
) -> PurchaseOrderDetail:
    """Put `quantity` of the product on the purchase order (R-purchasing-020): when the
    product is already on it, the quantity is added to that line and the line keeps
    its unit cost; otherwise a new line gets the quantity and `unit_cost`."""
    po_id = (
        purchase_order.pk
        if isinstance(purchase_order, PurchaseOrder)
        else int(purchase_order)
    )
    product_id = product.pk if isinstance(product, Product) else int(product)
    line = PurchaseOrderDetail.objects.filter(
        purchase_order_id=po_id,
        product_id=product_id,
    ).first()
    if line is None:
        return PurchaseOrderDetail.objects.create(
            purchase_order_id=po_id,
            product_id=product_id,
            quantity=quantity,
            unit_cost=unit_cost,
        )
    # Plain arithmetic, not F(): the history row (django-simple-history) copies the
    # saved values and cannot insert an expression.
    line.quantity += quantity
    line.save(update_fields=["quantity"])
    return line


def oldest_new_purchase_order(vendor: Company | int) -> PurchaseOrder | None:
    """The vendor's purchase order in status New with the lowest number, if any."""
    vendor_id = vendor.pk if isinstance(vendor, Company) else int(vendor)
    return (
        PurchaseOrder.objects.filter(vendor_id=vendor_id, status_id=NEW)
        .order_by("purchase_order_id")
        .first()
    )


def reorder_into_purchase_order(
    product: Product | int,
    vendor: Company | int,
    quantity: int,
) -> PurchaseOrderDetail:
    """Add a reorder of the product to the vendor's oldest New purchase order, or to a
    new New purchase order when the vendor has none (R-inventory-020,
    R-purchasing-001). The line's unit cost is the product's standard unit cost; a
    product already on that purchase order gets its quantity increased
    (R-purchasing-020). Returns the line; `line.purchase_order` is the order."""
    if not isinstance(product, Product):
        product = Product.objects.get(pk=int(product))
    purchase_order = oldest_new_purchase_order(vendor)
    if purchase_order is None:
        purchase_order = start_purchase_order(vendor)
    return add_purchase_order_line(
        purchase_order,
        product,
        quantity,
        product.standard_unit_cost,
    )
