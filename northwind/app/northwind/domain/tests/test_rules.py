"""One test per rule the domain app implements (rule id first in the docstring).

Data comes from legacy/factories.py; every expected value is worked out by hand in the
test. Each figure is checked in both forms: the queryset annotation and the plain
function for one object.
"""

# Expected values are worked out by hand and written as literals next to the sum.
# ruff: noqa: PLR2004

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db.models import Sum

from northwind.domain import inventory
from northwind.domain import people
from northwind.domain import purchasing
from northwind.domain import sales
from northwind.domain import system_settings
from northwind.legacy.audit import SYSTEM
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.choices import SystemSettingCode
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import OrderDetailFactory
from northwind.legacy.factories import OrderFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import PurchaseOrderDetailFactory
from northwind.legacy.factories import PurchaseOrderFactory
from northwind.legacy.factories import PurchaseOrderStatusFactory
from northwind.legacy.factories import StockTakeFactory
from northwind.legacy.factories import SystemSettingFactory
from northwind.legacy.factories import VendorFactory
from northwind.legacy.models import Employee
from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Product
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail
from northwind.legacy.models import StockTake

pytestmark = pytest.mark.django_db

ODS = OrderDetailStatusCode
POS = PurchaseOrderStatusCode


def at(day: int, hour: int = 9, month: int = 1) -> dt.datetime:
    return dt.datetime(2024, month, day, hour, 0)  # noqa: DTZ001 (USE_TZ is False)


def line(product, quantity, status=ODS.NEW, **kwargs) -> OrderDetail:
    """An order line of `product` in `status`; order fields as order__<field>."""
    return OrderDetailFactory(
        product=product,
        quantity=quantity,
        order_detail_status__order_detail_status_id=status,
        **kwargs,
    )


def po_line(product, quantity, status=POS.NEW, **kwargs) -> PurchaseOrderDetail:
    """A purchase order line of `product` on a purchase order in `status`."""
    return PurchaseOrderDetailFactory(
        product=product,
        quantity=quantity,
        purchase_order__status__status_id=status,
        **kwargs,
    )


@pytest.fixture
def new_status():
    """The New purchase order status row, which every real database carries."""
    return PurchaseOrderStatusFactory(status_id=POS.NEW)


def annotated(product: Product) -> Product:
    return inventory.with_stock_levels(Product.objects.filter(pk=product.pk)).get()


# ---------------------------------------------------------------- inventory


def test_physical_stock_counts_from_the_latest_stock_take():
    """R-inventory-001: physical stock = latest count + received since - invoiced
    since; unreceived lines and uninvoiced orders do not count."""
    product = ProductFactory()
    StockTakeFactory(product=product, stock_take_date=at(1), quantity_on_hand=99)
    StockTakeFactory(product=product, stock_take_date=at(15), quantity_on_hand=12)
    po_line(product, 10, POS.RECEIVED, received_date=at(20))  # after: +10
    po_line(product, 1, POS.RECEIVED, received_date=at(15))  # at the count: +1
    po_line(product, 7, POS.RECEIVED, received_date=at(10))  # before: ignored
    po_line(product, 5, POS.APPROVED)  # not received: ignored
    line(product, 3, ODS.INVOICED, order__invoice_date=at(16))  # after: -3
    line(product, 4, ODS.INVOICED, order__invoice_date=at(14))  # before: ignored
    line(product, 6, ODS.ALLOCATED)  # not invoiced: ignored
    # 12 + 10 + 1 - 3 = 20
    assert inventory.product_available(product) == 20
    assert annotated(product).product_available == 20


def test_invoiced_order_counts_as_sold_whatever_the_line_status():
    """R-inventory-001: every line of an invoiced order counts as sold from the invoice
    date, whatever the line's own status."""
    product = ProductFactory()
    StockTakeFactory(product=product, stock_take_date=at(1), quantity_on_hand=30)
    line(product, 2, ODS.ALLOCATED, order__invoice_date=at(2))
    line(product, 5, ODS.SHIPPED, order__invoice_date=at(3))
    # 30 - 2 - 5 = 23
    assert inventory.product_available(product) == 23
    assert annotated(product).product_available == 23


