"""Fixtures of the area's tests."""

import pytest

from northwind.legacy import factories as f
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import PurchaseOrderStatusCode


@pytest.fixture
def fixed_codes(db):
    """The fixed code rows the logic uses by key, as every database has them: the
    order line statuses that allocation sets and the New status of a purchase order
    a reorder creates."""
    for code in OrderDetailStatusCode:
        f.OrderDetailStatusFactory(order_detail_status_id=code)
    for code in PurchaseOrderStatusCode:
        f.PurchaseOrderStatusFactory(status_id=code)
