"""Fixtures of the Purchasing and receiving tests: synthetic rows from
legacy/factories.py only."""

from __future__ import annotations

from decimal import Decimal

import pytest

from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.choices import SystemSettingCode
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import OrderDetailStatusFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ProductVendorFactory
from northwind.legacy.factories import PurchaseOrderDetailFactory
from northwind.legacy.factories import PurchaseOrderFactory
from northwind.legacy.factories import PurchaseOrderStatusFactory
from northwind.legacy.factories import SystemSettingFactory
from northwind.legacy.factories import VendorFactory


@pytest.fixture
def statuses(db):
    """Every purchase order status and order line status (fixed codes)."""
    for code in PurchaseOrderStatusCode:
        PurchaseOrderStatusFactory(status_id=code)
    for code in OrderDetailStatusCode:
        OrderDetailStatusFactory(order_detail_status_id=code)


@pytest.fixture
def vendor_tax(db):
    """The vendor tax rate setting: 50 thousandths, i.e. 5%."""
    return SystemSettingFactory(
        setting_id=SystemSettingCode.VENDOR_TAX_RATE,
        setting_value="50",
    )


@pytest.fixture
def make_po(statuses):
    """A purchase order in a given status from a vendor (a new vendor by default)."""

    def make(status=PurchaseOrderStatusCode.NEW, **fields):
        return PurchaseOrderFactory(status__status_id=status, **fields)

    return make


@pytest.fixture
def vendor(db):
    return VendorFactory(company_name="Vendor Alpha")


@pytest.fixture
def product(vendor):
    """A product of `vendor`: standard cost 2.5000, minimum reorder 10, target 20."""
    product = ProductFactory(
        standard_unit_cost=Decimal("2.5000"),
        minimum_reorder_quantity=10,
        target_level=20,
    )
    ProductVendorFactory(product=product, vendor=vendor)
    return product


@pytest.fixture
def employee_for():
    """The employee record of a web user (linked by e-mail address)."""

    def make(user, first_name="Ann", last_name="Buyer"):
        return EmployeeFactory(
            first_name=first_name,
            last_name=last_name,
            email_address=user.email,
        )

    return make


@pytest.fixture
def po_with_line(make_po, vendor, product):
    """A New purchase order from `vendor` with one line of `product`."""
    po = make_po(vendor=vendor)
    line = PurchaseOrderDetailFactory(
        purchase_order=po,
        product=product,
        quantity=10,
        unit_cost=Decimal("2.5000"),
    )
    return po, line