def test_latest_stock_take_or_the_added_date_is_the_starting_point():
    """R-inventory-002: the latest stock take counts; a product without one counts
    from its added date, and the opening zero stock take written later keeps every
    figure."""
    counted = ProductFactory()
    StockTakeFactory(product=counted, stock_take_date=at(3), quantity_on_hand=8)
    StockTakeFactory(product=counted, stock_take_date=at(5), quantity_on_hand=4)
    assert inventory.last_stock_take(counted) == (at(5), 4)
    assert annotated(counted).last_stock_take_quantity == 4

    product = ProductFactory()
    Product.objects.filter(pk=product.pk).update(added_on=at(1, month=2))
    po_line(product, 6, POS.RECEIVED, received_date=at(3, month=2))  # +6
    line(product, 2, ODS.INVOICED, order__invoice_date=at(5, month=2))  # -2
    line(product, 9, ODS.INVOICED, order__invoice_date=at(20))  # before: ignored
    # no stock take: 0 + 6 - 2 = 4, counted from the added date
    assert inventory.last_stock_take(product) == (None, 0)
    assert inventory.stock_as_of(product) == at(1, month=2)
    assert inventory.product_available(product) == 4
    assert annotated(product).product_available == 4

    opening = inventory.ensure_opening_stock_take(product)
    assert opening is not None
    assert (opening.stock_take_date, opening.quantity_on_hand) == (at(1, month=2), 0)
    assert inventory.ensure_opening_stock_take(product) is None
    assert StockTake.objects.filter(product=product).count() == 1
    assert inventory.product_available(product) == 4
    assert annotated(product).product_available == 4


def test_allocated_and_no_stock_quantities():
    """R-inventory-003: allocated and no-stock quantities sum the order lines in those
    two line statuses; a product without such lines has zero."""
    product = ProductFactory()
    line(product, 5, ODS.ALLOCATED)
    line(product, 2, ODS.ALLOCATED)
    line(product, 4, ODS.NO_STOCK)
    line(product, 9, ODS.ON_ORDER)
    line(product, 7, ODS.NEW)
    line(product, 3, ODS.INVOICED)
    assert inventory.product_allocated(product) == 7  # 5 + 2
    assert inventory.product_no_stock(product) == 4
    row = annotated(product)
    assert (row.product_allocated, row.product_no_stock) == (7, 4)

    idle = ProductFactory()
    assert (inventory.product_allocated(idle), inventory.product_no_stock(idle)) == (
        0,
        0,
    )
    row = annotated(idle)
    assert (row.product_allocated, row.product_no_stock) == (0, 0)


def test_on_order_counts_approved_purchase_orders_only():
    """R-inventory-004: on order = purchase-order line quantities of Approved purchase
    orders; New, Submitted, Received and Closed ones do not count."""
    product = ProductFactory()
    po_line(product, 10, POS.APPROVED)
    po_line(product, 3, POS.APPROVED)
    po_line(product, 7, POS.NEW)
    po_line(product, 8, POS.SUBMITTED)
    po_line(product, 9, POS.RECEIVED, received_date=at(2))
    po_line(product, 11, POS.CLOSED, received_date=at(2))
    assert inventory.product_on_order(product) == 13  # 10 + 3
    assert annotated(product).product_on_order == 13


def test_quantity_to_sell_is_stock_minus_allocated_and_can_be_negative():
    """R-inventory-005: quantity to sell = physical stock - allocated quantity; it can
    be negative."""
    product = ProductFactory()
    StockTakeFactory(product=product, stock_take_date=at(1), quantity_on_hand=5)
    line(product, 8, ODS.ALLOCATED)
    # 5 - 8 = -3
    assert inventory.product_to_sell(product) == -3
    assert annotated(product).product_to_sell == -3


