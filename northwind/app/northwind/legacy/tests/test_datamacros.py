"""The original tables' data macros and validation rules, one test per rule (rule id
first in the docstring).

All data macros of the original are Before Change macros that stamp the audit columns
(legacy.audit); the validation rules are Meta.constraints that full_clean() and the
database both enforce. The original has no After Insert, After Update or After Delete
data macros.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction

from northwind.legacy import models
from northwind.legacy.audit import SYSTEM
from northwind.legacy.audit import acting_as
from northwind.legacy.audit import keeping_loaded_stamps
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.factories import FACTORIES
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import OrderDetailFactory
from northwind.legacy.factories import PurchaseOrderStatusFactory
from northwind.legacy.factories import StockTakeFactory

pytestmark = pytest.mark.django_db

EDITOR = "Pat Example"


def assert_stamped(model) -> None:
    """Insert stamps all four columns; an update keeps AddedBy and AddedOn, even when it
    tries to change or blank them, and refreshes ModifiedBy and ModifiedOn."""
    obj = FACTORIES[model].create()
    obj.refresh_from_db()
    assert (obj.added_by, obj.modified_by) == (SYSTEM, SYSTEM), model.__name__
    assert obj.added_on is not None
    assert obj.modified_on == obj.added_on
    added_on = obj.added_on
    with acting_as(EDITOR):
        obj.added_by = "Someone else"
        obj.added_on = None
        obj.save()
    obj.refresh_from_db()
    assert (obj.added_by, obj.added_on) == (SYSTEM, added_on), model.__name__
    assert obj.modified_by == EDITOR
    assert obj.modified_on >= added_on
    with acting_as(EDITOR):
        obj.added_by = None
        obj.save(update_fields=["added_by"])
    obj.refresh_from_db()
    assert obj.added_by == SYSTEM, model.__name__


def test_order_area_tables_carry_audit_stamps():
    """R-orders-031: the Before Change macros of the order-area tables stamp who created
    and last changed a row; the created stamps never change; System when nobody is
    signed in."""
    for model in (
        models.Company,
        models.CompanyType,
        models.Contact,
        models.EmployeePrivilege,
        models.Employee,
        models.OrderDetailStatus,
        models.OrderDetail,
        models.OrderStatus,
        models.Order,
        models.Privilege,
        models.String,
        models.TaxStatus,
        models.Title,
    ):
        assert_stamped(model)
    employee = EmployeeFactory.create(first_name="Ada", last_name="Sample")
    with acting_as(employee.full_name):
        order = FACTORIES[models.Order].create()
    assert order.added_by == order.modified_by == "Ada Sample"


def test_inventory_tables_carry_audit_stamps():
    """R-inventory-028: products, product categories, product-vendor links and stock
    takes carry the same audit stamps."""
    for model in (
        models.Product,
        models.ProductCategory,
        models.ProductVendor,
        models.StockTake,
    ):
        assert_stamped(model)


def test_purchasing_tables_carry_audit_stamps():
    """R-purchasing-027: purchase orders, their lines and the purchase order statuses
    carry the same audit stamps."""
    for model in (
        models.PurchaseOrder,
        models.PurchaseOrderDetail,
        models.PurchaseOrderStatus,
    ):
        assert_stamped(model)


def test_purchase_order_statuses_are_the_fixed_sequence():
    """R-purchasing-003: the purchase order statuses are the fixed codes New, Submitted,
    Approved, Received and Closed; their rows are stamped by the status table's Before
    Change macro, and a status outside the sequence is refused."""
    for code in PurchaseOrderStatusCode:
        status = PurchaseOrderStatusFactory.create(status_id=code)
        status.full_clean()
        assert status.added_by == SYSTEM
    names = {s.status_name for s in models.PurchaseOrderStatus.objects.all()}
    assert names == {code.label for code in PurchaseOrderStatusCode}
    outside = models.PurchaseOrderStatus(
        status_id=max(PurchaseOrderStatusCode) + 1,
        status_name="Other",
        sort_order=99,
    )
    with pytest.raises(ValidationError) as caught:
        outside.full_clean()
    assert "status_id" in caught.value.message_dict


def test_order_line_quantity_must_be_positive():
    """R-orders-006: an order line's quantity must be greater than zero (the original's
    field validation rule), checked by full_clean() and by the database."""
    line = OrderDetailFactory.create()
    line.quantity = 0
    with pytest.raises(ValidationError):
        line.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        line.save()
    line.quantity = 1
    line.full_clean()


def test_stock_take_quantities_cannot_be_negative():
    """R-inventory-009: the counted and the expected quantity of a stock take can never
    be negative; the expected quantity may be blank."""
    take = StockTakeFactory.create()
    take.quantity_on_hand = -1
    with pytest.raises(ValidationError):
        take.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        take.save()
    take.quantity_on_hand = 0
    take.expected_quantity = -1
    with pytest.raises(ValidationError):
        take.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        take.save()
    take.expected_quantity = None
    take.full_clean()
    take.save()


def test_loaded_rows_keep_their_stamps():
    """R-orders-031: rows written by an import carry the fixed name System, while a
    dataset load (keeping_loaded_stamps) keeps the stamps the rows already carry."""
    with keeping_loaded_stamps():
        kept = FACTORIES[models.Title].create(
            title="Kp.",
            added_by="Loaded Name",
            modified_by="Loaded Name",
        )
    kept.refresh_from_db()
    assert (kept.added_by, kept.modified_by) == ("Loaded Name", "Loaded Name")
    assert kept.added_on is not None
    imported = FACTORIES[models.Title].create(title="Im.", added_by="Loaded Name")
    imported.refresh_from_db()
    assert imported.added_by == SYSTEM
