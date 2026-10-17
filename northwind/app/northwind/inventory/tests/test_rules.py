"""Rule tests of the Products and Inventory area.

One test per rule of this area whose test_kind is rule (analysis/rules.json), with
the rule id first in the docstring, data from legacy/factories.py and the expected
values worked out by hand in the test. Never golden files or seed outputs.
"""

import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import get_resolver

from northwind.core.roles import role_names
from northwind.core.roles import role_permissions
from northwind.legacy import factories as f
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Product
from northwind.legacy.models import ProductCategory
from northwind.legacy.models import ProductVendor
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail
from northwind.legacy.models import StockTake

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.inventory import services
from northwind.inventory.views import StockTakeView

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("fixed_codes")]

T0 = dt.datetime(2024, 3, 1, 9, 0)  # noqa: DTZ001 (the app runs with USE_TZ False)
DAY = dt.timedelta(days=1)

ALLOCATED = OrderDetailStatusCode.ALLOCATED
NO_STOCK = OrderDetailStatusCode.NO_STOCK
ON_ORDER = OrderDetailStatusCode.ON_ORDER
LINE_NEW = OrderDetailStatusCode.NEW
APPROVED = PurchaseOrderStatusCode.APPROVED
PO_NEW = PurchaseOrderStatusCode.NEW
SUBMITTED = PurchaseOrderStatusCode.SUBMITTED
RECEIVED = PurchaseOrderStatusCode.RECEIVED


# ---------------------------------------------------------------- helpers


def product(**fields) -> Product:
    """A product counted at T0 with `counted` (default 12) on hand."""
    counted = fields.pop("counted", 12)
    item = f.ProductFactory(**fields)
    if counted is not None:
        f.StockTakeFactory(product=item, stock_take_date=T0, quantity_on_hand=counted)
    return item


def order_line(item, quantity, status=LINE_NEW, *, order_date=T0, invoiced=None):
    order = f.OrderFactory(order_date=order_date, invoice_date=invoiced)
    return f.OrderDetailFactory(
        order=order,
        product=item,
        quantity=quantity,
        order_detail_status=f.OrderDetailStatusFactory(order_detail_status_id=status),
    )


def po_line(item, quantity, status=APPROVED, *, received=None, vendor=None):
    purchase_order = f.PurchaseOrderFactory(
        status=f.PurchaseOrderStatusFactory(status_id=status),
        **({"vendor": vendor} if vendor is not None else {}),
    )
    return f.PurchaseOrderDetailFactory(
        purchase_order=purchase_order,
        product=item,
        quantity=quantity,
        received_date=received,
    )


def status_of(line: OrderDetail) -> int:
    line.refresh_from_db()
    return line.order_detail_status_id


def staff_user(user_with_role, first: str, last: str):
    """A signed-in user linked by e-mail address to an employee record."""
    email = f"{first}.{last}@example.com".lower()
    f.EmployeeFactory(first_name=first, last_name=last, email_address=email)
    return user_with_role("staff", email=email)


# ---------------------------------------------------------------- stock figures


def test_physical_stock_counts_from_the_latest_stock_take():
    """R-inventory-001: physical stock = latest count + purchase-order lines received
    at or after it - lines of orders invoiced at or after it, whatever the line
    status; unreceived lines and uninvoiced orders do not count."""
    item = product(counted=12)
    f.StockTakeFactory(product=item, stock_take_date=T0 - DAY, quantity_on_hand=99)
    po_line(item, 10, RECEIVED, received=T0 + DAY)  # counted
    po_line(item, 50, RECEIVED, received=T0 - DAY)  # before the count
    po_line(item, 7, APPROVED)  # not received
    order_line(item, 3, LINE_NEW, invoiced=T0 + DAY)  # invoiced: sold, any status
    order_line(item, 4, ALLOCATED, invoiced=T0 - DAY)  # invoiced before the count
    order_line(item, 5, ALLOCATED)  # not invoiced
    assert services.product_stock_levels(item).available == 12 + 10 - 3


