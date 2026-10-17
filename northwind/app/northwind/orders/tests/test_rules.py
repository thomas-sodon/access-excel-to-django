"""Rule tests of the Orders, Invoicing and Shipping area.

One test (or more) per rule of this area whose test_kind is rule (analysis/rules.json),
with the rule id first in the docstring, data from legacy/factories.py and the expected
values worked out by hand in the test. Never golden files or seed outputs.
"""

# Expected values are worked out by hand and written as literals next to the sum.

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from northwind.legacy.audit import SYSTEM
from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.choices import PaymentMethod
from northwind.legacy.choices import SystemSettingCode
from northwind.legacy.choices import TaxStatusCode
from northwind.legacy.factories import CompanyFactory
from northwind.legacy.factories import CompanyTypeFactory
from northwind.legacy.factories import ContactFactory
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import EmployeePrivilegeFactory
from northwind.legacy.factories import OrderDetailFactory
from northwind.legacy.factories import OrderDetailStatusFactory
from northwind.legacy.factories import OrderFactory
from northwind.legacy.factories import OrderStatusFactory
from northwind.legacy.factories import ProductCategoryFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ProductVendorFactory
from northwind.legacy.factories import PurchaseOrderFactory
from northwind.legacy.factories import ShipperFactory
from northwind.legacy.factories import StateFactory
from northwind.legacy.factories import StockTakeFactory
from northwind.legacy.factories import SystemSettingFactory
from northwind.legacy.factories import TaxStatusFactory
from northwind.legacy.factories import TitleFactory
from northwind.legacy.factories import VendorFactory
from northwind.legacy.models import Company
from northwind.legacy.models import Contact
from northwind.legacy.models import Employee
from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import ProductVendor
from northwind.legacy.models import SystemSetting

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.orders import services

pytestmark = pytest.mark.django_db

OS = OrderStatusCode
ODS = OrderDetailStatusCode


def at(day: int, hour: int = 9, month: int = 1) -> dt.datetime:
    return dt.datetime(2024, month, day, hour, 0)  # noqa: DTZ001 (USE_TZ is False)


@pytest.fixture(autouse=True)
def codes():
    """The fixed code rows every real database carries (R-orders-047)."""
    for code in OrderStatusCode:
        OrderStatusFactory(order_status_id=code)
    for code in OrderDetailStatusCode:
        OrderDetailStatusFactory(order_detail_status_id=code)
    for code in TaxStatusCode:
        TaxStatusFactory(tax_status_id=code)
    for code in CompanyTypeCode:
        CompanyTypeFactory(company_type_id=code)


def order_in(status: int = OS.NEW, **kwargs) -> Order:
    return OrderFactory(order_status__order_status_id=status, **kwargs)


def line_on(order, product, quantity, status=ODS.NEW, **kwargs) -> OrderDetail:
    return OrderDetailFactory(
        order=order,
        product=product,
        quantity=quantity,
        order_detail_status__order_detail_status_id=status,
        **kwargs,
    )


def stocked(quantity: int, **kwargs):
    """A product whose latest stock take counted `quantity` on 1 January 2024."""
    product = ProductFactory(**kwargs)
    StockTakeFactory(
        product=product,
        quantity_on_hand=quantity,
        expected_quantity=quantity,
        stock_take_date=at(1, 8),
    )
    return product


def status_of(line: OrderDetail) -> int:
    return OrderDetail.objects.get(pk=line.pk).order_detail_status_id


@pytest.fixture
def staff(user_with_role):
    """A signed-in staff user who is the employee Pat Lee (matched by e-mail)."""
    employee = EmployeeFactory(first_name="Pat", last_name="Lee")
    user = user_with_role("staff", email=employee.email_address)
    user.employee = employee
    return user


# ---------------------------------------------------------------- order header


def test_new_order_is_prefilled(staff):
    """R-orders-001: a new order has the signed-in employee as salesperson, the
    default sales tax rate (75 thousandths = 0.075), status New and the current date
    and time."""
    SystemSettingFactory(
        setting_id=SystemSettingCode.SALES_TAX_RATE,
        setting_value="75",
    )
    before = dt.datetime.now().replace(microsecond=0)  # noqa: DTZ005
    order = services.new_order(staff)
    assert order.employee == staff.employee
    assert order.tax_rate == pytest.approx(0.075)
    assert order.order_status_id == OS.NEW
    assert before <= order.order_date <= dt.datetime.now()  # noqa: DTZ005