@pytest.mark.parametrize(
    ("counted", "allocated", "no_stock", "approved", "target", "minimum", "expected"),
    [
        # supply 30 + 0 covers demand 0 + 20: the minimum, 10
        (30, 0, 0, 0, 20, 10, 10),
        # supply 2 + 0 against demand 5 + 20: shortfall 23 above the minimum 10
        (2, 0, 5, 0, 20, 10, 23),
        # supply (10 - 4) + 6 = 12 against demand 0 + 15: shortfall 3, raised to 10
        (10, 4, 0, 6, 15, 10, 10),
        # blank target counts as 0, blank minimum as 1: supply 0 covers demand 0
        (0, 0, 0, 0, None, None, 1),
        # blank target 0, demand 4 no stock, supply 1: shortfall 3 above minimum 1
        (1, 0, 4, 0, None, None, 3),
    ],
)
def test_suggested_reorder_quantity(  # noqa: PLR0913, PLR0917 (one per column)
    counted,
    allocated,
    no_stock,
    approved,
    target,
    minimum,
    expected,
):
    """R-inventory-006: minimum reorder quantity when quantity to sell + on order covers
    no stock + target level, otherwise the shortfall raised to the minimum."""
    product = ProductFactory(target_level=target, minimum_reorder_quantity=minimum)
    StockTakeFactory(product=product, stock_take_date=at(1), quantity_on_hand=counted)
    if allocated:
        line(product, allocated, ODS.ALLOCATED)
    if no_stock:
        line(product, no_stock, ODS.NO_STOCK)
    if approved:
        po_line(product, approved, POS.APPROVED)
    assert inventory.product_reorder_quantity(product) == expected
    assert annotated(product).product_reorder_quantity == expected
    assert inventory.stock_levels(product).reorder_quantity == expected


def test_allocation_oldest_order_first_never_part_allocated():
    """R-inventory-007: lines in Allocated, No Stock or On Order are re-evaluated oldest
    order date first (lower order number on a tie): Allocated when the whole quantity
    fits the unallocated stock, else On Order when it fits stock + on order, else No
    Stock; a later smaller line can be allocated when an earlier larger one could
    not."""
    product = ProductFactory()
    StockTakeFactory(product=product, stock_take_date=at(1), quantity_on_hand=10)
    po_line(product, 5, POS.APPROVED)  # on order 5
    a = line(product, 4, ODS.ALLOCATED, order__order_date=at(2))
    b = line(product, 8, ODS.NO_STOCK, order__order_date=at(3))
    # same order date: x has the lower order number, so it goes first
    x = line(product, 5, ODS.ON_ORDER, order__order_date=at(4))
    y = line(product, 2, ODS.NO_STOCK, order__order_date=at(4))
    late = line(product, 3, ODS.NO_STOCK, order__order_date=at(5))
    untouched = line(product, 50, ODS.NEW, order__order_date=at(1))
    assert x.order_id < y.order_id
    # stock 10, stock + on order 15
    # a 4 <= 10: Allocated (stock 6, total 11)
    # b 8 > 6, 8 <= 11: On Order (total 3)
    # x 5 <= 6: Allocated (stock 1, total -2)
    # y 2 > 1 and 2 > -2: No Stock
    # late 3: No Stock
    changed = inventory.allocate_inventory(product)
    statuses = {
        name: OrderDetail.objects.get(pk=obj.pk).order_detail_status_id
        for name, obj in {
            "a": a,
            "b": b,
            "x": x,
            "y": y,
            "late": late,
            "untouched": untouched,
        }.items()
    }
    assert statuses == {
        "a": ODS.ALLOCATED,
        "b": ODS.ON_ORDER,
        "x": ODS.ALLOCATED,
        "y": ODS.NO_STOCK,
        "late": ODS.NO_STOCK,
        "untouched": ODS.NEW,
    }
    assert {obj.pk for obj in changed} == {b.pk, x.pk}