def test_latest_stock_take_and_opening_stock_take():
    """R-inventory-002: the latest stock take counts; a new product gets an opening
    stock take of zero dated at its creation, and a product without one gets it the
    first time its stock is allocated, dated at its added date."""
    item = product(counted=12)
    f.StockTakeFactory(product=item, stock_take_date=T0 + DAY, quantity_on_hand=4)
    levels = services.product_stock_levels(item)
    assert levels.last_stock_take_date == T0 + DAY
    assert levels.available == 4  # noqa: PLR2004 (the later count)

    category = f.ProductCategoryFactory(product_category_code="OPN")
    created = services.save_product(
        Product(),
        {
            "product_name": "Opening stock product",
            "product_category": category,
            "standard_unit_cost": Decimal("1.0000"),
            "unit_price": Decimal("2.0000"),
            "discontinued": False,
        },
    )
    opening = list(StockTake.objects.filter(product=created))
    assert [(s.quantity_on_hand, s.stock_take_date) for s in opening] == [
        (0, created.added_on),
    ]

    loaded = product(counted=None)
    assert not StockTake.objects.filter(product=loaded).exists()
    services.allocate_inventory(loaded)
    take = StockTake.objects.get(product=loaded)
    assert (take.quantity_on_hand, take.stock_take_date) == (0, loaded.added_on)


def test_allocated_and_no_stock_quantities():
    """R-inventory-003: allocated = quantity on Allocated lines, no-stock = quantity on
    No Stock lines; zero without such lines."""
    item = product()
    order_line(item, 3, ALLOCATED)
    order_line(item, 4, ALLOCATED)
    order_line(item, 5, NO_STOCK)
    order_line(item, 2, LINE_NEW)
    levels = services.product_stock_levels(item)
    assert (levels.allocated, levels.no_stock) == (7, 5)
    empty = services.product_stock_levels(product())
    assert (empty.allocated, empty.no_stock) == (0, 0)


def test_on_order_counts_approved_purchase_orders_only():
    """R-inventory-004: only lines of Approved purchase orders are on order."""
    item = product()
    po_line(item, 10, APPROVED)
    po_line(item, 20, PO_NEW)
    po_line(item, 30, SUBMITTED)
    po_line(item, 40, RECEIVED)
    assert services.product_stock_levels(item).on_order == 10  # noqa: PLR2004


def test_quantity_to_sell_can_be_negative():
    """R-inventory-005: quantity to sell = physical stock - allocated, and can be
    negative."""
    item = product(counted=2)
    order_line(item, 5, ALLOCATED)
    levels = services.product_stock_levels(item)
    assert (levels.available, levels.allocated, levels.to_sell) == (2, 5, -3)


@pytest.mark.parametrize(
    ("target", "minimum", "expected"),
    [
        (20, 10, 10),  # shortfall 20 - 12 = 8, raised to the minimum 10
        (50, 10, 38),  # shortfall 50 - 12 = 38
        (5, 10, 10),  # supply 12 covers demand 5: the minimum
        (None, None, 1),  # blank target counts 0, blank minimum counts 1
    ],
)
def test_suggested_reorder_quantity(target, minimum, expected):
    """R-inventory-006: supply (to sell + on order) against demand (no stock +
    target): the minimum when covered, else the shortfall raised to the minimum."""
    item = product(counted=12, target_level=target, minimum_reorder_quantity=minimum)
    assert services.product_stock_levels(item).reorder_quantity == expected


def test_suggested_reorder_quantity_counts_no_stock_and_approved_orders():
    """R-inventory-006: no-stock lines add to demand, Approved purchase orders to
    supply; New ones do not."""
    item = product(counted=12, target_level=20, minimum_reorder_quantity=1)
    order_line(item, 9, NO_STOCK)  # demand 20 + 9 = 29
    po_line(item, 5, APPROVED)  # supply 12 + 5 = 17
    po_line(item, 100, PO_NEW)  # not on order
    assert services.product_stock_levels(item).reorder_quantity == 29 - 17


