"""Rule tests of the Purchasing and receiving area.

One test (or more) per rule of this area whose test_kind is rule
(analysis/rules.json), with the rule id first in the docstring, data from
legacy/factories.py and the expected values worked out by hand in the test. Never
golden files or seed outputs. A few e2e rules (R-purchasing-003, R-purchasing-008,
R-purchasing-023) get service-level tests here too.
"""
# Expected values are worked out by hand in each test.
# ruff: noqa: PLR2004

import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction

from northwind.domain import inventory
from northwind.legacy import audit
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import PaymentMethod
from northwind.legacy.choices import PurchaseOrderStatusCode as Status
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import OrderDetailFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ProductVendorFactory
from northwind.legacy.factories import PurchaseOrderDetailFactory
from northwind.legacy.factories import VendorFactory
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.purchasing import services
from northwind.purchasing.forms import LineForm
from northwind.purchasing.forms import PurchaseOrderForm

pytestmark = pytest.mark.django_db


def refused(rule: str):
    return pytest.raises(ValidationError, match=rule)


def fresh(obj):
    return type(obj).objects.get(pk=obj.pk)


def recent(value: dt.datetime | None) -> bool:
    """A date and time within the last minute (the service's Now)."""
    now = dt.datetime.now()  # noqa: DTZ005 (the app runs with USE_TZ False)
    return value is not None and now - dt.timedelta(minutes=1) <= value <= now


# ---------------------------------------------------------------- R-001


def test_new_purchase_order_starts_new(statuses, vendor):
    """R-purchasing-001: a purchase order entered by hand starts in status New, even
    when the form data asks for another status."""
    po = services.save_purchase_order(
        PurchaseOrder(),
        {"vendor": vendor, "notes": "first order", "status": Status.APPROVED},
    )
    assert fresh(po).status_id == Status.NEW
    assert fresh(po).vendor_id == vendor.pk


def test_reorder_creates_new_purchase_order(statuses, vendor, product):
    """R-purchasing-001: a purchase order created by a product reorder (the domain's
    reorder_into_purchase_order) starts in status New too."""
    from northwind.domain.purchasing import reorder_into_purchase_order  # noqa: PLC0415

    line = reorder_into_purchase_order(product, vendor, 12)
    assert line.purchase_order.status_id == Status.NEW


# ---------------------------------------------------------------- R-002


def test_purchase_order_needs_an_existing_vendor(statuses):
    """R-purchasing-002: without a vendor, or with a key that is no company, the save
    is refused and nothing is written."""
    with refused("R-purchasing-002"):
        services.save_purchase_order(PurchaseOrder(), {"vendor": None, "notes": ""})
    with refused("R-purchasing-002"):
        services.save_purchase_order(PurchaseOrder(), {"vendor": 987654})
    assert PurchaseOrder.objects.count() == 0


def test_purchase_order_form_requires_the_vendor(statuses):
    """R-purchasing-002: the new purchase order form marks the vendor as missing."""
    form = PurchaseOrderForm(data={"notes": "x"}, instance=PurchaseOrder())
    assert not form.is_valid()
    assert "vendor" in form.errors


# ---------------------------------------------------------------- R-003


def test_workflow_steps_cannot_be_skipped(make_po, user_with_role):
    """R-purchasing-003: each action works only from the status directly before it:
    approving a New, receiving a Submitted and closing an Approved purchase order are
    all refused, and the screen shows which steps are done."""
    approver = user_with_role("approver")
    new = make_po(Status.NEW)
    submitted = make_po(Status.SUBMITTED)
    approved = make_po(Status.APPROVED, shipping_fee=Decimal(1))
    with refused("R-purchasing-005"):
        services.approve_purchase_order(new, user=approver)
    with refused("R-purchasing-007"):
        services.receive_purchase_order(submitted, confirmed=True)
    with refused("R-purchasing-009"):
        services.close_purchase_order(approved, payment_method=PaymentMethod.CASH)
    assert [fresh(po).status_id for po in (new, submitted, approved)] == [
        Status.NEW,
        Status.SUBMITTED,
        Status.APPROVED,
    ]
    assert services.steps_done(fresh(approved)) == [
        ("Submitted", True),
        ("Approved", True),
        ("Received", False),
        ("Closed", False),
    ]


# ---------------------------------------------------------------- R-004