def test_customer_sets_the_tax_status(staff, client):
    """R-orders-002: choosing the customer sets the order's tax status to the
    customer's standard tax status; the user may still change it while New."""
    customer = CompanyFactory(standard_tax_status__tax_status_id=TaxStatusCode.TAXABLE)
    order = services.new_order(staff)
    services.save_order(
        order,
        {"customer": customer, "employee": staff.employee},
        user=staff,
    )
    assert order.tax_status_id == TaxStatusCode.TAXABLE
    exempt = TaxStatusFactory(tax_status_id=TaxStatusCode.TAX_EXEMPT)
    services.save_order(order, {"tax_status": exempt}, user=staff)
    assert Order.objects.get(pk=order.pk).tax_status_id == TaxStatusCode.TAX_EXEMPT
    client.force_login(staff)
    url = reverse("orders:order_create") + f"?customer={customer.pk}"
    response = client.get(url)
    assert response.context["form"].initial["tax_status"] == TaxStatusCode.TAXABLE


def test_lines_need_a_saved_order():
    """R-orders-004: order lines cannot be entered before the order is saved."""
    unsaved = Order(order_status_id=OS.NEW)
    with pytest.raises(ValidationError, match="R-orders-004"):
        services.save_order_line(
            unsaved,
            None,
            {"product": ProductFactory(), "quantity": 1},
        )
    assert not OrderDetail.objects.exists()


def test_required_fields_block_the_save(staff):
    """R-orders-005: an order, line, company, contact or employee is not saved while a
    required column is blank; the error names each blank field."""
    order = services.new_order(staff)
    with pytest.raises(ValidationError) as refused:
        services.save_order(order, {"customer": None, "employee": staff.employee})
    assert "customer" in refused.value.error_dict
    assert "R-orders-005" in str(refused.value)
    assert not Order.objects.exists()
    company = CompanyFactory()
    with pytest.raises(ValidationError, match="R-orders-005") as refused:
        services.save_contact(
            Contact(company=company),
            {"last_name": "Roe", "first_name": ""},
        )
    assert {"first_name", "job_title"} <= set(refused.value.error_dict)
    assert not Contact.objects.exists()
    with pytest.raises(ValidationError, match="R-orders-005"):
        services.save_employee(Employee(), {"first_name": "Sam"})
    with pytest.raises(ValidationError, match="R-orders-005"):
        services.save_company(Company(), {"company_name": "X"}, confirmed=True)


# ---------------------------------------------------------------- order lines


def test_quantity_must_be_above_zero():
    """R-orders-006: an order line's quantity must be greater than zero."""
    order = order_in()
    with pytest.raises(ValidationError, match="R-orders-006"):
        services.save_order_line(order, None, {"product": stocked(5), "quantity": 0})
    assert not OrderDetail.objects.exists()


def test_a_product_once_per_order():
    """R-orders-007: a product appears at most once on the same order."""
    order = order_in()
    product = stocked(10)
    services.save_order_line(order, None, {"product": product, "quantity": 1})
    with pytest.raises(ValidationError, match="R-orders-007"):
        services.save_order_line(order, None, {"product": product, "quantity": 2})
    assert OrderDetail.objects.filter(order=order).count() == 1


def test_product_price_is_copied_and_discount_starts_at_zero():
    """R-orders-008: choosing a product copies its list price into the unit price; a
    new line's discount starts at zero; the products can be narrowed to a
    category."""
    category = ProductCategoryFactory()
    product = stocked(10, unit_price=Decimal("12.5000"), product_category=category)
    other = stocked(10, unit_price=Decimal("3.0000"))
    line = services.save_order_line(
        order_in(),
        None,
        {"product": product, "quantity": 2},
    )
    assert line.unit_price == Decimal("12.5000")
    assert line.discount == 0
    line = services.save_order_line(line.order, line, {"product": other})
    assert line.unit_price == Decimal("3.0000")
    assert list(services.product_choices(category.pk)) == [product]
    assert set(services.product_choices(None)) == {product, other}


def test_line_status_allocated_or_no_stock():
    """R-orders-009: a new line starts New; saved with product and quantity it is
    Allocated when the available stock (10) covers the quantity, else No Stock."""
    order = order_in()
    covered = services.save_order_line(
        order,
        None,
        {"product": stocked(10), "quantity": 10},
    )
    short = services.save_order_line(
        order,
        None,
        {"product": stocked(3), "quantity": 4},
    )
    assert covered.order_detail_status_id == ODS.ALLOCATED
    assert short.order_detail_status_id == ODS.NO_STOCK


def test_saving_a_line_reallocates_oldest_order_first():
    """R-orders-010: after a line is saved, allocation runs again for its product,
    oldest order first: the stock of 3 goes to the older order's waiting line and
    the new line drops to No Stock."""
    product = stocked(3)
    older = line_on(order_in(order_date=at(2)), product, 3, ODS.NO_STOCK)
    newer = services.save_order_line(
        order_in(order_date=at(5)),
        None,
        {"product": product, "quantity": 3},
    )
    assert status_of(older) == ODS.ALLOCATED
    assert status_of(newer) == ODS.NO_STOCK


