"""Stock figures of a product and stock allocation (the original's inventory module).

Used by the orders area (a new order line is Allocated when the physical stock
covers it, R-orders-009; lines re-allocate, R-orders-010, R-orders-011), the
inventory area (product page, product list, stock takes) and the purchasing area
(on-order and bought quantities, reorder quantities, allocation after approval and
receipt).

Every figure comes in two forms that agree (tests/test_forms_agree.py):

- a queryset helper, `with_<figure>(Product queryset)`, that adds the figure as an
  annotation built from Subquery, OuterRef, Coalesce and Case, so it works in
  filter(), order_by() and values() on PostgreSQL and SQL Server;
- a plain function, `<figure>(product)`, for one product (a Product or its key).

Nulls follow the original: a product without matching rows has 0 (Nz(..., 0)), a
blank target level counts as 0 and a blank minimum reorder quantity as 1.

The figures (rule ids in analysis/rules.json):

- physical stock (`product_available`, R-inventory-001): quantity of the latest stock
  take + purchase-order lines received at or after that stock take - order lines whose
  order was invoiced at or after it. Lines without a received date and orders without
  an invoice date do not count.
- latest stock take (R-inventory-002): the stock take with the latest date and time
  (the largest counted quantity on a tie, as the reference rewrite takes Max). A
  product without one counts from its added date, or from now when that is blank;
  `ensure_opening_stock_take` writes that opening zero stock take, as the original
  did the first time it computed stock.
- allocated and no-stock quantities (R-inventory-003): order line quantities in the
  Allocated and No Stock line statuses.
- on-order quantity (R-inventory-004): purchase-order line quantities of Approved
  purchase orders only.
- quantity to sell (R-inventory-005): physical stock - allocated; can be negative.
- suggested reorder quantity (R-inventory-006).
- `allocate_inventory` (R-inventory-007) re-evaluates the waiting order lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Case
from django.db.models import DateTimeField
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import Coalesce
from django.db.models.functions import Now
from django.db.models.lookups import GreaterThan
from django.db.models.lookups import GreaterThanOrEqual

from northwind.legacy import audit
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Product
from northwind.legacy.models import PurchaseOrderDetail
from northwind.legacy.models import StockTake

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable

    from django.db.models import Expression
    from django.db.models import QuerySet

ALLOCATED = OrderDetailStatusCode.ALLOCATED
NO_STOCK = OrderDetailStatusCode.NO_STOCK
ON_ORDER = OrderDetailStatusCode.ON_ORDER
APPROVED = PurchaseOrderStatusCode.APPROVED

#: Line statuses that allocation re-evaluates (R-inventory-007).
WAITING_STATUSES = (ALLOCATED, NO_STOCK, ON_ORDER)

# Annotation names the queryset helpers add.
LAST_STOCK_TAKE_DATE = "last_stock_take_date"
LAST_STOCK_TAKE_QUANTITY = "last_stock_take_quantity"
STOCK_AS_OF = "stock_as_of"
PRODUCT_BOUGHT = "product_bought"
PRODUCT_SOLD = "product_sold"
PRODUCT_AVAILABLE = "product_available"
PRODUCT_ALLOCATED = "product_allocated"
PRODUCT_NO_STOCK = "product_no_stock"
PRODUCT_ON_ORDER = "product_on_order"
PRODUCT_TO_SELL = "product_to_sell"
PRODUCT_REORDER_QUANTITY = "product_reorder_quantity"


# ---------------------------------------------------------------- expressions


def _quantity_total(rows: QuerySet) -> Coalesce:
    """Nz(Sum(Quantity) of `rows`, 0) as a correlated subquery (rows filter on
    OuterRef)."""
    total = rows.order_by().values("product").annotate(total=Sum("quantity"))
    return Coalesce(
        Subquery(total.values("total"), output_field=IntegerField()),
        Value(0),
        output_field=IntegerField(),
    )


def _annotate(
    queryset: QuerySet,
    name: str,
    build: Callable[[], Expression],
) -> QuerySet:
    """Add one annotation unless the queryset already has it."""
    if name in queryset.query.annotations:
        return queryset
    return queryset.annotate(**{name: build()})


def _order_quantity(status: int) -> Coalesce:
    return _quantity_total(
        OrderDetail.objects.filter(product=OuterRef("pk"), order_detail_status=status),
    )


def with_product_allocated(queryset: QuerySet) -> QuerySet:
    """Annotate `product_allocated` (R-inventory-003)."""
    return _annotate(queryset, PRODUCT_ALLOCATED, lambda: _order_quantity(ALLOCATED))


def with_product_no_stock(queryset: QuerySet) -> QuerySet:
    """Annotate `product_no_stock` (R-inventory-003)."""
    return _annotate(queryset, PRODUCT_NO_STOCK, lambda: _order_quantity(NO_STOCK))


def with_product_on_order(queryset: QuerySet) -> QuerySet:
    """Annotate `product_on_order`: quantities on Approved purchase orders
    (R-inventory-004)."""
    return _annotate(
        queryset,
        PRODUCT_ON_ORDER,
        lambda: _quantity_total(
            PurchaseOrderDetail.objects.filter(
                product=OuterRef("pk"),
                purchase_order__status=APPROVED,
            ),
        ),
    )


def with_last_stock_take(queryset: QuerySet) -> QuerySet:
    """Annotate `last_stock_take_date`, `last_stock_take_quantity` (0 without a stock
    take) and `stock_as_of`, the moment the stock figures count from: the latest stock
    take, else the product's added date, else now (R-inventory-002)."""
    latest = StockTake.objects.filter(product=OuterRef("pk")).order_by(
        "-stock_take_date",
        "-quantity_on_hand",
    )
    queryset = _annotate(
        queryset,
        LAST_STOCK_TAKE_DATE,
        lambda: Subquery(
            latest.values("stock_take_date")[:1],
            output_field=DateTimeField(),
        ),
    )
    queryset = _annotate(
        queryset,
        LAST_STOCK_TAKE_QUANTITY,
        lambda: Coalesce(
            Subquery(latest.values("quantity_on_hand")[:1]),
            Value(0),
            output_field=IntegerField(),
        ),
    )
    return _annotate(
        queryset,
        STOCK_AS_OF,
        lambda: Coalesce(
            F(LAST_STOCK_TAKE_DATE),
            F("added_on"),
            Now(),
            output_field=DateTimeField(),
        ),
    )