def test_submit_records_submitter_and_date_time(make_po, user_with_role, employee_for):
    """R-purchasing-004: submitting a New purchase order records the signed-in user's
    employee as submitter, the current date and time, and status Submitted."""
    user = user_with_role("staff")
    employee = employee_for(user)
    po = make_po(Status.NEW)
    services.submit_purchase_order(po, user=user)
    po = fresh(po)
    assert po.status_id == Status.SUBMITTED
    assert po.submitted_by_id == employee.pk
    assert recent(po.submitted_date)
    assert isinstance(po.submitted_date, dt.datetime)


def test_submit_is_refused_unless_new(make_po, user_with_role):
    """R-purchasing-004: from any other status the submit is refused and nothing
    changes."""
    user = user_with_role("staff")
    po = make_po(Status.SUBMITTED, submitted_date=dt.datetime(2024, 2, 1, 9, 0))  # noqa: DTZ001
    with refused("R-purchasing-004"):
        services.submit_purchase_order(po, user=user)
    po = fresh(po)
    assert po.status_id == Status.SUBMITTED
    assert po.submitted_date == dt.datetime(2024, 2, 1, 9, 0)  # noqa: DTZ001


def test_submit_is_refused_without_an_employee_record(make_po, user_with_role):
    """R-purchasing-004: the submitter is the signed-in user's employee record (the
    employee with the user's e-mail address). A user without one is refused, so a
    Submitted purchase order never has a blank submitter; nothing changes."""
    user = user_with_role("staff")
    EmployeeFactory(email_address="someone.else@example.org")
    po = make_po(Status.NEW)
    with refused("R-purchasing-004"):
        services.submit_purchase_order(po, user=user)
    po = fresh(po)
    assert (po.status_id, po.submitted_by_id, po.submitted_date) == (
        Status.NEW,
        None,
        None,
    )


# ---------------------------------------------------------------- R-005


def test_approve_needs_the_privilege(make_po, user_with_role):
    """R-purchasing-005: a user without the approve-purchase-order privilege is
    refused and the purchase order stays Submitted."""
    po = make_po(Status.SUBMITTED)
    with refused("R-purchasing-005"):
        services.approve_purchase_order(po, user=user_with_role("staff"))
    assert fresh(po).status_id == Status.SUBMITTED
    assert fresh(po).approved_date is None


def test_approver_may_approve_own_purchase_order(
    make_po,
    user_with_role,
    employee_for,
):
    """R-purchasing-005: an approver may approve a purchase order they submitted;
    the approver and the current date and time are recorded, status Approved."""
    user = user_with_role("approver")
    employee = employee_for(user)
    po = make_po(Status.NEW)
    services.submit_purchase_order(po, user=user)
    services.approve_purchase_order(po, user=user)
    po = fresh(po)
    assert po.status_id == Status.APPROVED
    assert po.submitted_by_id == employee.pk
    assert po.approved_by_id == employee.pk
    assert recent(po.approved_date)


def test_approve_is_refused_without_an_employee_record(make_po, user_with_role):
    """R-purchasing-005: an approver whose sign-in e-mail is no employee's cannot be
    recorded as approver, so the approval is refused and the purchase order stays
    Submitted without approver or approved date."""
    po = make_po(Status.SUBMITTED)
    with refused("R-purchasing-005"):
        services.approve_purchase_order(po, user=user_with_role("approver"))
    po = fresh(po)
    assert (po.status_id, po.approved_by_id, po.approved_date) == (
        Status.SUBMITTED,
        None,
        None,
    )


# ---------------------------------------------------------------- R-006


def test_allocation_reruns_after_approve_and_receive(
    po_with_line,
    product,
    user_with_role,
    employee_for,
):
    """R-purchasing-006: approving re-runs allocation, so a waiting order line of 5
    (No Stock, nothing in stock) fits in the 10 now on order and becomes On Order;
    receiving re-runs it again and the 10 received cover it: Allocated."""
    po, _line = po_with_line
    waiting = OrderDetailFactory(
        product=product,
        quantity=5,
        order_detail_status__order_detail_status_id=OrderDetailStatusCode.NO_STOCK,
    )
    po.status_id = Status.SUBMITTED
    po.save()
    approver = user_with_role("approver")
    employee_for(approver)
    services.approve_purchase_order(po, user=approver)
    assert fresh(waiting).order_detail_status_id == OrderDetailStatusCode.ON_ORDER
    services.receive_purchase_order(po, confirmed=True)
    assert fresh(waiting).order_detail_status_id == OrderDetailStatusCode.ALLOCATED


# ---------------------------------------------------------------- R-007