def test_changing_a_lines_product_reallocates_the_previous_product():
    """R-orders-010: when a line changes product, allocation runs again for the
    previous product too: its freed stock of 3 goes to the waiting line."""
    product, other = stocked(3), stocked(10)
    moving = line_on(order_in(order_date=at(5)), product, 3, ODS.ALLOCATED)
    waiting = line_on(order_in(order_date=at(6)), product, 3, ODS.NO_STOCK)
    services.save_order_line(moving.order, moving, {"product": other})
    assert status_of(moving) == ODS.ALLOCATED
    assert status_of(waiting) == ODS.ALLOCATED


def test_deleting_a_line_reallocates_its_product():
    """R-orders-010: deleting a line runs allocation again for its product."""
    product = stocked(3)
    deleted = line_on(order_in(order_date=at(5)), product, 3, ODS.ALLOCATED)
    waiting = line_on(order_in(order_date=at(6)), product, 3, ODS.NO_STOCK)
    services.delete_order_line(deleted)
    assert not OrderDetail.objects.filter(pk=deleted.pk).exists()
    assert status_of(waiting) == ODS.ALLOCATED


def test_deleting_an_order_deletes_its_lines_and_reallocates():
    """R-orders-011: deleting an order deletes its lines and re-runs allocation for
    each line's product."""
    product = stocked(3)
    order = order_in(order_date=at(2))
    line_on(order, product, 3, ODS.ALLOCATED)
    waiting = line_on(order_in(order_date=at(3)), product, 3, ODS.NO_STOCK)
    services.delete_order(order)
    assert not Order.objects.filter(pk=order.pk).exists()
    assert not OrderDetail.objects.filter(order_id=order.pk).exists()
    assert status_of(waiting) == ODS.ALLOCATED


def test_only_new_or_invoiced_orders_are_deleted():
    """R-orders-012: a New or Invoiced order can be deleted; a Shipped, Paid or
    Closed one is refused; an unsaved order deletes nothing."""
    for status in (OS.SHIPPED, OS.PAID, OS.CLOSED):
        order = order_in(status)
        with pytest.raises(ValidationError, match="R-orders-012"):
            services.delete_order(order)
        assert Order.objects.filter(pk=order.pk).exists()
    invoiced = order_in(OS.INVOICED)
    services.delete_order(invoiced)
    assert not Order.objects.filter(pk=invoiced.pk).exists()
    services.delete_order(Order(order_status_id=OS.NEW))


def test_lines_are_read_only_once_invoiced():
    """R-orders-013: lines can be added, changed or deleted only while the order is
    New."""
    order = order_in(OS.INVOICED)
    line = line_on(order, stocked(5), 1, ODS.INVOICED)
    with pytest.raises(ValidationError, match="R-orders-013"):
        services.save_order_line(order, None, {"product": stocked(5), "quantity": 1})
    with pytest.raises(ValidationError, match="R-orders-013"):
        services.save_order_line(order, line, {"quantity": 2})
    with pytest.raises(ValidationError, match="R-orders-013"):
        services.delete_order_line(line)
    assert OrderDetail.objects.get(pk=line.pk).quantity == 1


def test_editable_fields_follow_the_status():
    """R-orders-014: which order fields can be edited depends on the status; a
    locked field is refused."""
    expected = {
        None: {
            "customer",
            "employee",
            "notes",
            "shipping_fee",
            "tax_rate",
            "tax_status",
        },
        OS.NEW: {"notes", "shipping_fee", "tax_rate", "tax_status"},
        OS.INVOICED: {"notes", "shipped_date", "shipper"},
        OS.SHIPPED: {"notes", "payment_method", "paid_date"},
        OS.PAID: {"notes"},
        OS.CLOSED: set(),
    }
    assert set(services.editable_order_fields(Order())) == expected[None]
    for status, fields in expected.items():
        if status is not None:
            assert set(services.editable_order_fields(order_in(status))) == fields
    new = order_in(OS.NEW)
    with pytest.raises(ValidationError, match="R-orders-014"):
        services.save_order(new, {"customer": CompanyFactory()})
    services.save_order(new, {"notes": "call first"})
    assert Order.objects.get(pk=new.pk).notes == "call first"


# ---------------------------------------------------------------- workflow