# ---------------------------------------------------------------- allocation


def test_allocation_whole_lines_oldest_order_first():
    """R-inventory-007: waiting lines oldest order first; Allocated when the whole
    line fits the unallocated stock, else On Order when it fits stock + on order,
    else No Stock; a later smaller line can be allocated."""
    item = product(counted=10)
    po_line(item, 5, APPROVED)  # on order 5
    first = order_line(item, 6, NO_STOCK, order_date=T0 + 1 * DAY)  # 10 -> 4 left
    second = order_line(item, 8, ALLOCATED, order_date=T0 + 2 * DAY)  # fits 4 + 5
    third = order_line(item, 3, ON_ORDER, order_date=T0 + 3 * DAY)  # fits 4
    fourth = order_line(item, 2, ALLOCATED, order_date=T0 + 4 * DAY)  # nothing left
    untouched = order_line(item, 1, LINE_NEW, order_date=T0)
    changed = services.allocate_inventory(item)
    assert [status_of(line) for line in (first, second, third, fourth)] == [
        ALLOCATED,
        ON_ORDER,
        ALLOCATED,
        NO_STOCK,
    ]
    assert status_of(untouched) == LINE_NEW
    assert {line.pk for line in changed} == {
        first.pk,
        second.pk,
        third.pk,
        fourth.pk,
    }


def test_allocation_breaks_a_date_tie_by_order_number():
    """R-inventory-007: on the same order date the lower order number goes first."""
    item = product(counted=5)
    lower = order_line(item, 5, NO_STOCK, order_date=T0)
    higher = order_line(item, 5, NO_STOCK, order_date=T0)
    assert lower.order_id < higher.order_id
    services.allocate_inventory(item)
    assert (status_of(lower), status_of(higher)) == (ALLOCATED, NO_STOCK)


def test_saving_a_stock_take_reallocates():
    """R-inventory-008: a new stock take re-runs allocation for the product."""
    item = product(counted=0)
    waiting = order_line(item, 4, NO_STOCK)
    result = services.record_stock_take(item, 5, confirmed=True)
    assert status_of(waiting) == ALLOCATED
    assert [line.pk for line in result.reallocated] == [waiting.pk]


# ---------------------------------------------------------------- stock takes


def test_stock_take_is_dated_by_the_system_with_the_expected_quantity():
    """R-inventory-009: the date is the moment of saving, the expected quantity is
    the physical stock then; the count is required and neither can be negative."""
    item = product(counted=12)
    po_line(item, 3, RECEIVED, received=T0 + DAY)  # physical stock 15
    before = dt.datetime.now().replace(microsecond=0)  # noqa: DTZ005
    result = services.record_stock_take(item, 15)
    after = dt.datetime.now()  # noqa: DTZ005
    take = result.stock_take
    assert (take.quantity_on_hand, take.expected_quantity) == (15, 15)
    assert before <= take.stock_take_date <= after
    oversold = product(counted=1)
    order_line(oversold, 3, LINE_NEW, invoiced=T0 + DAY)  # physical stock -2
    count = StockTake.objects.count()
    for counted in (None, "", -1):
        with pytest.raises(ValidationError, match="R-inventory-009"):
            services.record_stock_take(item, counted, confirmed=True)
    with pytest.raises(ValidationError, match="R-inventory-009"):
        services.record_stock_take(oversold, 0, confirmed=True)
    assert StockTake.objects.count() == count


