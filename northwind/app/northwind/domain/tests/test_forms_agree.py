"""The queryset form and the plain form of each shared figure agree, also inside
filter() and order_by(), on every database the app runs on."""

# The fixture varies its rows by literal row numbers.
# ruff: noqa: PLR2004

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from northwind.domain import inventory
from northwind.domain import people
from northwind.domain import sales
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import OrderDetailFactory
from northwind.legacy.factories import OrderFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import PurchaseOrderDetailFactory
from northwind.legacy.factories import StockTakeFactory
from northwind.legacy.models import Employee
from northwind.legacy.models import Order
from northwind.legacy.models import Product

pytestmark = pytest.mark.django_db

ODS = OrderDetailStatusCode
POS = PurchaseOrderStatusCode
FIGURES = (
    "last_stock_take_date",
    "last_stock_take_quantity",
    "available",
    "allocated",
    "no_stock",
    "on_order",
    "to_sell",
    "reorder_quantity",
)


def at(day: int, month: int = 3) -> dt.datetime:
    return dt.datetime(2024, month, day, 12, 0)  # noqa: DTZ001 (USE_TZ is False)


@pytest.fixture
def products() -> list[Product]:
    """Products whose figures cover every branch: counted or not, received and
    invoiced before and after the count, each line status, each purchase order
    status, blank target and minimum."""
    made = []
    for n in range(6):
        product = ProductFactory(
            target_level=None if n == 4 else 5 * n,
            minimum_reorder_quantity=None if n == 5 else 2 + n,
        )
        if n % 3:
            StockTakeFactory(
                product=product,
                stock_take_date=at(2 + n),
                quantity_on_hand=3 * n,
            )
        else:
            Product.objects.filter(pk=product.pk).update(added_on=at(1 + n))
        for k, status in enumerate(
            (ODS.ALLOCATED, ODS.NO_STOCK, ODS.ON_ORDER, ODS.NEW),
        ):
            OrderDetailFactory(
                product=product,
                quantity=1 + (n + k) % 4,
                order_detail_status__order_detail_status_id=status,
                order__invoice_date=at(1 + n + k) if k % 2 else None,
            )
        for k, status in enumerate((POS.APPROVED, POS.RECEIVED, POS.NEW)):
            PurchaseOrderDetailFactory(
                product=product,
                quantity=2 + (n * k) % 5,
                purchase_order__status__status_id=status,
                received_date=at(3 + n - k) if status == POS.RECEIVED else None,
            )
        made.append(product)
    return made


def test_stock_figures_agree(products):
    """Every stock figure of with_stock_levels equals the plain function's."""
    rows = {p.pk: p for p in inventory.with_stock_levels(Product.objects.all())}
    for product in products:
        plain = inventory.stock_levels(product)
        row = rows[product.pk]
        assert {
            "last_stock_take_date": row.last_stock_take_date,
            "last_stock_take_quantity": row.last_stock_take_quantity,
            "available": row.product_available,
            "allocated": row.product_allocated,
            "no_stock": row.product_no_stock,
            "on_order": row.product_on_order,
            "to_sell": row.product_to_sell,
            "reorder_quantity": row.product_reorder_quantity,
        } == {name: getattr(plain, name) for name in FIGURES}, product.pk
        assert row.product_available == inventory.product_available(product)
        assert row.product_to_sell == inventory.product_to_sell(product)
        assert row.product_reorder_quantity == inventory.product_reorder_quantity(
            product,
        )


def test_stock_figures_filter_and_order(products):
    """The annotations work in filter() and order_by()."""
    to_sell = {p.pk: inventory.product_to_sell(p) for p in products}
    reorder = {p.pk: inventory.product_reorder_quantity(p) for p in products}
    threshold = sorted(to_sell.values())[len(to_sell) // 2]
    below = inventory.with_product_to_sell(Product.objects.all()).filter(
        product_to_sell__lt=threshold,
    )
    assert set(below.values_list("pk", flat=True)) == {
        pk for pk, value in to_sell.items() if value < threshold
    }
    ordered = inventory.with_product_reorder_quantity(Product.objects.all()).order_by(
        "-product_reorder_quantity",
        "pk",
    )
    assert list(ordered.values_list("pk", flat=True)) == sorted(
        reorder,
        key=lambda pk: (-reorder[pk], pk),
    )
    on_order = inventory.with_product_on_order(Product.objects.all()).filter(
        product_on_order__gt=0,
    )
    assert set(on_order.values_list("pk", flat=True)) == {
        p.pk for p in products if inventory.product_on_order(p) > 0
    }


def test_helpers_compose_without_duplicates(products):
    """Applying helpers twice or in any order adds each annotation once."""
    queryset = inventory.with_product_allocated(Product.objects.all())
    queryset = inventory.with_stock_levels(inventory.with_stock_levels(queryset))
    assert queryset.count() == len(products)


def test_order_totals_agree():
    """with_order_total equals order_total for each order, in filter() and
    order_by() too."""
    orders = []
    for n in range(4):
        order = OrderFactory()
        for k in range(n):
            OrderDetailFactory(
                order=order,
                quantity=1 + k,
                discount=None if (n, k) == (3, 2) else 0.25 * (k % 3),
                unit_price=Decimal("2.5") * (n + k),
            )
        orders.append(order)
    plain = {order.pk: sales.order_total(order) for order in orders}
    annotated = dict(
        sales.with_order_total(Order.objects.all()).values_list("pk", "order_total"),
    )
    assert annotated == plain
    big = sales.with_order_total(Order.objects.all()).filter(order_total__gt=10)
    assert set(big.values_list("pk", flat=True)) == {
        pk for pk, total in plain.items() if total is not None and total > 10
    }
    ranked = sales.with_order_total(Order.objects.all())
    ranked = ranked.filter(order_total__isnull=False).order_by("-order_total", "pk")
    assert list(ranked.values_list("pk", flat=True)) == sorted(
        (pk for pk, total in plain.items() if total is not None),
        key=lambda pk: (-plain[pk], pk),
    )


def test_full_names_agree():
    """with_full_name equals full_name and sorts like it."""
    for first, last in (("Bo", "Zed"), ("Al", "Young"), ("Cy", "Able")):
        EmployeeFactory(first_name=first, last_name=last)
    rows = people.with_full_name(Employee.objects.all()).order_by("full_name_fnln")
    assert [row.full_name_fnln for row in rows] == sorted(
        people.full_name(e) for e in Employee.objects.all()
    )