def test_receive_needs_confirmation(po_with_line):
    """R-purchasing-007: declining the confirmation changes nothing."""
    po, line = po_with_line
    po.status_id = Status.APPROVED
    po.save()
    with refused("R-purchasing-007"):
        services.receive_purchase_order(po, confirmed=False)
    assert fresh(po).status_id == Status.APPROVED
    assert fresh(po).received_date is None
    assert fresh(line).received_date is None


def test_receive_stamps_order_and_every_line(po_with_line, product, vendor):
    """R-purchasing-007: receiving an Approved purchase order sets the same current
    date and time on the purchase order and on every line, and status Received."""
    po, line = po_with_line
    other = ProductFactory()
    ProductVendorFactory(product=other, vendor=vendor)
    second = PurchaseOrderDetailFactory(purchase_order=po, product=other, quantity=10)
    po.status_id = Status.APPROVED
    po.save()
    services.receive_purchase_order(po, confirmed=True)
    po = fresh(po)
    assert po.status_id == Status.RECEIVED
    assert recent(po.received_date)
    assert fresh(line).received_date == po.received_date
    assert fresh(second).received_date == po.received_date


# ---------------------------------------------------------------- R-008


def test_received_quantity_raises_available_stock(
    po_with_line,
    product,
    user_with_role,
    employee_for,
):
    """R-purchasing-008: while Approved the 10 ordered count as on order; once
    received they count as stock bought, so the product's physical stock is 10."""
    po, _line = po_with_line
    po.status_id = Status.SUBMITTED
    po.save()
    approver = user_with_role("approver")
    employee_for(approver)
    services.approve_purchase_order(po, user=approver)
    assert inventory.product_on_order(product) == 10
    assert inventory.product_available(product) == 0
    services.receive_purchase_order(po, confirmed=True)
    assert inventory.product_on_order(product) == 0
    assert inventory.product_available(product) == 10


# ---------------------------------------------------------------- R-009


def test_close_stores_payment_tax_and_total(po_with_line, product, vendor_tax):
    """R-purchasing-009: closing a Received purchase order with shipping fee 7.0000
    and payment by check stores now as payment date, tax 1.5000 (5% of 10 x 2.5000 +
    4 x 1.2500 = 30.0000) and payment amount 30 + 1.5 + 7 = 38.5000, status Closed."""
    po, _line = po_with_line
    other = ProductFactory()
    PurchaseOrderDetailFactory(
        purchase_order=po,
        product=other,
        quantity=4,
        unit_cost=Decimal("1.2500"),
    )
    po.status_id = Status.RECEIVED
    po.save()
    services.close_purchase_order(
        po,
        shipping_fee=Decimal("7.0000"),
        payment_method=PaymentMethod.CHECK,
    )
    po = fresh(po)
    assert po.status_id == Status.CLOSED
    assert recent(po.payment_date)
    assert po.tax_amount == Decimal("1.5000")
    assert po.payment_amount == Decimal("38.5000")
    assert po.shipping_fee == Decimal("7.0000")
    assert po.payment_method == "Check"


def test_close_needs_shipping_fee_and_payment_method(po_with_line, vendor_tax):
    """R-purchasing-009: without the payment method (or the shipping fee) the close
    is refused and nothing changes; only the three fixed methods are accepted."""
    po, _line = po_with_line
    po.status_id = Status.RECEIVED
    po.save()
    with refused("R-purchasing-009"):
        services.close_purchase_order(po, shipping_fee=Decimal(5))
    with refused("R-purchasing-009"):
        services.close_purchase_order(po, payment_method=PaymentMethod.CASH)
    with refused("R-purchasing-009"):
        services.close_purchase_order(
            po,
            shipping_fee=Decimal(5),
            payment_method="Wire",
        )
    po = fresh(po)
    assert po.status_id == Status.RECEIVED
    assert po.payment_date is None
    assert sorted(PaymentMethod.values) == ["Cash", "Check", "Credit Card"]


# ---------------------------------------------------------------- R-010


def test_amounts(po_with_line, vendor_tax):
    """R-purchasing-010: lines 10 x 2.5000 and 4 x 1.2500 give subtotal 30.0000; at
    the vendor tax rate of 5% the tax is 1.5000 (shipping not taxed); with shipping
    fee 7.0000 the total is 38.5000, and with no shipping fee 31.5000."""
    po, _line = po_with_line
    PurchaseOrderDetailFactory(
        purchase_order=po,
        product=ProductFactory(),
        quantity=4,
        unit_cost=Decimal("1.2500"),
    )
    amounts = services.purchase_order_amounts(po)
    assert (amounts.subtotal, amounts.tax, amounts.total) == (
        Decimal("30.0000"),
        Decimal("1.5000"),
        Decimal("31.5000"),
    )
    po.shipping_fee = Decimal("7.0000")
    po.save()
    assert services.purchase_order_amounts(po).total == Decimal("38.5000")
    assert services.purchase_order_amounts(po).tax == Decimal("1.5000")


