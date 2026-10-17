"""Order line amounts and order totals (the original's order total query).

Used by the orders area (order screen, order lists, invoice) and the reports area
(sales per employee, per product and per quarter, the catalog's lifetime sales).

The original computes Quantity * (1 - Discount) * UnitPrice in double precision and
sums it per order; both forms here do the same, so the values are floats exactly as
the database returns them. Round for display or output with
core.vbacompat.ccur (four places, half-even, docs/contracts.md#canonical-output).
Nulls as the original: a line with a blank discount has no amount and adds nothing
to a sum; an order without lines (or whose lines all have no amount) has no total.

Portability: SQL Server refuses an aggregate over a subquery, so never Sum() the
`order_total` annotation inside a GROUP BY (values(...).annotate(Sum(...))). Group
the order lines instead: OrderDetail.objects.values("order__employee").annotate(
total=Sum(line_amount_expression())) gives the same sums on both databases
(tests/test_rules.py, R-reports-004).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import F
from django.db.models import FloatField
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Cast

from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail

if TYPE_CHECKING:
    from django.db.models import Expression
    from django.db.models import QuerySet

LINE_AMOUNT = "line_amount"
ORDER_TOTAL = "order_total"


def line_amount_expression(prefix: str = "") -> Expression:
    """Quantity x (1 - Discount) x UnitPrice of an order line, as a double
    (R-orders-022). `prefix` reaches the line through a relation ("lines__" from
    an Order queryset, say)."""
    return (
        F(f"{prefix}quantity")
        * (Value(1) - F(f"{prefix}discount"))
        * Cast(F(f"{prefix}unit_price"), FloatField())
    )


def with_line_amount(queryset: QuerySet) -> QuerySet:
    """Annotate `line_amount` on an OrderDetail queryset (R-orders-022)."""
    return queryset.annotate(**{LINE_AMOUNT: line_amount_expression()})


def order_total_expression(order_ref: str = "pk") -> Subquery:
    """The order's total without tax and shipping, as a correlated subquery; null when
    the order has no lines (R-orders-023). `order_ref` names the order key in the
    outer queryset ("order_id" from an OrderDetail queryset, say)."""
    totals = (
        OrderDetail.objects.filter(order_id=OuterRef(order_ref))
        .order_by()
        .values("order")
        .annotate(total=Sum(line_amount_expression()))
        .values("total")
    )
    return Subquery(totals, output_field=FloatField())


def with_order_total(queryset: QuerySet) -> QuerySet:
    """Annotate `order_total` on an Order queryset (R-orders-023)."""
    return queryset.annotate(**{ORDER_TOTAL: order_total_expression()})


def line_amount(line: OrderDetail) -> float | None:
    """Quantity x (1 - Discount) x UnitPrice of one line; None when the discount is
    blank (R-orders-022)."""
    if line.quantity is None or line.discount is None or line.unit_price is None:
        return None
    return line.quantity * (1 - line.discount) * float(line.unit_price)


def order_total(order: Order | int) -> float | None:
    """Sum of the line amounts of one order; None when no line has an amount
    (R-orders-023)."""
    order_id = order.pk if isinstance(order, Order) else int(order)
    amounts = [
        amount
        for amount in map(
            line_amount,
            OrderDetail.objects.filter(order_id=order_id).order_by("pk"),
        )
        if amount is not None
    ]
    return sum(amounts) if amounts else None