def with_product_available(queryset: QuerySet) -> QuerySet:
    """Annotate `product_available`, the physical stock (R-inventory-001), with its
    parts `product_bought` and `product_sold` and the stock take annotations of
    with_last_stock_take."""
    queryset = with_last_stock_take(queryset)
    queryset = _annotate(
        queryset,
        PRODUCT_BOUGHT,
        lambda: _quantity_total(
            PurchaseOrderDetail.objects.filter(
                product=OuterRef("pk"),
                received_date__gte=OuterRef(STOCK_AS_OF),
            ),
        ),
    )
    queryset = _annotate(
        queryset,
        PRODUCT_SOLD,
        lambda: _quantity_total(
            OrderDetail.objects.filter(
                product=OuterRef("pk"),
                order__invoice_date__gte=OuterRef(STOCK_AS_OF),
            ),
        ),
    )
    return _annotate(
        queryset,
        PRODUCT_AVAILABLE,
        lambda: F(LAST_STOCK_TAKE_QUANTITY) + F(PRODUCT_BOUGHT) - F(PRODUCT_SOLD),
    )


def with_product_to_sell(queryset: QuerySet) -> QuerySet:
    """Annotate `product_to_sell` = physical stock - allocated (R-inventory-005)."""
    queryset = with_product_allocated(with_product_available(queryset))
    return _annotate(
        queryset,
        PRODUCT_TO_SELL,
        lambda: F(PRODUCT_AVAILABLE) - F(PRODUCT_ALLOCATED),
    )