def test_allocation_lets_a_smaller_later_line_through():
    """R-inventory-007: a later smaller line is allocated although an earlier larger
    line could not be."""
    product = ProductFactory()
    StockTakeFactory(product=product, stock_take_date=at(1), quantity_on_hand=3)
    big = line(product, 5, ODS.ALLOCATED, order__order_date=at(2))
    small = line(product, 3, ODS.NO_STOCK, order__order_date=at(3))
    inventory.allocate_inventory(product)
    big.refresh_from_db()
    small.refresh_from_db()
    # big 5 > 3 and 5 > 3 + 0 on order: No Stock; small 3 <= 3: Allocated
    assert big.order_detail_status_id == ODS.NO_STOCK
    assert small.order_detail_status_id == ODS.ALLOCATED


# ---------------------------------------------------------------- purchasing


@pytest.mark.usefixtures("new_status")
def test_new_purchase_order_starts_new():
    """R-purchasing-001: a purchase order starts in status New, by hand or by a
    reorder."""
    vendor = VendorFactory()
    by_hand = purchasing.start_purchase_order(vendor, status_id=POS.APPROVED)
    assert by_hand.status_id == POS.NEW
    product = ProductFactory()
    reordered = purchasing.reorder_into_purchase_order(product, vendor, 4)
    # the vendor's oldest New purchase order is the one just started
    assert reordered.purchase_order_id == by_hand.pk
    other = purchasing.reorder_into_purchase_order(product, VendorFactory(), 4)
    assert other.purchase_order.status_id == POS.NEW


@pytest.mark.usefixtures("new_status")
def test_reorder_goes_to_the_vendors_oldest_new_purchase_order():
    """R-inventory-020: a reorder adds the product to the vendor's oldest New purchase
    order (quantity added when the product is on it), at the product's standard unit
    cost; without a New one, a new purchase order with that single line."""
    vendor = VendorFactory()
    PurchaseOrderFactory(vendor=vendor, status__status_id=POS.APPROVED)
    oldest = PurchaseOrderFactory(vendor=vendor, status__status_id=POS.NEW)
    PurchaseOrderFactory(vendor=vendor, status__status_id=POS.NEW)
    product = ProductFactory(standard_unit_cost=Decimal("2.5000"))

    first = purchasing.reorder_into_purchase_order(product, vendor, 15)
    assert first.purchase_order_id == oldest.pk
    assert (first.quantity, first.unit_cost) == (15, Decimal("2.5000"))
    again = purchasing.reorder_into_purchase_order(product.pk, vendor.pk, 5)
    assert again.pk == first.pk
    assert again.quantity == 20  # 15 + 5

    loner = VendorFactory()
    before = PurchaseOrder.objects.count()
    created = purchasing.reorder_into_purchase_order(product, loner, 7)
    assert PurchaseOrder.objects.count() == before + 1
    assert created.purchase_order.vendor_id == loner.pk
    assert created.purchase_order.status_id == POS.NEW
    assert list(
        created.purchase_order.lines.values_list("product_id", "quantity"),
    ) == [(product.pk, 7)]


def test_one_line_per_product_quantity_added_cost_kept():
    """R-purchasing-020: adding a product already on the purchase order adds the
    quantity to its line and keeps the line's unit cost; a new product gets a new
    line."""
    purchase_order = PurchaseOrderFactory()
    product = ProductFactory()
    first = purchasing.add_purchase_order_line(
        purchase_order,
        product,
        6,
        Decimal("3.2500"),
    )
    second = purchasing.add_purchase_order_line(
        purchase_order.pk,
        product.pk,
        4,
        Decimal("9.9900"),
    )
    assert second.pk == first.pk
    assert (second.quantity, second.unit_cost) == (10, Decimal("3.2500"))
    other = purchasing.add_purchase_order_line(
        purchase_order,
        ProductFactory(),
        2,
        Decimal("1.0000"),
    )
    assert other.pk != first.pk
    assert purchase_order.lines.count() == 2


# ---------------------------------------------------------------- sales