def test_amounts_without_lines_are_blank(make_po, vendor_tax):
    """R-purchasing-010: a purchase order without lines has no subtotal, tax or
    total, as the original screen shows blanks."""
    po = make_po(Status.NEW, shipping_fee=Decimal(3))
    amounts = services.purchase_order_amounts(po)
    assert (amounts.subtotal, amounts.tax, amounts.total) == (None, None, None)


# ---------------------------------------------------------------- R-011


def test_fields_lock_by_status(make_po):
    """R-purchasing-011: New and Submitted allow only the notes; Approved adds the
    received date; Received allows shipping fee, payment method and notes; Closed
    nothing. The edit form carries only those fields."""
    assert services.editable_fields(PurchaseOrder()) == ("vendor", "notes")
    expected = {
        Status.NEW: {"notes"},
        Status.SUBMITTED: {"notes"},
        Status.APPROVED: {"received_date", "notes"},
        Status.RECEIVED: {"shipping_fee", "payment_method", "notes"},
        Status.CLOSED: set(),
    }
    for status, fields in expected.items():
        po = make_po(status)
        assert set(services.editable_fields(po)) == fields
        assert set(PurchaseOrderForm(instance=po).fields) == fields


def test_locked_field_edit_is_refused(make_po):
    """R-purchasing-011: the shipping fee of an Approved purchase order and the notes
    of a Closed one cannot be changed; the received date of an Approved one can."""
    approved = make_po(Status.APPROVED)
    with refused("R-purchasing-011"):
        services.save_purchase_order(approved, {"shipping_fee": Decimal(4)})
    assert fresh(approved).shipping_fee is None
    when = dt.datetime(2024, 3, 4, 5, 6, 7)  # noqa: DTZ001
    services.save_purchase_order(approved, {"received_date": when, "notes": "ok"})
    assert fresh(approved).received_date == when
    closed = make_po(Status.CLOSED, notes="final")
    with refused("R-purchasing-011"):
        services.save_purchase_order(closed, {"notes": "changed"})
    assert fresh(closed).notes == "final"


# ---------------------------------------------------------------- R-012


def test_lines_frozen_from_submitted(po_with_line, product):
    """R-purchasing-012: once Submitted, lines cannot be added, changed or deleted."""
    po, line = po_with_line
    po.status_id = Status.SUBMITTED
    po.save()
    with refused("R-purchasing-012"):
        services.add_purchase_order_line(po, product, 30, Decimal(2))
    with refused("R-purchasing-012"):
        services.update_purchase_order_line(line, product, 40, Decimal(2))
    with refused("R-purchasing-012"):
        services.delete_purchase_order_line(line)
    line = fresh(line)
    assert (line.quantity, line.unit_cost) == (10, Decimal("2.5000"))
    assert not services.lines_editable(fresh(po))


def test_lines_editable_while_new(po_with_line, product):
    """R-purchasing-012: while New a line can be changed and deleted."""
    _po, line = po_with_line
    services.update_purchase_order_line(line, product, 30, Decimal("2.0000"))
    assert fresh(line).quantity == 30
    services.delete_purchase_order_line(line)
    assert not PurchaseOrderDetail.objects.filter(pk=line.pk).exists()


# ---------------------------------------------------------------- R-013


def test_lines_need_a_saved_purchase_order(statuses, vendor, product):
    """R-purchasing-013: a line cannot be entered before the purchase order is saved;
    the user is told to complete and save it first."""
    with refused("R-purchasing-013"):
        services.add_purchase_order_line(
            PurchaseOrder(vendor=vendor),
            product,
            10,
            Decimal(2),
        )
    assert PurchaseOrderDetail.objects.count() == 0


# ---------------------------------------------------------------- R-014


def test_delete_new_or_submitted_with_lines(po_with_line, make_po):
    """R-purchasing-014: a New purchase order is deleted with its lines; a Submitted
    one can be deleted too."""
    po, line = po_with_line
    services.delete_purchase_order(po)
    assert not PurchaseOrder.objects.filter(pk=po.pk).exists()
    assert not PurchaseOrderDetail.objects.filter(pk=line.pk).exists()
    submitted = make_po(Status.SUBMITTED)
    services.delete_purchase_order(submitted)
    assert not PurchaseOrder.objects.filter(pk=submitted.pk).exists()