def test_a_count_that_differs_needs_confirmation():
    """R-inventory-010: a count that differs from the expected quantity is refused
    with both figures unless confirmed; nothing is saved when declined."""
    item = product(counted=12)
    count = StockTake.objects.count()
    with pytest.raises(services.StockTakeMismatchError) as refused:
        services.record_stock_take(item, 9)
    assert (refused.value.counted, refused.value.expected) == (9, 12)
    assert StockTake.objects.count() == count
    services.record_stock_take(item, 9, confirmed=True)
    assert StockTake.objects.count() == count + 1


def test_stock_takes_are_append_only():
    """R-inventory-011: no role may change or delete a stock take, and the area has
    no route that edits or deletes one; recording adds a new row and leaves the
    earlier ones as they were."""
    for role in role_names():
        granted = role_permissions(role)
        assert "legacy.change_stocktake" not in granted
        assert "legacy.delete_stocktake" not in granted
        assert "legacy.add_stocktake" in granted
    names = [
        pattern.name
        for pattern in get_resolver("northwind.inventory.urls").url_patterns
    ]
    assert [name for name in names if "stock" in name.lower()] == [
        "form_sfrmProductDetail_StockTake",
    ]
    assert not hasattr(StockTakeView, "put")
    assert not hasattr(StockTakeView, "delete")
    item = product(counted=12)
    earlier = StockTake.objects.get(product=item)
    services.record_stock_take(item, 12)
    assert StockTake.objects.filter(product=item).count() == 2  # noqa: PLR2004
    again = StockTake.objects.get(pk=earlier.pk)
    assert (again.quantity_on_hand, again.stock_take_date) == (12, T0)


# ---------------------------------------------------------------- products


def product_data(category, **overrides):
    data = {
        "product_name": "Rule product",
        "product_category": category,
        "standard_unit_cost": Decimal("3.0000"),
        "unit_price": Decimal("5.0000"),
        "discontinued": False,
        "target_level": 20,
        "minimum_reorder_quantity": 10,
    }
    data.update(overrides)
    return data


def test_product_required_fields_positive_cost_and_unique_name():
    """R-inventory-012: required fields, a standard unit cost above zero, and a
    unique name (the code is unique and built, R-inventory-013); nothing is saved
    when refused."""
    category = f.ProductCategoryFactory()
    f.ProductFactory(product_name="Taken name")
    count = Product.objects.count()
    for overrides in (
        {"product_name": ""},
        {"product_category": None},
        {"unit_price": None},
        {"standard_unit_cost": None},
        {"standard_unit_cost": Decimal("0.0000")},
        {"standard_unit_cost": Decimal("-1.0000")},
        {"discontinued": None},
        {"product_name": "Taken name"},
    ):
        with pytest.raises(ValidationError, match="R-inventory-012"):
            services.save_product(Product(), product_data(category, **overrides))
    assert Product.objects.count() == count
    services.save_product(Product(), product_data(category))
    assert Product.objects.count() == count + 1


def test_product_code_is_built_from_the_category():
    """R-inventory-013: NWT + category code + '-' + product number, rebuilt when the
    category changes and kept otherwise."""
    beverages = f.ProductCategoryFactory(product_category_code="BEV")
    dried = f.ProductCategoryFactory(product_category_code="DRY")
    item = services.save_product(Product(), product_data(beverages))
    assert item.product_code == f"NWTBEV-{item.pk}"
    services.save_product(item, {"product_category": dried})
    item.refresh_from_db()
    assert item.product_code == f"NWTDRY-{item.pk}"
    services.save_product(item, {"unit_price": Decimal("6.0000")})
    item.refresh_from_db()
    assert item.product_code == f"NWTDRY-{item.pk}"