def test_invoice_needs_new_order_allocated_lines_and_fee():
    """R-orders-015: invoicing needs a New order with at least one line, every line
    Allocated and a shipping fee (zero accepted); it sets the order and its lines to
    Invoiced and stamps the invoice date."""
    order = order_in(shipping_fee=Decimal(0))
    with pytest.raises(ValidationError, match="at least one line"):
        services.create_invoice(order)
    product = stocked(5)
    line = line_on(order, product, 1, ODS.ALLOCATED)
    waiting = line_on(order, stocked(5), 1, ODS.NO_STOCK)
    with pytest.raises(ValidationError, match="Allocated"):
        services.create_invoice(order)
    waiting.delete()
    order.shipping_fee = None
    order.save()
    with pytest.raises(ValidationError, match="R-orders-015") as refused:
        services.create_invoice(order)
    assert "shipping_fee" in refused.value.error_dict
    order.shipping_fee = Decimal(0)
    order.save()
    services.create_invoice(order)
    order.refresh_from_db()
    assert order.order_status_id == OS.INVOICED
    assert order.invoice_date is not None
    assert status_of(line) == ODS.INVOICED
    with pytest.raises(ValidationError, match="only a New order"):
        services.create_invoice(order)


def test_shipping_needs_an_invoiced_order_and_its_fields():
    """R-orders-016: shipping needs an Invoiced order, the shipped date, the shipper
    and the fee; it sets the order and every line to Shipped."""
    shipper = ShipperFactory()
    new = order_in(OS.NEW, shipping_fee=Decimal(5))
    with pytest.raises(ValidationError, match="only an Invoiced order"):
        services.ship_order(new, shipped_date=at(9), shipper=shipper)
    order = order_in(OS.INVOICED, shipping_fee=None)
    line = line_on(order, stocked(5), 1, ODS.INVOICED)
    with pytest.raises(ValidationError, match="R-orders-016") as refused:
        services.ship_order(order, shipped_date=None, shipper=None)
    assert set(refused.value.error_dict) == {"shipped_date", "shipper", "shipping_fee"}
    services.ship_order(
        order,
        shipped_date=at(9),
        shipper=shipper,
        shipping_fee=Decimal(7),
    )
    order.refresh_from_db()
    assert order.order_status_id == OS.SHIPPED
    assert (order.shipped_date, order.shipper, order.shipping_fee) == (
        at(9),
        shipper,
        7,
    )
    assert status_of(line) == ODS.SHIPPED


def test_payment_needs_a_shipped_order_method_and_date():
    """R-orders-017: receiving payment needs a Shipped order, a payment method from
    the fixed list and the paid date; it sets the order to Paid."""
    with pytest.raises(ValidationError, match="only a Shipped order"):
        services.receive_payment(
            order_in(OS.INVOICED),
            payment_method=PaymentMethod.CASH,
            paid_date=at(10),
        )
    order = order_in(OS.SHIPPED)
    with pytest.raises(ValidationError, match="R-orders-017") as refused:
        services.receive_payment(order, payment_method="Barter", paid_date=None)
    assert set(refused.value.error_dict) == {"payment_method", "paid_date"}
    services.receive_payment(
        order,
        payment_method=PaymentMethod.CHECK,
        paid_date=at(10),
    )
    order.refresh_from_db()
    assert (order.order_status_id, order.payment_method, order.paid_date) == (
        OS.PAID,
        "Check",
        at(10),
    )


def test_closing_needs_a_paid_order_and_confirmation():
    """R-orders-018: closing needs a Paid order and the user's confirmation; a
    Closed order cannot be edited."""
    with pytest.raises(ValidationError, match="only a Paid order"):
        services.close_order(order_in(OS.SHIPPED), confirmed=True)
    order = order_in(OS.PAID)
    with pytest.raises(ValidationError, match="confirm"):
        services.close_order(order, confirmed=False)
    assert Order.objects.get(pk=order.pk).order_status_id == OS.PAID
    services.close_order(order, confirmed=True)
    assert Order.objects.get(pk=order.pk).order_status_id == OS.CLOSED
    with pytest.raises(ValidationError, match="R-orders-014"):
        services.save_order(order, {"notes": "late note"})


def test_reprinting_the_invoice_changes_nothing(client, staff):
    """R-orders-019: past New the invoice can be opened again and that changes
    neither the order nor its lines; on a New order no reprint is offered."""
    assert not services.can_reprint_invoice(order_in(OS.NEW))
    assert not services.can_reprint_invoice(Order())
    order = order_in(OS.INVOICED, customer=CompanyFactory(), invoice_date=at(3))
    line = line_on(order, stocked(5), 2, ODS.INVOICED)
    assert services.can_reprint_invoice(order)
    before = Order.objects.filter(pk=order.pk).values().get()
    line_before = OrderDetail.objects.filter(pk=line.pk).values().get()
    client.force_login(staff)
    for query in ("", "?format=pdf"):
        url = reverse("orders:report_rptInvoice", kwargs={"pk": order.pk}) + query
        assert client.get(url).status_code == HTTPStatus.OK
    assert Order.objects.filter(pk=order.pk).values().get() == before
    assert OrderDetail.objects.filter(pk=line.pk).values().get() == line_before