def test_delete_refused_after_submitted(make_po):
    """R-purchasing-014: an Approved, Received or Closed purchase order cannot be
    deleted."""
    for status in (Status.APPROVED, Status.RECEIVED, Status.CLOSED):
        po = make_po(status)
        with refused("R-purchasing-014"):
            services.delete_purchase_order(po)
        assert PurchaseOrder.objects.filter(pk=po.pk).exists()


# ---------------------------------------------------------------- R-015


def test_vendor_fixed_once_saved(po_with_line, vendor):
    """R-purchasing-015: the vendor of a saved purchase order can never be changed,
    in any status; the lines stay."""
    po, line = po_with_line
    other = VendorFactory()
    with refused("R-purchasing-015"):
        services.save_purchase_order(po, {"vendor": other, "notes": "x"})
    assert fresh(po).vendor_id == vendor.pk
    assert PurchaseOrderDetail.objects.filter(pk=line.pk).exists()
    assert "vendor" not in PurchaseOrderForm(instance=po).fields


def test_vendor_choice_sets_product_choices(statuses, vendor, product):
    """R-purchasing-015: the vendor is chosen before the first save, without a
    confirmation, and it decides the product choices of the lines."""
    other_vendor = VendorFactory()
    other_product = ProductFactory()
    ProductVendorFactory(product=other_product, vendor=other_vendor)
    po = services.save_purchase_order(PurchaseOrder(), {"vendor": vendor})
    assert list(LineForm(purchase_order=po).fields["product"].queryset) == [product]


# ---------------------------------------------------------------- R-018


def test_product_choice_fills_quantity_and_cost(statuses, product):
    """R-purchasing-018: choosing the product fills in its reorder quantity (target
    20 - (stock 0 + on order 0) = 20, above the minimum 10) and its standard unit
    cost 2.5000."""
    assert services.line_defaults(product) == (20, Decimal("2.5000"))


# ---------------------------------------------------------------- R-019


def test_line_below_minimum_reorder_is_refused(make_po, vendor, product):
    """R-purchasing-019: a quantity of 5, below the minimum reorder quantity 10, is
    refused; a missing unit cost and an unknown product are refused too."""
    po = make_po(Status.NEW, vendor=vendor)
    with refused("R-purchasing-019"):
        services.add_purchase_order_line(po, product, 5, Decimal(2))
    with refused("R-purchasing-019"):
        services.add_purchase_order_line(po, product, 12, None)
    with refused("R-purchasing-019"):
        services.add_purchase_order_line(po, 987654, 12, Decimal(2))
    assert PurchaseOrderDetail.objects.filter(purchase_order=po).count() == 0


def test_line_below_target_level_only_warns(make_po, vendor, product):
    """R-purchasing-019: 12 more of a product with nothing to sell stays below its
    target level of 20 (8 short): a warning, and the line is still saved; 25 gives
    no warning."""
    po = make_po(Status.NEW, vendor=vendor)
    result = services.add_purchase_order_line(po, product, 12, Decimal("2.5000"))
    assert fresh(result.line).quantity == 12
    assert len(result.warnings) == 1
    assert "R-purchasing-019" in result.warnings[0]
    assert "8 more" in result.warnings[0]
    other = ProductFactory(minimum_reorder_quantity=1, target_level=20)
    result = services.add_purchase_order_line(po, other, 25, Decimal(1))
    assert result.warnings == []


# ---------------------------------------------------------------- R-020


def test_same_product_adds_to_its_line(po_with_line, product):
    """R-purchasing-020: adding 15 more of a product already on the purchase order
    (10 at 2.5000) gives one line of 25 that keeps the unit cost 2.5000."""
    po, line = po_with_line
    result = services.add_purchase_order_line(po, product, 15, Decimal("9.9900"))
    assert result.line.pk == line.pk
    line = fresh(line)
    assert (line.quantity, line.unit_cost) == (25, Decimal("2.5000"))
    assert PurchaseOrderDetail.objects.filter(purchase_order=po).count() == 1