def test_category_code_is_fixed_once_products_use_it():
    """R-inventory-014: a category's code cannot change while products belong to it;
    name and code are required and unique."""
    used = f.ProductCategoryFactory(product_category_code="USE")
    f.ProductFactory(product_category=used)
    with pytest.raises(ValidationError, match="R-inventory-014"):
        services.save_category(used, {"product_category_code": "NEW"})
    used.refresh_from_db()
    assert used.product_category_code == "USE"
    free = f.ProductCategoryFactory(product_category_code="FRE")
    services.save_category(free, {"product_category_code": "FRX"})
    free.refresh_from_db()
    assert free.product_category_code == "FRX"
    for data in (
        {"product_category_name": "", "product_category_code": "AAA"},
        {"product_category_name": "Only name", "product_category_code": ""},
        {"product_category_name": "Other", "product_category_code": "USE"},
        {"product_category_name": used.product_category_name},
    ):
        data.setdefault("product_category_code", "ZZZ")
        with pytest.raises(ValidationError, match="R-inventory-014"):
            services.save_category(ProductCategory(), data)


def test_category_with_products_cannot_be_deleted():
    """R-inventory-015: a category is deleted only when no product belongs to it."""
    used = f.ProductCategoryFactory()
    f.ProductFactory(product_category=used)
    with pytest.raises(ValidationError, match="R-inventory-015"):
        services.delete_category(used)
    assert ProductCategory.objects.filter(pk=used.pk).exists()
    empty = f.ProductCategoryFactory()
    services.delete_category(empty)
    assert not ProductCategory.objects.filter(pk=empty.pk).exists()


def test_product_delete_is_blocked_by_lines_and_needs_confirmation():
    """R-inventory-016: refused while on an order line or a purchase-order line, or
    without confirmation (nothing deleted); confirmed, the product goes with its
    stock takes and vendor links in one step."""
    on_order = product()
    order_line(on_order, 1)
    with pytest.raises(ValidationError, match="order line"):
        services.delete_product(on_order, confirmed=True)
    on_po = product()
    po_line(on_po, 1)
    with pytest.raises(ValidationError, match="purchase-order line"):
        services.delete_product(on_po, confirmed=True)
    free = product()
    f.ProductVendorFactory(product=free)
    with pytest.raises(ValidationError, match="R-inventory-016"):
        services.delete_product(free, confirmed=False)
    assert StockTake.objects.filter(product=free).count() == 1
    assert ProductVendor.objects.filter(product=free).count() == 1
    services.delete_product(free, confirmed=True)
    assert not Product.objects.filter(pk=free.pk).exists()
    assert not StockTake.objects.filter(product_id=free.pk).exists()
    assert not ProductVendor.objects.filter(product_id=free.pk).exists()
    assert Product.objects.filter(pk__in=[on_order.pk, on_po.pk]).count() == 2  # noqa: PLR2004


# ---------------------------------------------------------------- reorder


def test_reorder_opens_the_outstanding_purchase_order():
    """R-inventory-017: with an on-order quantity, the Approved, New or Submitted
    purchase order holding the product is opened and nothing changes."""
    item = product(counted=0, target_level=50)
    f.ProductVendorFactory(product=item)
    approved = po_line(item, 10, APPROVED)
    po_line(item, 3, PO_NEW)
    purchase_orders = PurchaseOrder.objects.count()
    lines = list(PurchaseOrderDetail.objects.values_list("pk", "quantity"))
    result = services.reorder_product(item)
    assert result.opened_existing
    assert result.purchase_order.pk == approved.purchase_order_id
    assert PurchaseOrder.objects.count() == purchase_orders
    assert list(PurchaseOrderDetail.objects.values_list("pk", "quantity")) == lines


def test_reorder_without_on_order_does_not_open_a_new_purchase_order():
    """R-inventory-017: a New purchase order alone puts nothing on order, so the
    reorder goes ahead (R-inventory-020 adds to that New order)."""
    item = product(counted=0, target_level=15, minimum_reorder_quantity=1)
    link = f.ProductVendorFactory(product=item)
    waiting = po_line(item, 4, PO_NEW, vendor=link.vendor)
    result = services.reorder_product(item)
    assert not result.opened_existing
    waiting.refresh_from_db()
    assert waiting.quantity == 4 + 15