def test_invoice_without_lines_has_nothing_to_print(client, staff):
    """R-orders-021: opening the invoice of an order without lines shows a nothing
    to print message instead of an empty invoice."""
    order = order_in(OS.INVOICED)
    assert services.invoice_for(order) is None
    client.force_login(staff)
    url = reverse("orders:report_rptInvoice", kwargs={"pk": order.pk})
    response = client.get(url)
    assert b"nothing to print" in response.content
    assert b"invoice-lines" not in response.content
    pdf = client.get(url + "?format=pdf")
    assert pdf.status_code == HTTPStatus.FOUND


def test_order_screen_amounts():
    """R-orders-022: line price = quantity x (1 - discount) x unit price; subtotal =
    2 x 0.9 x 10.00 + 1 x 5.00 = 23.00; tax = 0.1 x 23.00 = 2.30 when Taxable, 0
    otherwise; total = subtotal + tax + fee, a blank fee counting as 0, and a zero
    fee is never taxed."""
    order = order_in(
        tax_status__tax_status_id=TaxStatusCode.TAXABLE,
        tax_rate=0.1,
        shipping_fee=Decimal("0.0000"),
    )
    first = line_on(order, stocked(9), 2, unit_price=Decimal("10.0000"), discount=0.1)
    line_on(order, stocked(9), 1, unit_price=Decimal("5.0000"), discount=0.0)
    assert services.line_price(first) == Decimal("18.0000")
    amounts = services.order_amounts(order)
    assert (amounts.subtotal, amounts.tax, amounts.shipping, amounts.total) == (
        Decimal("23.0000"),
        Decimal("2.3000"),
        Decimal("0.0000"),
        Decimal("25.3000"),
    )
    order.tax_status_id = TaxStatusCode.TAX_EXEMPT
    order.shipping_fee = None
    amounts = services.order_amounts(order)
    assert (amounts.tax, amounts.total) == (Decimal("0.0000"), Decimal("23.0000"))
    order.shipping_fee = Decimal("4.5000")
    assert services.order_amounts(order).total == Decimal("27.5000")


# ---------------------------------------------------------------- order list


def test_order_list_filters(staff):
    """R-orders-025: Open orders (all but Closed, the default), Recent orders (order
    date within 30 days), My orders (the signed-in employee's) and All orders."""
    today = at(31)
    closed = order_in(OS.CLOSED, order_date=at(30))
    recent = order_in(OS.NEW, order_date=at(2), employee=staff.employee)
    old = order_in(OS.PAID, order_date=at(30, month=11) - dt.timedelta(days=365))
    orders = Order.objects.all()

    def ids(choice):
        return set(
            services.filter_order_list(
                orders,
                choice,
                user=staff,
                today=today,
            ).values_list(
                "pk",
                flat=True,
            ),
        )

    assert ids(None) == ids("open") == {recent.pk, old.pk}
    assert ids("recent") == {closed.pk, recent.pk}
    assert ids("mine") == {recent.pk}
    assert ids("all") == {closed.pk, recent.pk, old.pk}
    assert services.DEFAULT_ORDER_FILTER == "open"


def test_order_list_opens_on_open_orders(client, staff):
    """R-orders-025: the list opens with the Open orders filter and tells the user
    when there are no recent orders."""
    customer = CompanyFactory()
    order_in(OS.CLOSED, customer=customer)
    shown = order_in(OS.NEW, customer=customer)
    client.force_login(staff)
    response = client.get(reverse("orders:form_frmOrderList"))
    assert [row.record.pk for row in response.context["table"].rows] == [shown.pk]
    response = client.get(reverse("orders:form_frmOrderList") + "?show=recent")
    assert b"There are no recent orders." in response.content


def test_order_list_footer_counts_and_sums(client, staff):
    """R-orders-026: the footer shows the number of orders shown and the sum of their
    totals: 2 x 10.00 + 3 x 1.50 = 24.50 for two orders."""
    customer = CompanyFactory()
    first = order_in(OS.NEW, customer=customer)
    second = order_in(OS.NEW, customer=customer)
    line_on(first, stocked(5), 2, unit_price=Decimal(10), discount=0.0)
    line_on(second, stocked(5), 3, unit_price=Decimal("1.5"), discount=0.0)
    order_in(OS.CLOSED, customer=customer)
    count, total = services.order_list_footer(
        services.filter_order_list(services.queries.order_list(), "open"),
    )
    assert (count, total) == (2, Decimal("24.5000"))
    client.force_login(staff)
    response = client.get(reverse("orders:form_frmOrderList"))
    assert (response.context["footer_count"], response.context["footer_total"]) == (
        2,
        Decimal("24.5000"),
    )


# ---------------------------------------------------------------- audit and history