def test_line_amount_is_quantity_times_one_minus_discount_times_price():
    """R-orders-022: a line's price is quantity x (1 - discount) x unit price; a blank
    discount gives no amount."""
    priced = line(ProductFactory(), 3, discount=0.25, unit_price=Decimal("4.0000"))
    blank = line(ProductFactory(), 2, discount=None, unit_price=Decimal("4.0000"))
    # 3 x 0.75 x 4 = 9
    assert sales.line_amount(priced) == 9.0
    assert sales.line_amount(blank) is None
    amounts = dict(
        sales.with_line_amount(OrderDetail.objects.all()).values_list(
            "pk",
            "line_amount",
        ),
    )
    assert amounts == {priced.pk: 9.0, blank.pk: None}


def test_order_total_sums_the_lines_and_is_blank_without_lines():
    """R-orders-023: an order's total is the sum of quantity x (1 - discount) x unit
    price over its lines, without tax and shipping; an order without lines has no
    total."""
    order = OrderFactory(shipping_fee=Decimal("7.0000"), tax_rate=0.1)
    line(ProductFactory(), 3, order=order, discount=0.25, unit_price=Decimal(4))
    line(ProductFactory(), 2, order=order, discount=0.0, unit_price=Decimal("2.5"))
    empty = OrderFactory()
    # 3 x 0.75 x 4 + 2 x 1 x 2.5 = 9 + 5 = 14
    assert sales.order_total(order) == 14.0
    assert sales.order_total(empty) is None
    totals = dict(
        sales.with_order_total(Order.objects.all()).values_list(
            "pk",
            "order_total",
        ),
    )
    assert totals == {order.pk: 14.0, empty.pk: None}


def test_line_amounts_feed_the_monthly_product_sales():
    """R-reports-005: monthly sales per product sum quantity x unit price x (1 -
    discount) over the order lines; grouping the lines by product and month works on
    both databases."""
    product = ProductFactory()
    line(product, 2, discount=0.5, unit_price=Decimal(10), order__order_date=at(3))
    line(product, 1, discount=0.0, unit_price=Decimal(10), order__order_date=at(9))
    line(
        product,
        4,
        discount=0.0,
        unit_price=Decimal(10),
        order__order_date=at(9, month=2),
    )
    rows = (
        OrderDetail.objects.filter(product=product)
        .values("order__order_date__month")
        .annotate(total=Sum(sales.line_amount_expression()))
        .order_by("order__order_date__month")
    )
    # January: 2 x 0.5 x 10 + 1 x 1 x 10 = 20; February: 4 x 10 = 40
    assert [(r["order__order_date__month"], r["total"]) for r in rows] == [
        (1, 20.0),
        (2, 40.0),
    ]


def test_sales_per_employee_sum_order_totals():
    """R-reports-004: sales per salesperson are the sum of their orders' totals; an
    order without lines adds nothing. Grouped over the order lines, as SQL Server
    refuses an aggregate over the order_total subquery."""
    seller = EmployeeFactory()
    first = OrderFactory(employee=seller)
    line(ProductFactory(), 3, order=first, discount=0.25, unit_price=Decimal(4))
    second = OrderFactory(employee=seller)
    line(ProductFactory(), 2, order=second, discount=0.0, unit_price=Decimal("2.5"))
    OrderFactory(employee=seller)  # no lines
    other = OrderFactory()
    line(ProductFactory(), 1, order=other, discount=0.0, unit_price=Decimal(100))
    rows = dict(
        OrderDetail.objects.values("order__employee")
        .annotate(total=Sum(sales.line_amount_expression()))
        .values_list("order__employee", "total"),
    )
    # the seller sums 9 and 5 to 14, the other salesperson has 100
    assert rows == {seller.pk: 14.0, other.employee_id: 100.0}
    orders = sales.with_order_total(seller.orders.all())
    assert orders.aggregate(total=Sum("order_total"))["total"] == 14.0


# ---------------------------------------------------------------- people