def with_product_reorder_quantity(queryset: QuerySet) -> QuerySet:
    """Annotate `product_reorder_quantity` (R-inventory-006): the minimum reorder
    quantity when quantity to sell + on order covers no stock + target level,
    otherwise the shortfall, raised to the minimum reorder quantity."""
    queryset = with_product_to_sell(queryset)
    queryset = with_product_no_stock(with_product_on_order(queryset))

    def build() -> Case:
        supply = F(PRODUCT_TO_SELL) + F(PRODUCT_ON_ORDER)
        demand = F(PRODUCT_NO_STOCK) + Coalesce(
            F("target_level"),
            Value(0),
            output_field=IntegerField(),
        )
        minimum = Coalesce(
            F("minimum_reorder_quantity"),
            Value(1),
            output_field=IntegerField(),
        )
        return Case(
            When(GreaterThanOrEqual(supply, demand), then=minimum),
            When(GreaterThan(minimum, demand - supply), then=minimum),
            default=demand - supply,
            output_field=IntegerField(),
        )

    return _annotate(queryset, PRODUCT_REORDER_QUANTITY, build)


def with_stock_levels(queryset: QuerySet) -> QuerySet:
    """Every figure of this module as annotations (the product list and page)."""
    return with_product_reorder_quantity(queryset)


# ---------------------------------------------------------------- one product


@dataclass(frozen=True)
class StockLevels:
    """The stock figures of one product (inventory service product_stock_levels)."""

    last_stock_take_date: dt.datetime | None
    last_stock_take_quantity: int
    available: int
    allocated: int
    no_stock: int
    on_order: int
    to_sell: int
    reorder_quantity: int


def _product_id(product: Product | int) -> int:
    return product.pk if isinstance(product, Product) else int(product)


def _quantity(rows: QuerySet) -> int:
    return rows.aggregate(total=Sum("quantity"))["total"] or 0


def product_allocated(product: Product | int) -> int:
    """Quantity on order lines in the Allocated status (R-inventory-003)."""
    return _quantity(
        OrderDetail.objects.filter(
            product_id=_product_id(product),
            order_detail_status=ALLOCATED,
        ),
    )


def product_no_stock(product: Product | int) -> int:
    """Quantity on order lines in the No Stock status (R-inventory-003)."""
    return _quantity(
        OrderDetail.objects.filter(
            product_id=_product_id(product),
            order_detail_status=NO_STOCK,
        ),
    )


def product_on_order(product: Product | int) -> int:
    """Quantity on lines of Approved purchase orders (R-inventory-004)."""
    return _quantity(
        PurchaseOrderDetail.objects.filter(
            product_id=_product_id(product),
            purchase_order__status=APPROVED,
        ),
    )


def last_stock_take(product: Product | int) -> tuple[dt.datetime | None, int]:
    """(date, counted quantity) of the latest stock take; (None, 0) without one
    (R-inventory-002)."""
    latest = (
        StockTake.objects.filter(product_id=_product_id(product))
        .order_by("-stock_take_date", "-quantity_on_hand")
        .values_list("stock_take_date", "quantity_on_hand")
        .first()
    )
    return latest if latest is not None else (None, 0)


def stock_as_of(product: Product | int) -> dt.datetime:
    """The moment the stock figures count from: the latest stock take, else the
    product's added date, else now (R-inventory-002)."""
    taken_on, _quantity_counted = last_stock_take(product)
    if taken_on is not None:
        return taken_on
    added_on = (
        Product.objects.filter(pk=_product_id(product))
        .values_list("added_on", flat=True)
        .first()
    )
    return added_on if added_on is not None else audit.stamp_time()


def product_bought(product: Product | int, as_of: dt.datetime) -> int:
    """Quantity on purchase-order lines received at or after `as_of`."""
    return _quantity(
        PurchaseOrderDetail.objects.filter(
            product_id=_product_id(product),
            received_date__gte=as_of,
        ),
    )


def product_sold(product: Product | int, as_of: dt.datetime) -> int:
    """Quantity on order lines whose order was invoiced at or after `as_of`."""
    return _quantity(
        OrderDetail.objects.filter(
            product_id=_product_id(product),
            order__invoice_date__gte=as_of,
        ),
    )


def product_available(product: Product | int) -> int:
    """Physical stock (R-inventory-001)."""
    as_of = stock_as_of(product)
    _taken_on, counted = last_stock_take(product)
    return counted + product_bought(product, as_of) - product_sold(product, as_of)