def test_reorder_needs_a_linked_vendor_and_a_choice_among_several():
    """R-inventory-018: no vendor refuses; one vendor is used; with several the user
    must pick one of them."""
    item = product(counted=0, target_level=5, minimum_reorder_quantity=1)
    with pytest.raises(ValidationError, match="R-inventory-018"):
        services.reorder_product(item)
    only = f.ProductVendorFactory(product=item).vendor
    assert services.reorder_product(item).purchase_order.vendor_id == only.pk
    other = product(counted=0, target_level=5, minimum_reorder_quantity=1)
    first = f.ProductVendorFactory(product=other).vendor
    second = f.ProductVendorFactory(product=other).vendor
    stranger = f.VendorFactory()
    for choice in (None, stranger.pk):
        with pytest.raises(ValidationError, match="R-inventory-018"):
            services.reorder_product(other, vendor=choice)
    result = services.reorder_product(other, vendor=second.pk)
    assert result.purchase_order.vendor_id == second.pk
    assert not PurchaseOrder.objects.filter(vendor=first).exists()


def test_reorder_quantity_suggested_minimum_or_asked():
    """R-inventory-019: the suggested quantity; when zero the minimum; when that is
    zero too, the user's quantity, and none or zero cancels."""
    suggested = product(counted=12, target_level=50, minimum_reorder_quantity=10)
    f.ProductVendorFactory(product=suggested)
    assert services.reorder_product(suggested, quantity=3).quantity == 50 - 12
    asked = product(counted=12, target_level=0, minimum_reorder_quantity=0)
    f.ProductVendorFactory(product=asked)
    count = PurchaseOrderDetail.objects.count()
    for quantity in (None, 0):
        with pytest.raises(ValidationError, match="R-inventory-019"):
            services.reorder_product(asked, quantity=quantity)
    assert PurchaseOrderDetail.objects.count() == count
    assert services.reorder_product(asked, quantity=7).line.quantity == 7  # noqa: PLR2004


def test_reorder_goes_to_the_vendors_oldest_new_purchase_order():
    """R-inventory-020: the vendor's oldest New purchase order gets the line (or a
    raised quantity); with no New order a new New one is created; the unit cost is
    the standard unit cost."""
    vendor = f.VendorFactory()
    item = product(
        counted=0,
        target_level=6,
        minimum_reorder_quantity=1,
        standard_unit_cost=Decimal("2.7500"),
    )
    f.ProductVendorFactory(product=item, vendor=vendor)
    new = f.PurchaseOrderStatusFactory(status_id=PO_NEW)
    oldest = f.PurchaseOrderFactory(vendor=vendor, status=new)
    f.PurchaseOrderFactory(vendor=vendor, status=new)
    result = services.reorder_product(item)
    assert result.purchase_order.pk == oldest.pk
    assert (result.line.quantity, result.line.unit_cost) == (6, Decimal("2.7500"))
    services.reorder_product(item)
    result.line.refresh_from_db()
    assert result.line.quantity == 12  # noqa: PLR2004

    lonely = f.VendorFactory()
    f.PurchaseOrderFactory(
        vendor=lonely,
        status=f.PurchaseOrderStatusFactory(status_id=SUBMITTED),
    )
    other = product(counted=0, target_level=4, minimum_reorder_quantity=1)
    f.ProductVendorFactory(product=other, vendor=lonely)
    created = services.reorder_product(other).purchase_order
    assert created.status_id == PO_NEW
    assert created.vendor_id == lonely.pk
    assert list(created.lines.values_list("product_id", "quantity")) == [(other.pk, 4)]