def test_audit_stamps_name_the_signed_in_employee(staff):
    """R-orders-031: inserts set created and modified by and on to the signed-in
    employee's full name; updates keep the created stamps; without anybody signed in
    the name is System."""
    order = services.new_order(staff)
    services.save_order(
        order,
        {"customer": CompanyFactory(), "employee": staff.employee},
        user=staff,
    )
    stored = Order.objects.get(pk=order.pk)
    assert (stored.added_by, stored.modified_by) == ("Pat Lee", "Pat Lee")
    created_on = stored.added_on
    services.save_order(stored, {"notes": "by the system"})
    stored = Order.objects.get(pk=order.pk)
    assert (stored.added_by, stored.added_on, stored.modified_by) == (
        "Pat Lee",
        created_on,
        SYSTEM,
    )


def test_record_history_line():
    """R-orders-032: the history line says when and by whom the record was created
    and last modified, leaving out the blank parts."""
    order = order_in()
    order.added_by, order.added_on = "Pat Lee", dt.datetime(2024, 1, 15, 10, 30)  # noqa: DTZ001
    order.modified_by, order.modified_on = "Sam Roe", dt.datetime(2024, 1, 16)  # noqa: DTZ001
    assert services.record_history(order) == (
        "Created 1/15/2024 10:30:00 AM by Pat Lee ~ Modified 1/16/2024 by Sam Roe"
    )
    order.added_by, order.modified_on = None, None
    assert services.record_history(order) == (
        "Created 1/15/2024 10:30:00 AM ~ Modified by Sam Roe"
    )
    order.added_on, order.modified_by = None, None
    assert services.record_history(order) == ""


# ---------------------------------------------------------------- companies


def test_company_delete_rules():
    """R-orders-033: a company with orders as customer, as shipper or purchase orders
    cannot be deleted (the counts are given); otherwise, once confirmed, it is
    deleted with its contacts and vendor-product links."""
    customer = CompanyFactory()
    order_in(customer=customer)
    with pytest.raises(ValidationError, match="1 orders as customer"):
        services.delete_company(customer, confirmed=True)
    vendor = VendorFactory()
    PurchaseOrderFactory(vendor=vendor)
    with pytest.raises(ValidationError, match="1 purchase orders"):
        services.delete_company(vendor, confirmed=True)
    idle = VendorFactory()
    ContactFactory(company=idle)
    ContactFactory(company=idle)
    ProductVendorFactory(vendor=idle)
    with pytest.raises(ValidationError, match="2 contacts and 1 vendor-product links"):
        services.delete_company(idle, confirmed=False)
    assert Company.objects.filter(pk=idle.pk).exists()
    services.delete_company(idle, confirmed=True)
    assert not Company.objects.filter(pk=idle.pk).exists()
    assert not Contact.objects.filter(company_id=idle.pk).exists()
    assert not ProductVendor.objects.filter(vendor_id=idle.pk).exists()


def test_company_type_change_rules():
    """R-orders-034: the type cannot change while the company has orders, shipments,
    purchase orders or vendor-product links."""
    vendor = VendorFactory()
    ProductVendorFactory(vendor=vendor)
    with pytest.raises(ValidationError, match="R-orders-034"):
        services.change_company_type(vendor, CompanyTypeCode.CUSTOMER)
    assert Company.objects.get(pk=vendor.pk).company_type_id == CompanyTypeCode.VENDOR
    shipper = ShipperFactory()
    order_in(shipper=shipper)
    with pytest.raises(ValidationError, match="R-orders-034"):
        services.save_company(
            shipper,
            {"company_type": CompanyTypeCode.VENDOR},
            confirmed=True,
        )
    unused = VendorFactory()
    services.change_company_type(unused, CompanyTypeCode.CUSTOMER)
    assert Company.objects.get(pk=unused.pk).company_type_id == CompanyTypeCode.CUSTOMER


def test_company_screen_follows_the_type(client, staff):
    """R-orders-035: the company screen is titled with the company type and shows the
    related list that fits it."""
    assert (
        services.company_related_list(CompanyTypeCode.CUSTOMER)[0] == "customer_orders"
    )
    assert services.company_related_list(CompanyTypeCode.SHIPPER)[0] == "shipper_orders"
    assert services.company_related_list(CompanyTypeCode.VENDOR)[0] == "purchase_orders"
    assert services.company_related_list(CompanyTypeCode.OWN_COMPANY) is None
    client.force_login(staff)
    shipper = ShipperFactory(company_name="Fast Freight")
    response = client.get(
        reverse("orders:form_frmCompanyDetail", kwargs={"pk": shipper.pk}),
    )
    assert b"Shipper: Fast Freight" in response.content
    assert b'id="shipper-orders"' in response.content
    assert b'id="customer-orders"' not in response.content