def test_database_refuses_a_second_line(po_with_line, product):
    """R-purchasing-020: the database refuses a second line for the same product,
    and changing another line to that product is refused."""
    po, _line = po_with_line
    with pytest.raises(IntegrityError), transaction.atomic():
        PurchaseOrderDetail.objects.create(
            purchase_order=po,
            product=product,
            quantity=1,
            unit_cost=Decimal(1),
        )
    other = PurchaseOrderDetailFactory(purchase_order=po, quantity=10)
    with refused("R-purchasing-020"):
        services.update_purchase_order_line(other, product, 10, Decimal(1))


# ---------------------------------------------------------------- R-021


def test_add_no_stock_lines(po_with_line, vendor, product):
    """R-purchasing-021: of the vendor's products, only the one not yet on the
    purchase order with a customer line waiting in No Stock (5) is added, with its
    reorder quantity (no stock 5 + target 20 - stock 0 = 25) and standard cost; the
    product already on it, a product without waiting lines and another vendor's
    product are not."""
    po, line = po_with_line
    no_stock = OrderDetailStatusCode.NO_STOCK
    wanted = ProductFactory(standard_unit_cost=Decimal("3.2500"))
    ProductVendorFactory(product=wanted, vendor=vendor)
    OrderDetailFactory(
        product=wanted,
        quantity=5,
        order_detail_status__order_detail_status_id=no_stock,
    )
    OrderDetailFactory(
        product=product,
        quantity=5,
        order_detail_status__order_detail_status_id=no_stock,
    )
    idle = ProductFactory()
    ProductVendorFactory(product=idle, vendor=vendor)
    elsewhere = ProductFactory()
    ProductVendorFactory(product=elsewhere, vendor=VendorFactory())
    OrderDetailFactory(
        product=elsewhere,
        quantity=5,
        order_detail_status__order_detail_status_id=no_stock,
    )
    assert services.add_no_stock_lines(po) == 1
    added = PurchaseOrderDetail.objects.get(purchase_order=po, product=wanted)
    assert (added.quantity, added.unit_cost) == (25, Decimal("3.2500"))
    assert fresh(line).quantity == 10
    assert PurchaseOrderDetail.objects.filter(purchase_order=po).count() == 2
    assert OrderDetail.objects.count() == 3


def test_add_no_stock_lines_needs_a_saved_purchase_order(statuses, vendor):
    """R-purchasing-021: on an unsaved purchase order the action is refused."""
    with refused("R-purchasing-021"):
        services.add_no_stock_lines(PurchaseOrder(vendor=vendor))


# ---------------------------------------------------------------- R-023


def test_vendor_dialog_choices(statuses, vendor, product):
    """R-purchasing-023: only the product's vendors, by name; with several, OK
    without a choice is refused; one vendor needs no choice; a product without a
    vendor cannot be reordered."""
    second = VendorFactory(company_name="Another Vendor")
    VendorFactory(company_name="Unrelated Vendor")
    assert services.choose_vendor(product, None) == vendor
    ProductVendorFactory(product=product, vendor=second)
    assert services.vendor_choices(product) == [second, vendor]
    with refused("R-purchasing-023"):
        services.choose_vendor(product, None)
    assert services.choose_vendor(product, second.pk) == second
    with refused("R-purchasing-023"):
        services.vendor_choices(ProductFactory())


# ---------------------------------------------------------------- R-027


def test_audit_stamps(make_po, user_with_role, employee_for):
    """R-purchasing-027: a row written without a signed-in user carries System; an
    update by a signed-in user stamps their full name (first then last) as modifier
    and keeps who added it and when."""
    with audit.acting_as(None):
        po = make_po(Status.NEW)
    po = fresh(po)
    assert (po.added_by, po.modified_by) == ("System", "System")
    added_on = po.added_on
    user = user_with_role("staff")
    employee_for(user, first_name="Ann", last_name="Buyer")
    services.submit_purchase_order(po, user=user)
    po = fresh(po)
    assert po.modified_by == "Ann Buyer"
    assert po.added_by == "System"
    assert po.added_on == added_on
    assert recent(po.modified_on)


def test_audit_stamps_on_lines(po_with_line, product, user_with_role, employee_for):
    """R-purchasing-027: purchase order lines are stamped the same way: a line added
    by a signed-in user carries their name as adder and modifier."""
    po, _line = po_with_line
    user = user_with_role("staff")
    employee_for(user, first_name="Bo", last_name="Clerk")
    other = ProductFactory()
    result = services.add_purchase_order_line(po, other, 25, Decimal(1), user=user)
    line = fresh(result.line)
    assert (line.added_by, line.modified_by) == ("Bo Clerk", "Bo Clerk")