def test_discontinued_product_is_not_reordered_or_highlighted():
    """R-inventory-021: no reorder for a discontinued product; the reorder quantity
    is highlighted only for an active product with a suggestion above zero."""
    stopped = product(counted=0, target_level=30, discontinued=True)
    f.ProductVendorFactory(product=stopped)
    with pytest.raises(ValidationError, match="R-inventory-021"):
        services.reorder_product(stopped)
    assert not PurchaseOrder.objects.exists()
    assert not services.product_actions(stopped).reorder
    levels = services.product_stock_levels(stopped)
    assert levels.reorder_quantity > 0
    assert not services.needs_reorder_attention(stopped, levels)
    active = product(counted=0, target_level=30)
    assert services.product_actions(active).reorder
    assert services.needs_reorder_attention(
        active,
        services.product_stock_levels(active),
    )
    idle = product(counted=0, target_level=0, minimum_reorder_quantity=0)
    assert not services.needs_reorder_attention(
        idle,
        services.product_stock_levels(idle),
    )


def test_product_page_levels_and_actions():
    """R-inventory-022: a saved product shows its levels, recalculated when its target
    level changes; an unsaved one shows zeros and no delete, reorder or histories."""
    unsaved = services.product_actions(Product())
    assert unsaved == services.ProductActions(
        delete=False,
        reorder=False,
        order_history=False,
        purchase_order_history=False,
    )
    assert services.product_stock_levels(Product()) == services.ZERO_LEVELS
    item = product(counted=12, target_level=20, minimum_reorder_quantity=1)
    order_line(item, 2, NO_STOCK)
    order_line(item, 3, ALLOCATED)
    po_line(item, 4, APPROVED)
    levels = services.product_stock_levels(item)
    assert (
        levels.to_sell,
        levels.no_stock,
        levels.allocated,
        levels.on_order,
        levels.reorder_quantity,
    ) == (9, 2, 3, 4, (20 + 2) - (9 + 4))
    services.save_product(item, {"target_level": 40})
    assert services.product_stock_levels(item).reorder_quantity == (40 + 2) - (9 + 4)
    assert all(vars(services.product_actions(item)).values())


# ---------------------------------------------------------------- audit and vendors


def test_audit_stamps_name_the_signed_in_user_or_system(user_with_role):
    """R-inventory-028: created rows get the signed-in user's full name and now as
    added and modified stamps; later changes refresh only the modified stamps; with
    no signed-in user the name is System."""
    ada = staff_user(user_with_role, "Ada", "Lovelace")
    bob = staff_user(user_with_role, "Bob", "Stone")
    category = services.save_category(
        ProductCategory(),
        {"product_category_name": "Stamped", "product_category_code": "STP"},
    )
    assert (category.added_by, category.modified_by) == ("System", "System")
    item = services.save_product(Product(), product_data(category), user=ada)
    item.refresh_from_db()
    added_on = item.added_on
    assert (item.added_by, item.modified_by) == ("Ada Lovelace", "Ada Lovelace")
    assert added_on is not None
    services.save_product(item, {"unit_price": Decimal("9.0000")}, user=bob)
    item.refresh_from_db()
    assert (item.added_by, item.added_on) == ("Ada Lovelace", added_on)
    assert item.modified_by == "Bob Stone"
    take = services.record_stock_take(item, 0, user=bob).stock_take
    assert (take.added_by, take.modified_by) == ("Bob Stone", "Bob Stone")
    link = services.add_product_vendor(item, f.VendorFactory(), user=ada)
    assert (link.added_by, link.modified_by) == ("Ada Lovelace", "Ada Lovelace")


def test_vendor_link_is_unique_and_needs_an_existing_vendor():
    """R-inventory-029: product and vendor required, the vendor an existing company,
    and a vendor linked to a product only once."""
    item = product()
    vendor = f.VendorFactory()
    services.add_product_vendor(item, vendor)
    for choice in (vendor, None, vendor.pk + 1000):
        with pytest.raises(ValidationError, match="R-inventory-029"):
            services.add_product_vendor(item, choice)
    assert ProductVendor.objects.filter(product=item).count() == 1