def test_company_save_asks_for_confirmation(client, staff):
    """R-orders-036: saving the company screen asks first; without the confirmation
    nothing is saved."""
    company = CompanyFactory(company_name="Before")
    with pytest.raises(ValidationError, match="R-orders-036"):
        services.save_company(company, {"company_name": "After"}, confirmed=False)
    assert Company.objects.get(pk=company.pk).company_name == "Before"
    client.force_login(staff)
    url = reverse("orders:company_update", kwargs={"pk": company.pk})
    data = {
        "company_name": "After",
        "company_type": company.company_type_id,
        "address": company.address,
        "city": company.city,
        "state": company.state_id,
        "zip": company.zip,
        "standard_tax_status": company.standard_tax_status_id,
    }
    response = client.post(url, data)
    assert b'id="confirm-save"' in response.content
    assert Company.objects.get(pk=company.pk).company_name == "Before"
    response = client.post(url, {**data, "confirmed": "yes"})
    assert response.status_code == HTTPStatus.FOUND
    assert Company.objects.get(pk=company.pk).company_name == "After"


def test_company_list_filter_and_new_company_type(client, staff):
    """R-orders-037: the company list filters to Customers, Shippers, Vendors or all
    with a matching heading, and a new company from the list takes the filtered
    type."""
    customer, shipper, vendor = CompanyFactory(), ShipperFactory(), VendorFactory()
    companies = Company.objects.all()
    assert set(services.filter_company_list(companies, "shippers")) == {shipper}
    assert set(services.filter_company_list(companies, "vendors")) == {vendor}
    assert set(services.filter_company_list(companies, "all")) == {
        customer,
        shipper,
        vendor,
    }
    client.force_login(staff)
    response = client.get(reverse("orders:form_frmCompanyList") + "?show=shippers")
    assert response.context["heading"] == "Shippers"
    assert [row.record.pk for row in response.context["table"].rows] == [shipper.pk]
    response = client.get(reverse("orders:company_create") + "?show=shippers")
    assert response.context["form"].initial["company_type"] == CompanyTypeCode.SHIPPER


def test_new_customer_name_from_the_order(client, staff):
    """R-orders-038: a customer name typed on the order that does not exist opens the
    company screen on a new customer with that name filled in."""
    client.force_login(staff)
    url = reverse("orders:company_create") + "?show=customers&name=Brand+New+Co"
    form = client.get(url).context["form"]
    assert form.initial["company_name"] == "Brand New Co"
    assert form.initial["company_type"] == CompanyTypeCode.CUSTOMER


# ---------------------------------------------------------------- employees


def test_employee_delete_rules():
    """R-orders-040: an employee with orders, submitted purchase orders, supervised
    employees or privileges cannot be deleted, and every reason is given; otherwise
    the user confirms by the employee's name."""
    busy = EmployeeFactory(first_name="Ann", last_name="Busy")
    order_in(employee=busy)
    PurchaseOrderFactory(submitted_by=busy)
    EmployeeFactory(supervisor=busy)
    EmployeePrivilegeFactory(employee=busy)
    with pytest.raises(ValidationError) as refused:
        services.delete_employee(busy, confirmed=True)
    message = str(refused.value)
    for reason in ("1 orders", "1 purchase orders", "supervises 1", "1 privileges"):
        assert reason in message
    free = EmployeeFactory(first_name="Bo", last_name="Free")
    with pytest.raises(ValidationError, match="confirm deleting Bo Free"):
        services.delete_employee(free, confirmed=False)
    services.delete_employee(free, confirmed=True)
    assert not Employee.objects.filter(pk=free.pk).exists()


def test_employee_is_not_their_own_supervisor():
    """R-orders-041: the supervisor list leaves out the employee being edited, and an
    employee cannot be saved as their own supervisor."""
    employee, other = EmployeeFactory(), EmployeeFactory()
    assert set(services.supervisor_choices(employee)) == {other}
    with pytest.raises(ValidationError, match="R-orders-041"):
        services.save_employee(employee, {"supervisor": employee})
    services.save_employee(employee, {"supervisor": other})
    assert Employee.objects.get(pk=employee.pk).supervisor == other


def test_new_employee_opens_the_privilege_screen(client, staff):
    """R-orders-042: after a new employee is saved, the privilege screen opens for
    that employee."""
    client.force_login(staff)
    response = client.post(
        reverse("orders:employee_create"),
        {"first_name": "Nia", "last_name": "New", "job_title": "Buyer"},
    )
    employee = Employee.objects.get(first_name="Nia", last_name="New")
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse(
        "orders:form_sfrmEmployee_Privileges",
        kwargs={"pk": employee.pk},
    )


def test_title_comes_from_the_titles_list(client, staff):
    """R-orders-044: an employee's title must be in the titles list; a new title is
    added on the title screen, pre-filled with the typed value."""
    employee = EmployeeFactory()
    with pytest.raises(ValidationError, match="R-orders-044"):
        services.save_employee(employee, {"title": "Dr."})
    services.add_title("Dr.")
    services.save_employee(employee, {"title": "Dr."})
    assert Employee.objects.get(pk=employee.pk).title_id == "Dr."
    client.force_login(staff)
    form = client.get(
        reverse("orders:form_frmEmployeeTitles") + "?title=Prof.",
    ).context["form"]
    assert form.initial["title"] == "Prof."