def test_full_name_is_first_then_last():
    """R-orders-043: an employee's full name is first name, a space, last name."""
    employee = EmployeeFactory(first_name="Ada", last_name="Example")
    assert people.full_name(employee) == "Ada Example"
    row = people.with_full_name(Employee.objects.filter(pk=employee.pk)).get()
    assert row.full_name_fnln == "Ada Example"
    order = OrderFactory(employee=employee)
    names = people.with_full_name(
        Order.objects.filter(pk=order.pk),
        prefix="employee__",
        name="salesperson",
    ).values_list("salesperson", flat=True)
    assert list(names) == ["Ada Example"]
    assert people.full_name(None) is None


def test_signed_in_employee_is_the_salesperson(django_user_model):
    """R-orders-001: the salesperson of a new order is the signed-in employee, the
    employee whose e-mail address is the user's (case ignored)."""
    employee = EmployeeFactory(email_address="pat.seller@example.com")
    EmployeeFactory(email_address="someone.else@example.com")
    user = django_user_model.objects.create_user(email="Pat.Seller@Example.com")
    assert people.signed_in_employee(user) == employee
    stranger = django_user_model.objects.create_user(email="nobody@example.com")
    assert people.signed_in_employee(stranger) is None
    assert people.signed_in_employee(AnonymousUser()) is None


def test_signed_in_employee_submits(django_user_model):
    """R-purchasing-004: the submitter recorded on a purchase order is the signed-in
    user's employee record."""
    employee = EmployeeFactory(email_address="sam.buyer@example.com")
    user = django_user_model.objects.create_user(email="sam.buyer@example.com")
    purchase_order = PurchaseOrderFactory(submitted_by=people.signed_in_employee(user))
    assert purchase_order.submitted_by == employee


def test_stamps_carry_the_signed_in_employees_full_name(django_user_model):
    """R-orders-031: rows written for a signed-in employee are stamped with the
    employee's first and last name; a user without an employee record with their own
    name or e-mail address; nobody signed in with System."""
    EmployeeFactory(
        first_name="Ada",
        last_name="Example",
        email_address="ada@example.com",
    )
    ada = django_user_model.objects.create_user(email="ada@example.com")
    named = django_user_model.objects.create_user(email="x@example.com", name="Xu")
    bare = django_user_model.objects.create_user(email="y@example.com")
    assert people.stamp_name(ada) == "Ada Example"
    assert people.stamp_name(named) == "Xu"
    assert people.stamp_name(bare) == "y@example.com"
    assert people.stamp_name(AnonymousUser()) == SYSTEM
    with people.acting_for(ada):
        product = ProductFactory()
    product.refresh_from_db()
    assert (product.added_by, product.modified_by) == ("Ada Example", "Ada Example")


# ---------------------------------------------------------------- settings


@pytest.mark.parametrize(
    ("stored", "expected"),
    [("75", 0.075), ("87.5", 0.0875), ("0", 0.0), ("", 0.0), (None, 0.0)],
)
def test_default_sales_tax_rate_is_stored_in_thousandths(stored, expected):
    """R-orders-001: the default sales tax rate is stored as whole thousandths and
    divided by 1000 when read; a blank setting reads as 0."""
    SystemSettingFactory(
        setting_id=SystemSettingCode.SALES_TAX_RATE,
        setting_value=stored,
    )
    assert system_settings.sales_tax_rate() == expected


def test_vendor_tax_rate_is_one_system_wide_setting():
    """R-purchasing-010: the vendor tax rate is one system-wide setting, read in
    thousandths like the sales tax rate; a missing setting reads as 0."""
    assert system_settings.vendor_tax_rate() == 0.0
    SystemSettingFactory(
        setting_id=SystemSettingCode.VENDOR_TAX_RATE,
        setting_value="62.5",
    )
    SystemSettingFactory(
        setting_id=SystemSettingCode.SALES_TAX_RATE,
        setting_value="10",
    )
    assert system_settings.vendor_tax_rate() == 0.0625
    assert system_settings.sales_tax_rate() == 0.01