def product_to_sell(product: Product | int) -> int:
    """Physical stock - allocated; can be negative (R-inventory-005)."""
    return product_available(product) - product_allocated(product)


def product_reorder_quantity(product: Product | int) -> int:
    """Suggested reorder quantity (R-inventory-006)."""
    target_level, minimum = (
        Product.objects.filter(pk=_product_id(product))
        .values_list("target_level", "minimum_reorder_quantity")
        .get()
    )
    return _reorder_quantity(
        to_sell=product_to_sell(product),
        on_order=product_on_order(product),
        no_stock=product_no_stock(product),
        target_level=target_level,
        minimum_reorder_quantity=minimum,
    )


def _reorder_quantity(
    *,
    to_sell: int,
    on_order: int,
    no_stock: int,
    target_level: int | None,
    minimum_reorder_quantity: int | None,
) -> int:
    supply = to_sell + on_order
    demand = no_stock + (0 if target_level is None else target_level)
    minimum = 1 if minimum_reorder_quantity is None else minimum_reorder_quantity
    if supply >= demand:
        return minimum
    return max(demand - supply, minimum)


def stock_levels(product: Product | int) -> StockLevels:
    """Every stock figure of one product."""
    taken_on, counted = last_stock_take(product)
    available = product_available(product)
    allocated = product_allocated(product)
    no_stock = product_no_stock(product)
    on_order = product_on_order(product)
    target_level, minimum = (
        Product.objects.filter(pk=_product_id(product))
        .values_list("target_level", "minimum_reorder_quantity")
        .get()
    )
    to_sell = available - allocated
    return StockLevels(
        last_stock_take_date=taken_on,
        last_stock_take_quantity=counted,
        available=available,
        allocated=allocated,
        no_stock=no_stock,
        on_order=on_order,
        to_sell=to_sell,
        reorder_quantity=_reorder_quantity(
            to_sell=to_sell,
            on_order=on_order,
            no_stock=no_stock,
            target_level=target_level,
            minimum_reorder_quantity=minimum,
        ),
    )


# ---------------------------------------------------------------- writes


def ensure_opening_stock_take(product: Product | int) -> StockTake | None:
    """Give a product without any stock take its opening stock take: quantity 0, dated
    at the product's added date, or now when that is blank (R-inventory-002). Returns
    the new stock take, or None when the product already had one. The figures stay
    the same: they already count from that moment."""
    product_id = _product_id(product)
    if StockTake.objects.filter(product_id=product_id).exists():
        return None
    return StockTake.objects.create(
        product_id=product_id,
        stock_take_date=stock_as_of(product_id),
        quantity_on_hand=0,
    )


def allocate_inventory(product: Product | int) -> list[OrderDetail]:
    """Re-evaluate the product's order lines in Allocated, No Stock or On Order status,
    oldest order date first, lower order number first on a tie (R-inventory-007).

    A line becomes Allocated when its whole quantity fits in the physical stock not yet
    allocated, else On Order when it fits in that stock plus the on-order quantity, else
    No Stock; lines are never part-allocated. Returns the lines whose status changed;
    only those are saved (stamped with the current audit name, legacy.audit). Writes
    the opening stock take first when the product has none, as the original's stock
    calculation did (R-inventory-002)."""
    product_id = _product_id(product)
    with transaction.atomic():
        ensure_opening_stock_take(product_id)
        available = product_available(product_id)
        to_allocate = available + product_on_order(product_id)
        lines = OrderDetail.objects.filter(
            product_id=product_id,
            order_detail_status__in=WAITING_STATUSES,
        ).order_by("order__order_date", "order_id")
        changed: list[OrderDetail] = []
        for line in lines:
            if line.quantity <= available:
                status = ALLOCATED
                available -= line.quantity
                to_allocate -= line.quantity
            elif line.quantity <= to_allocate:
                status = ON_ORDER
                to_allocate -= line.quantity
            else:
                status = NO_STOCK
            if line.order_detail_status_id != status:
                line.order_detail_status_id = status
                line.save(update_fields=["order_detail_status"])
                changed.append(line)
    return changed