def test_phone_numbers_are_us_format():
    """R-orders-045: ten digits shown 3-3-4, optionally followed by an extension of up
    to eight characters; anything else (international numbers) is refused."""
    assert services.clean_phone("555-123-4567") == "5551234567"
    assert services.clean_phone("(555) 123-4567 x204") == "5551234567x204"
    assert services.clean_phone("") is None
    assert services.format_phone("5551234567x204") == "555-123-4567 x204"
    for bad in ("12345", "+44 20 7946 0958", "555-123-4567 extension 1234"):
        with pytest.raises(ValidationError, match="R-orders-045"):
            services.clean_phone(bad)
    employee = EmployeeFactory()
    with pytest.raises(ValidationError, match="R-orders-045"):
        services.save_employee(employee, {"primary_phone": "020 7946 0958"})
    services.save_employee(employee, {"primary_phone": "555 123 4567"})
    assert Employee.objects.get(pk=employee.pk).primary_phone == "5551234567"


def test_names_are_unique():
    """R-orders-046: a company name once per type, a contact's name once per company,
    an employee's name once, an operating-system login on one employee and each
    title once."""
    EmployeeFactory(first_name="Ann", last_name="Lee", windows_user_name="alee")
    with pytest.raises(ValidationError, match="R-orders-046"):
        services.save_employee(
            Employee(),
            {"first_name": "Ann", "last_name": "Lee", "job_title": "Clerk"},
        )
    with pytest.raises(ValidationError, match="R-orders-046"):
        services.save_employee(
            Employee(),
            {
                "first_name": "Bo",
                "last_name": "Lee",
                "job_title": "Clerk",
                "windows_user_name": "alee",
            },
        )
    state = StateFactory()
    CompanyFactory(company_name="Acme", state=state)
    data = {
        "company_name": "Acme",
        "company_type": CompanyTypeCode.CUSTOMER,
        "address": "1 Way",
        "city": "Town",
        "state": state,
        "zip": "12345",
    }
    with pytest.raises(ValidationError, match="R-orders-046"):
        services.save_company(Company(), data, confirmed=True)
    shipper = services.save_company(
        Company(),
        {
            **data,
            "company_type": CompanyTypeFactory(company_type_id=CompanyTypeCode.SHIPPER),
        },
        confirmed=True,
    )
    assert shipper.pk is not None
    TitleFactory(title="Ms.")
    with pytest.raises(ValidationError, match="R-orders-046"):
        services.add_title("Ms.")


def test_new_company_is_tax_exempt():
    """R-orders-048: a new company's standard tax status is Tax Exempt unless the
    user picks another."""
    company = services.save_company(
        Company(),
        {
            "company_name": "New Buyer",
            "company_type": CompanyTypeCode.CUSTOMER,
            "address": "1 Way",
            "city": "Town",
            "state": StateFactory(),
            "zip": "12345",
            "standard_tax_status": None,
        },
        confirmed=True,
    )
    assert company.standard_tax_status_id == TaxStatusCode.TAX_EXEMPT


# ---------------------------------------------------------------- start-up


def test_first_run_shifts_dates_once():
    """R-orders-049: the start-up command moves every date forward by the days
    between the latest order date (15 January) and today (25 January), 10 days,
    stamps the changed rows System, sets the first-run flag and never runs again."""
    latest = order_in(order_date=dt.datetime(2024, 1, 15, 10, 30))  # noqa: DTZ001
    earlier = order_in(order_date=at(3), shipped_date=at(4))
    call_command("first_run", today="2024-01-25")
    latest.refresh_from_db()
    earlier.refresh_from_db()
    assert latest.order_date == dt.datetime(2024, 1, 25, 10, 30)  # noqa: DTZ001
    assert (earlier.order_date, earlier.shipped_date) == (at(13), at(14))
    assert earlier.modified_by == SYSTEM
    assert (
        SystemSetting.objects.get(pk=SystemSettingCode.FIRST_RUN).setting_value == "-1"
    )
    assert services.first_run_done()
    call_command("first_run", today="2024-02-25")
    latest.refresh_from_db()
    assert latest.order_date == dt.datetime(2024, 1, 25, 10, 30)  # noqa: DTZ001


def test_first_run_never_moves_dates_backwards():
    """R-orders-049: when the latest order date is after today nothing moves, but the
    flag is still set."""
    order = order_in(order_date=at(20))
    result = services.first_run(at(10))
    assert (result.ran, result.days, result.rows) == (True, 0, 0)
    assert Order.objects.get(pk=order.pk).order_date == at(20)
    assert services.first_run_done()
