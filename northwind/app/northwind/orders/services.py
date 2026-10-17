"""Services of the Orders, Invoicing and Shipping area: one function per services[]
entry of analysis/interfaces.md for this area, plus the record saves the area's
screens make (order header, company, contact, employee, title, privilege grant).

Views call a service for every write. A service checks its rules first; a refused
action raises ValidationError with a plain message that names the rule id and changes
nothing. Every write runs inside `transaction.atomic()` and `acting_for(user)`, so the
audit stamps carry the signed-in employee's name (R-orders-031, legacy/audit.py).
Shared calculations come from the domain app: stock figures and allocation
(domain.inventory), line amounts and order totals (domain.sales), the signed-in
employee (domain.people) and the tax rate setting (domain.system_settings).

No data macro with a side effect (After Insert, After Update, After Delete) exists on
this area's tables (S4.models notes); the Before Change audit stamps are legacy's.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.db.models import Max
from django.db.models import Sum
from simple_history.models import HistoricalChanges

from northwind.core import vbacompat
from northwind.domain.inventory import allocate_inventory
from northwind.domain.inventory import product_available
from northwind.domain.people import acting_for
from northwind.domain.people import signed_in_employee
from northwind.domain.sales import line_amount
from northwind.domain.sales import order_total
from northwind.domain.system_settings import sales_tax_rate
from northwind.domain.system_settings import system_setting
from northwind.legacy import audit
from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.choices import PaymentMethod
from northwind.legacy.choices import SystemSettingCode
from northwind.legacy.choices import TaxStatusCode
from northwind.legacy.models import Company
from northwind.legacy.models import Contact
from northwind.legacy.models import Employee
from northwind.legacy.models import EmployeePrivilege
from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Privilege
from northwind.legacy.models import Product
from northwind.legacy.models import ProductVendor
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import SystemSetting
from northwind.legacy.models import Title

from . import queries

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from django.db.models import QuerySet

OS = OrderStatusCode
ODS = OrderDetailStatusCode

#: The main table of the area (the skeleton's example screens used it).
Record = Order

# ---------------------------------------------------------------- refusals


def refuse(rule: str, text: str, *, field: str | None = None) -> NoReturn:
    """Raise the ValidationError of a refused action: '<rule id>: <text>'."""
    message = f"{rule}: {text}"
    error = ValidationError(message, code=rule)
    if field is not None:
        raise ValidationError({field: error})
    raise error


def _label(instance: models.Model, name: str) -> str:
    return str(instance._meta.get_field(name).verbose_name)  # noqa: SLF001


def check_required(instance: models.Model, rule: str = "R-orders-005") -> None:
    """Refuse a save while a column the table marks as required is blank; the error
    names each blank field, so the form highlights them (R-orders-005)."""
    blanks = {}
    for field in instance._meta.concrete_fields:  # noqa: SLF001
        if field.primary_key or field.blank or not field.editable:
            continue
        if getattr(instance, field.attname) in (None, ""):
            message = f"{rule}: {field.verbose_name} is required."
            blanks[field.name] = ValidationError(message, code=rule)
    if blanks:
        raise ValidationError(blanks)


def check_unique(instance: models.Model, rule: str = "R-orders-046") -> None:
    """Refuse a duplicate name (the tables' unique indexes, R-orders-046)."""
    try:
        instance.validate_unique()
        instance.validate_constraints()
    except ValidationError as error:
        refuse(rule, " ".join(error.messages))


def _plain(value: Any) -> Any:
    return value.pk if isinstance(value, models.Model) else value


def _stored(instance: models.Model, name: str) -> Any:
    return getattr(instance, instance._meta.get_field(name).attname)  # noqa: SLF001


def _changed(instance: models.Model, data: Mapping[str, Any]) -> list[str]:
    """The fields of `data` whose value differs from the instance's."""
    return [
        name for name, value in data.items() if _plain(value) != _stored(instance, name)
    ]


def _assign(instance: models.Model, data: Mapping[str, Any]) -> None:
    """Set the fields of `data`; a relation takes a model instance or its key."""
    for name, value in data.items():
        field = instance._meta.get_field(name)  # noqa: SLF001
        if (
            field.is_relation
            and value is not None
            and not isinstance(value, models.Model)
        ):
            setattr(instance, field.attname, value)
        else:
            setattr(instance, name, value)


def _require_type(
    company: Company | None,
    company_type: int,
    *,
    field: str,
    rule: str = "R-orders-003",
) -> None:
    """The customer must be a Customer and the shipper a Shipper (R-orders-003)."""
    if company is not None and company.company_type_id != company_type:
        label = CompanyTypeCode(company_type).label
        refuse(rule, f"choose a company whose type is {label}.", field=field)


# ---------------------------------------------------------------- phone numbers

PHONE_FIELDS = ("business_phone", "primary_phone", "secondary_phone")
PHONE = re.compile(r"\(?(\d{3})\)?[-. ]?(\d{3})[-. ]?(\d{4})(?:\s*(\S.{0,7}))?")
PHONE_STORED = re.compile(r"(\d{3})(\d{3})(\d{4})(.*)")


def clean_phone(value: str | None, *, field: str | None = None) -> str | None:
    """A phone number as the original's input mask takes it (R-orders-045): ten
    digits, entered or shown as 3-3-4, optionally followed by an extension of up to
    eight characters. Stored as the typed characters only (ten digits, then the
    extension), as the mask stores it. Blank stays blank."""
    text = (value or "").strip()
    if not text:
        return None
    match = PHONE.fullmatch(text)
    if match is None:
        refuse(
            "R-orders-045",
            "enter the phone number as ten digits (3-3-4), optionally followed by "
            "an extension of up to eight characters.",
            field=field,
        )
    area, exchange, number, extension = match.groups()
    return f"{area}{exchange}{number}{extension or ''}"


def format_phone(value: str | None) -> str:
    """A stored phone number shown as 3-3-4 digits and the extension
    (R-orders-045); a value in another shape is shown as stored."""
    match = PHONE_STORED.fullmatch(value or "")
    if match is None:
        return value or ""
    area, exchange, number, extension = match.groups()
    shown = f"{area}-{exchange}-{number}"
    return f"{shown} {extension.strip()}" if extension.strip() else shown


def _clean_phones(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        name: clean_phone(value, field=name) if name in PHONE_FIELDS else value
        for name, value in data.items()
    }


# ---------------------------------------------------------------- record history


def record_history(instance: models.Model) -> str:
    """The one-line history of a record: when and by whom it was created and last
    modified, leaving out the blank parts (R-orders-032)."""
    parts = []
    for verb, by, on in (
        ("Created", instance.added_by, instance.added_on),
        ("Modified", instance.modified_by, instance.modified_on),
    ):
        if not by and not on:
            continue
        text = verb
        if on:
            text += f" {vbacompat.general_date(on)}"
        if by:
            text += f" by {by}"
        parts.append(text)
    return " ~ ".join(parts)


# ---------------------------------------------------------------- order header

#: The order fields a user edits, by order status (R-orders-014); None is unsaved.
EDITABLE_ORDER_FIELDS: dict[int | None, tuple[str, ...]] = {
    None: ("customer", "employee", "notes", "shipping_fee", "tax_rate", "tax_status"),
    OS.NEW: ("notes", "shipping_fee", "tax_rate", "tax_status"),
    OS.INVOICED: ("notes", "shipped_date", "shipper"),
    OS.SHIPPED: ("notes", "payment_method", "paid_date"),
    OS.PAID: ("notes",),
    OS.CLOSED: (),
}


def editable_order_fields(order: Order) -> tuple[str, ...]:
    """The fields of the order a user may edit in its current status
    (R-orders-014)."""
    status = None if order.pk is None else order.order_status_id
    return EDITABLE_ORDER_FIELDS.get(status, ())


def new_order(user: Any = None) -> Order:
    """A new, unsaved order pre-filled as the original does (R-orders-001): the
    signed-in employee as salesperson, the default sales tax rate, status New and
    the current date and time as order date."""
    return Order(
        employee=signed_in_employee(user),
        tax_rate=sales_tax_rate(),
        order_status_id=OS.NEW,
        order_date=audit.stamp_time(),
    )


def customer_tax_status(customer: Company | int | None) -> int | None:
    """The customer's standard tax status, the order's default (R-orders-002)."""
    if customer is None:
        return None
    return (
        Company.objects.filter(pk=_plain(customer))
        .values_list("standard_tax_status_id", flat=True)
        .first()
    )


def save_order(order: Order, data: Mapping[str, Any], *, user: Any = None) -> Order:
    """Create or edit an order header.

    Only the fields the order's status leaves editable may change (R-orders-014);
    choosing the customer of a new order sets its tax status to the customer's
    standard one unless the user chose one (R-orders-002); the customer must be a
    Customer and the shipper a Shipper (R-orders-003); required fields must be
    filled in (R-orders-005)."""
    creating = order.pk is None
    allowed = editable_order_fields(order)
    locked = [name for name in _changed(order, data) if name not in allowed]
    if locked:
        names = ", ".join(_label(order, name) for name in locked)
        status = "unsaved" if creating else order.order_status.order_status_name
        refuse(
            "R-orders-014",
            f"{names} cannot be changed while the order is {status}.",
        )
    customer_changed = "customer" in _changed(order, data)
    _assign(order, data)
    if creating:
        order.order_status_id = order.order_status_id or OS.NEW
        if order.order_date is None:
            order.order_date = audit.stamp_time()
    if customer_changed and "tax_status" not in data and order.customer_id:
        order.tax_status_id = customer_tax_status(order.customer_id)
    _require_type(
        order.customer if order.customer_id else None,
        queries.CUSTOMER,
        field="customer",
    )
    _require_type(order.shipper, queries.SHIPPER, field="shipper")
    check_required(order)
    with transaction.atomic(), acting_for(user):
        order.save()
    return order


# ---------------------------------------------------------------- order lines


def product_choices(category: int | None = None) -> QuerySet:
    """The products an order line offers, narrowed to one category or all
    (R-orders-008); discontinued products stay selectable (Q-inventory-005)."""
    products = Product.objects.order_by("product_name")
    if category:
        products = products.filter(product_category_id=category)
    return products


def _require_new_order(order: Order) -> None:
    if order.pk is None:
        refuse("R-orders-004", "save the order before entering its lines.")
    if order.order_status_id != OS.NEW:
        refuse(
            "R-orders-013",
            "order lines can be added, changed or deleted only while the order is New.",
        )


def save_order_line(
    order: Order,
    line: OrderDetail | None,
    data: Mapping[str, Any],
    *,
    user: Any = None,
) -> OrderDetail:
    """Add or change an order line (interfaces.md save_order_line).

    The order must be saved (R-orders-004) and New (R-orders-013). Choosing a product
    copies its list price into the unit price; a new line's discount starts at zero
    (R-orders-008). The quantity must be above zero (R-orders-006), a product appears
    once per order (R-orders-007) and required fields must be filled (R-orders-005).
    A new line starts New and, with product and quantity, becomes Allocated when the
    product's available stock covers the whole quantity, else No Stock
    (R-orders-009). Then stock allocation runs again for the product, and for the
    previous product when it changed (R-orders-010)."""
    _require_new_order(order)
    if line is None:
        line = OrderDetail(order=order, order_detail_status_id=ODS.NEW, discount=0.0)
    previous_product = line.product_id if line.pk else None
    _assign(
        line,
        {k: v for k, v in data.items() if k in ("product", "quantity", "discount")},
    )
    if line.product_id and line.product_id != previous_product:
        price = line.product.unit_price
        if price is None:
            line.product = None
        else:
            line.unit_price = price
    if line.quantity is not None and line.quantity <= 0:
        refuse(
            "R-orders-006",
            "the quantity must be greater than zero.",
            field="quantity",
        )
    duplicate = OrderDetail.objects.filter(order=order, product_id=line.product_id)
    if line.product_id and duplicate.exclude(pk=line.pk).exists():
        refuse("R-orders-007", "this product is already on the order.", field="product")
    check_required(line)
    if product_available(line.product_id) >= line.quantity:
        line.order_detail_status_id = ODS.ALLOCATED
    else:
        line.order_detail_status_id = ODS.NO_STOCK
    with transaction.atomic(), acting_for(user):
        line.save()
        if previous_product and previous_product != line.product_id:
            allocate_inventory(previous_product)
        allocate_inventory(line.product_id)
    line.refresh_from_db()
    return line


def delete_order_line(line: OrderDetail, *, user: Any = None) -> None:
    """Delete an order line of a New order and re-run stock allocation for its
    product (R-orders-010, R-orders-013). The screen asks for confirmation first."""
    _require_new_order(line.order)
    product_id = line.product_id
    with transaction.atomic(), acting_for(user):
        line.delete()
        allocate_inventory(product_id)


# ---------------------------------------------------------------- order workflow


def _set_line_status(order: Order, status: int) -> None:
    for line in order.lines.order_by("pk"):
        line.order_detail_status_id = status
        line.save(update_fields=["order_detail_status"])


def _require_saved(order: Order, rule: str) -> None:
    if order.pk is None:
        refuse(rule, "save the order first.")


def create_invoice(order: Order, *, user: Any = None) -> Order:
    """Invoice a New order (R-orders-015): it needs at least one line, every line
    Allocated (no partial invoices) and a shipping fee (zero is accepted, blank is
    not). Sets the status to Invoiced, the invoice date to now and every line to
    Invoiced; the screen then opens the invoice (R-orders-020)."""
    rule = "R-orders-015"
    _require_saved(order, rule)
    if order.order_status_id != OS.NEW:
        refuse(rule, "only a New order can be invoiced.")
    lines = order.lines.all()
    if not lines.exists():
        refuse(rule, "an order needs at least one line before it is invoiced.")
    if lines.exclude(order_detail_status_id=ODS.ALLOCATED).exists():
        refuse(
            rule,
            "every line must be Allocated; partial invoices are not supported.",
        )
    if order.shipping_fee is None:
        refuse(
            rule,
            "fill in the shipping fee (zero is accepted).",
            field="shipping_fee",
        )
    with transaction.atomic(), acting_for(user):
        order.order_status_id = OS.INVOICED
        order.invoice_date = audit.stamp_time()
        order.save()
        _set_line_status(order, ODS.INVOICED)
    return order


def ship_order(
    order: Order,
    *,
    shipped_date: dt.datetime | None,
    shipper: Company | None,
    shipping_fee: Decimal | None = None,
    user: Any = None,
) -> Order:
    """Ship an Invoiced order (R-orders-016): it needs the shipped date, the shipper
    and the shipping fee, and sets the order and every line to Shipped. The shipped
    date may be any date. The fee is the order's own unless it has none yet."""
    rule = "R-orders-016"
    _require_saved(order, rule)
    if order.order_status_id != OS.INVOICED:
        refuse(rule, "only an Invoiced order can be shipped.")
    fee = order.shipping_fee if order.shipping_fee is not None else shipping_fee
    missing = {
        name: ValidationError(
            f"{rule}: fill in the {label} to ship the order.",
            code=rule,
        )
        for name, label, value in (
            ("shipped_date", "shipped date", shipped_date),
            ("shipper", "shipper", shipper),
            ("shipping_fee", "shipping fee", fee),
        )
        if value is None
    }
    if missing:
        raise ValidationError(missing)
    _require_type(shipper, queries.SHIPPER, field="shipper")
    with transaction.atomic(), acting_for(user):
        order.shipped_date = shipped_date
        order.shipper = shipper
        order.shipping_fee = fee
        order.order_status_id = OS.SHIPPED
        order.save()
        _set_line_status(order, ODS.SHIPPED)
    return order


def receive_payment(
    order: Order,
    *,
    payment_method: str | None,
    paid_date: dt.datetime | None,
    user: Any = None,
) -> Order:
    """Receive payment for a Shipped order (R-orders-017): it needs one of the fixed
    payment methods and the paid date, and sets the order to Paid. The paid date may
    be any date."""
    rule = "R-orders-017"
    _require_saved(order, rule)
    if order.order_status_id != OS.SHIPPED:
        refuse(rule, "only a Shipped order can be paid.")
    missing = {}
    if payment_method not in PaymentMethod.values:
        missing["payment_method"] = ValidationError(
            f"{rule}: choose the payment method.",
            code=rule,
        )
    if paid_date is None:
        missing["paid_date"] = ValidationError(
            f"{rule}: fill in the paid date.",
            code=rule,
        )
    if missing:
        raise ValidationError(missing)
    with transaction.atomic(), acting_for(user):
        order.payment_method = payment_method
        order.paid_date = paid_date
        order.order_status_id = OS.PAID
        order.save()
    return order


def close_order(order: Order, *, confirmed: bool, user: Any = None) -> Order:
    """Close a Paid order after the user confirms (R-orders-018); nothing on it can be
    edited afterwards (R-orders-014)."""
    rule = "R-orders-018"
    _require_saved(order, rule)
    if order.order_status_id != OS.PAID:
        refuse(rule, "only a Paid order can be closed.")
    if not confirmed:
        refuse(rule, "confirm closing the order; nothing was changed.")
    with transaction.atomic(), acting_for(user):
        order.order_status_id = OS.CLOSED
        order.save()
    return order


def delete_order(order: Order, *, user: Any = None) -> None:
    """Delete a New or Invoiced order with its lines, re-running stock allocation for
    each line's product (R-orders-011, R-orders-012). Deleting an unsaved order does
    nothing. The screen asks for confirmation first."""
    if order.pk is None:
        return
    if order.order_status_id not in (OS.NEW, OS.INVOICED):
        refuse(
            "R-orders-012",
            "only a New or Invoiced order can be deleted; this one is "
            f"{order.order_status.order_status_name}.",
        )
    with transaction.atomic(), acting_for(user):
        for line in order.lines.order_by("pk"):
            product_id = line.product_id
            line.delete()
            allocate_inventory(product_id)
        order.delete()


def next_action(order: Order) -> str | None:
    """The workflow action the order screen highlights (R-orders-030)."""
    if order.pk is None:
        return None
    return {
        OS.NEW: "invoice",
        OS.INVOICED: "ship",
        OS.SHIPPED: "pay",
        OS.PAID: "close",
    }.get(order.order_status_id)


def can_reprint_invoice(order: Order) -> bool:
    """The invoice can be opened again once the order is past New (R-orders-019)."""
    return order.pk is not None and order.order_status_id != OS.NEW


# ---------------------------------------------------------------- amounts


def _money(value: float | Decimal | None) -> Decimal | None:
    return None if value is None else vbacompat.ccur(value)


@dataclass(frozen=True)
class OrderAmounts:
    """The order screen's and the invoice's amounts (R-orders-020, R-orders-022)."""

    subtotal: Decimal | None
    tax: Decimal | None
    shipping: Decimal | None
    total: Decimal | None


def order_amounts(order: Order) -> OrderAmounts:
    """Subtotal = the order total of its lines; tax = tax rate x subtotal when the
    order is Taxable, else 0 (shipping is never taxed); total = subtotal + tax +
    shipping fee, a blank fee counting as 0 (R-orders-020, R-orders-022). An order
    without lines has no subtotal, tax or total."""
    subtotal = order_total(order)
    shipping = order.shipping_fee
    if subtotal is None:
        return OrderAmounts(None, None, _money(shipping), None)
    taxable = order.tax_status_id == TaxStatusCode.TAXABLE
    tax = (order.tax_rate or 0.0) * subtotal if taxable else 0.0
    total = subtotal + tax + float(shipping or 0)
    return OrderAmounts(_money(subtotal), _money(tax), _money(shipping), _money(total))


def line_price(line: OrderDetail) -> Decimal | None:
    """Quantity x (1 - discount) x unit price of one line (R-orders-022)."""
    return _money(line_amount(line))


# ---------------------------------------------------------------- invoice


@dataclass(frozen=True)
class InvoiceLine:
    product_code: str
    product_name: str
    quantity: int
    unit_price: Decimal
    discount: float | None
    extended_price: Decimal | None


@dataclass(frozen=True)
class Invoice:
    """The printable invoice of one order (R-orders-020)."""

    number: int
    printed_on: dt.datetime
    customer_name: str
    address: str
    city_line: str
    sales_person: str
    own_address: list[str]
    lines: list[InvoiceLine]
    amounts: OrderAmounts


def own_company_address() -> list[str]:
    """The trading company's name, street and 'city state, zip' lines
    (R-orders-020)."""
    company = queries.own_company()
    if company is None:
        return []
    return [
        company.company_name,
        company.address,
        f"{company.city} {company.state_id}, {company.zip}",
    ]


def invoice_for(order: Order, today: dt.datetime | None = None) -> Invoice | None:
    """The invoice of an order, from the area's invoice query (R-orders-020): the
    invoice number is the order number and the date is the day it is printed. None
    when the order has nothing to print, no lines (R-orders-021). Reading it never
    changes the order (R-orders-019)."""
    rows = list(queries.invoice_lines().filter(order_id=order.pk))
    if not rows:
        return None
    first = rows[0]
    lines = [
        InvoiceLine(
            product_code=row.product_code,
            product_name=row.product_name,
            quantity=row.quantity,
            unit_price=row.unit_price,
            discount=row.discount,
            extended_price=line_price(row),
        )
        for row in rows
    ]
    return Invoice(
        number=order.pk,
        printed_on=today or vbacompat.date(),
        customer_name=first.company_name,
        address=first.address,
        city_line=f"{first.city} {first.state_abbrev}, {first.zip}",
        sales_person=first.sales_person,
        own_address=own_company_address(),
        lines=lines,
        amounts=order_amounts(order),
    )


# ---------------------------------------------------------------- order list

ORDER_FILTERS = (
    ("open", "Open orders"),
    ("recent", "Recent orders"),
    ("mine", "My orders"),
    ("all", "All orders"),
)
DEFAULT_ORDER_FILTER = "open"
RECENT_DAYS = 30


def filter_order_list(
    orders: QuerySet,
    choice: str | None,
    *,
    user: Any = None,
    today: dt.datetime | None = None,
) -> QuerySet:
    """The order list's filters (R-orders-025): Open orders (every status except
    Closed, the default), Recent orders (order date within the last 30 days), My
    orders (the signed-in employee's) and All orders."""
    choice = choice or DEFAULT_ORDER_FILTER
    if choice == "open":
        return orders.exclude(order_status_id=OS.CLOSED)
    if choice == "recent":
        since = (today or vbacompat.date()) - dt.timedelta(days=RECENT_DAYS)
        return orders.filter(order_date__gte=since)
    if choice == "mine":
        employee = signed_in_employee(user)
        if employee is None:
            return orders.none()
        return orders.filter(employee=employee)
    return orders


def order_list_footer(orders: QuerySet) -> tuple[int, Decimal | None]:
    """The number of orders shown and the sum of their totals (R-orders-026)."""
    total = orders.order_by().aggregate(total=Sum("order_total"))["total"]
    return orders.count(), _money(total)


# ---------------------------------------------------------------- companies

COMPANY_FILTERS = (
    ("all", "Companies", None),
    ("customers", "Customers", CompanyTypeCode.CUSTOMER),
    ("shippers", "Shippers", CompanyTypeCode.SHIPPER),
    ("vendors", "Vendors", CompanyTypeCode.VENDOR),
)


def company_filter(choice: str | None) -> tuple[str, str, int | None]:
    """(key, heading, company type) of the company list's filter (R-orders-037):
    Customers, Shippers, Vendors or all companies."""
    for key, heading, company_type in COMPANY_FILTERS:
        if key == choice:
            return key, heading, company_type
    return COMPANY_FILTERS[0]


def filter_company_list(companies: QuerySet, choice: str | None) -> QuerySet:
    """The company list filtered to one company type, or all (R-orders-037)."""
    _key, _heading, company_type = company_filter(choice)
    if company_type is None:
        return companies
    return companies.filter(company_type_id=company_type)


#: The related list of the company screen, by company type (R-orders-035).
COMPANY_RELATED_LIST = {
    CompanyTypeCode.CUSTOMER: ("customer_orders", "Orders"),
    CompanyTypeCode.SHIPPER: ("shipper_orders", "Orders Shipped"),
    CompanyTypeCode.VENDOR: ("purchase_orders", "Purchase Orders"),
}


def company_related_list(company_type: int | None) -> tuple[str, str] | None:
    """Which related list the company screen shows for a company type, and its
    heading; none for the trading company itself (R-orders-035)."""
    return COMPANY_RELATED_LIST.get(company_type)


@dataclass(frozen=True)
class CompanyLinks:
    """What refers to a company (R-orders-033, R-orders-034)."""

    contacts: int
    customer_orders: int
    shipper_orders: int
    purchase_orders: int
    vendor_products: int

    @property
    def active(self) -> bool:
        """It has orders as customer or shipper, or purchase orders."""
        return self.customer_orders + self.shipper_orders + self.purchase_orders > 0


def company_links(company: Company) -> CompanyLinks:
    return CompanyLinks(
        contacts=Contact.objects.filter(company=company).count(),
        customer_orders=Order.objects.filter(customer=company).count(),
        shipper_orders=Order.objects.filter(shipper=company).count(),
        purchase_orders=PurchaseOrder.objects.filter(vendor=company).count(),
        vendor_products=ProductVendor.objects.filter(vendor=company).count(),
    )


def delete_company(company: Company, *, confirmed: bool, user: Any = None) -> None:
    """Delete a company with its contacts and vendor-product links (R-orders-033).
    Refused while it has orders as customer, orders as shipper or purchase orders
    (the message gives each count); otherwise the user confirms first, told how many
    contacts and vendor-product links go too."""
    rule = "R-orders-033"
    links = company_links(company)
    if links.active:
        refuse(
            rule,
            "the company cannot be deleted: it has "
            f"{links.customer_orders} orders as customer, {links.shipper_orders} "
            f"orders as shipper and {links.purchase_orders} purchase orders.",
        )
    if not confirmed:
        refuse(
            rule,
            f"confirm the delete: {links.contacts} contacts and "
            f"{links.vendor_products} vendor-product links are deleted with it.",
        )
    with transaction.atomic(), acting_for(user):
        Contact.objects.filter(company=company).delete()
        ProductVendor.objects.filter(vendor=company).delete()
        company.delete()


def _check_type_change(company: Company) -> None:
    links = company_links(company)
    if links.active or links.vendor_products:
        refuse(
            "R-orders-034",
            "the company type cannot be changed: the company has "
            f"{links.customer_orders} orders as customer, {links.shipper_orders} "
            f"orders as shipper, {links.purchase_orders} purchase orders and "
            f"{links.vendor_products} vendor-product links.",
            field="company_type",
        )


def change_company_type(
    company: Company,
    company_type: Any,
    *,
    user: Any = None,
) -> Company:
    """Change a company's type; refused while it has orders, shipments, purchase
    orders or vendor-product links (R-orders-034)."""
    if _plain(company_type) != company.company_type_id:
        _check_type_change(company)
    with transaction.atomic(), acting_for(user):
        company.company_type_id = _plain(company_type)
        company.save()
    return company


def save_company(
    company: Company,
    data: Mapping[str, Any],
    *,
    confirmed: bool,
    user: Any = None,
) -> Company:
    """Create or edit a company. The user confirms the save first; without the
    confirmation nothing is saved (R-orders-036). A type change follows
    R-orders-034; a new company is Tax Exempt unless the user picks another
    (R-orders-048); phones follow R-orders-045, required fields R-orders-005 and the
    name is unique per company type (R-orders-046)."""
    if not confirmed:
        refuse("R-orders-036", "confirm saving the company; nothing was saved.")
    creating = company.pk is None
    if not creating and "company_type" in _changed(company, data):
        _check_type_change(company)
    _assign(company, _clean_phones(data))
    if creating and company.standard_tax_status_id is None:
        company.standard_tax_status_id = TaxStatusCode.TAX_EXEMPT
    check_required(company)
    check_unique(company)
    with transaction.atomic(), acting_for(user):
        company.save()
    return company


def save_contact(
    contact: Contact,
    data: Mapping[str, Any],
    *,
    user: Any = None,
) -> Contact:
    """Create or edit a contact of a company: required fields (R-orders-005), phones
    (R-orders-045), first and last name once per company (R-orders-046)."""
    _assign(contact, _clean_phones(data))
    check_required(contact)
    check_unique(contact)
    with transaction.atomic(), acting_for(user):
        contact.save()
    return contact


def delete_contact(contact: Contact, *, user: Any = None) -> None:
    """Delete one contact of a company."""
    with transaction.atomic(), acting_for(user):
        contact.delete()


# ---------------------------------------------------------------- employees


def supervisor_choices(employee: Employee | None) -> QuerySet:
    """The supervisor list: every employee except the one being edited
    (R-orders-041)."""
    choices = queries.employee_choices()
    if employee is not None and employee.pk is not None:
        choices = choices.exclude(pk=employee.pk)
    return choices


def save_employee(
    employee: Employee,
    data: Mapping[str, Any],
    *,
    user: Any = None,
) -> Employee:
    """Create or edit an employee. An employee is not their own supervisor
    (R-orders-041); the title comes from the titles list (R-orders-044); phones follow
    R-orders-045; required fields R-orders-005; first and last name once and an
    operating-system login on one employee at most (R-orders-046)."""
    data = _clean_phones(data)
    supervisor = data.get("supervisor")
    if (
        supervisor is not None
        and employee.pk is not None
        and _plain(supervisor) == employee.pk
    ):
        refuse(
            "R-orders-041",
            "an employee cannot be their own supervisor.",
            field="supervisor",
        )
    title = data.get("title")
    if isinstance(title, str):
        if not Title.objects.filter(pk=title).exists():
            refuse(
                "R-orders-044",
                "choose a title from the titles list.",
                field="title",
            )
        data = {**data, "title": Title.objects.get(pk=title)}
    if "windows_user_name" in data and not data["windows_user_name"]:
        data = {**data, "windows_user_name": None}
    _assign(employee, data)
    check_required(employee)
    check_unique(employee)
    with transaction.atomic(), acting_for(user):
        employee.save()
    return employee


def employee_delete_reasons(employee: Employee) -> list[str]:
    """Every reason an employee cannot be deleted (R-orders-040)."""
    name = queries.employees().filter(pk=employee.pk).values_list(
        "full_name_fnln",
        flat=True,
    ).first() or str(employee)
    counts = (
        (Order.objects.filter(employee=employee).count(), "has {n} orders"),
        (
            PurchaseOrder.objects.filter(submitted_by=employee).count(),
            "has submitted {n} purchase orders",
        ),
        (
            Employee.objects.filter(supervisor=employee).count(),
            "supervises {n} employees",
        ),
        (
            EmployeePrivilege.objects.filter(employee=employee).count(),
            "holds {n} privileges",
        ),
    )
    return [f"{name} {text.format(n=n)}." for n, text in counts if n]


def delete_employee(employee: Employee, *, confirmed: bool, user: Any = None) -> None:
    """Delete an employee. Refused while they have orders, submitted purchase orders,
    supervise employees or hold privileges, naming every reason; otherwise the user
    confirms the delete by the employee's name (R-orders-040)."""
    rule = "R-orders-040"
    reasons = employee_delete_reasons(employee)
    if reasons:
        refuse(rule, "the employee cannot be deleted: " + " ".join(reasons))
    if not confirmed:
        refuse(rule, f"confirm deleting {employee}; nothing was deleted.")
    with transaction.atomic(), acting_for(user):
        employee.delete()


def add_title(text: str | None, *, user: Any = None) -> Title:
    """Add a courtesy title to the titles list (R-orders-044); each title once
    (R-orders-046)."""
    title = Title(title=(text or "").strip())
    check_required(title)
    check_unique(title)
    with transaction.atomic(), acting_for(user):
        title.save()
    return title


def grant_privilege(
    employee: Employee,
    privilege: Privilege,
    *,
    user: Any = None,
) -> EmployeePrivilege:
    """Grant a privilege to an employee, once (the privilege screen that opens after
    a new employee is saved, R-orders-042)."""
    with transaction.atomic(), acting_for(user):
        grant, _created = EmployeePrivilege.objects.get_or_create(
            employee=employee,
            privilege=privilege,
        )
    return grant


def revoke_privilege(grant: EmployeePrivilege, *, user: Any = None) -> None:
    """Withdraw one privilege grant."""
    with transaction.atomic(), acting_for(user):
        grant.delete()


# ---------------------------------------------------------------- first run

TRUE_TEXT = {"true", "yes", "on"}


def first_run_done() -> bool:
    """Whether the first-run flag in the system settings is set (R-orders-049). A
    missing or blank flag reads as not set, as the original's error path did."""
    text = (system_setting(SystemSettingCode.FIRST_RUN) or "").strip()
    try:
        return Decimal(text) != 0
    except ArithmeticError:
        return text.lower() in TRUE_TEXT


def _set_first_run_flag() -> None:
    setting = SystemSetting.objects.filter(pk=SystemSettingCode.FIRST_RUN).first()
    if setting is None:
        setting = SystemSetting(
            setting_id=SystemSettingCode.FIRST_RUN,
            setting_name="FirstTimeRun",
        )
    setting.setting_value = "-1"
    setting.save()


def _legacy_models() -> Iterable[type[models.Model]]:
    for model in apps.get_app_config("legacy").get_models():
        if not issubclass(model, HistoricalChanges):
            yield model


def shift_dates(days: int) -> int:
    """Move every date of every kept table `days` days forward; rows that change are
    stamped with the name System (R-orders-049, R-orders-031). Returns the number of
    rows changed."""
    changed = 0
    now = audit.stamp_time()
    for model in _legacy_models():
        fields = [
            field.attname
            for field in model._meta.concrete_fields  # noqa: SLF001
            if isinstance(field, models.DateTimeField) and field.name != "modified_on"
        ]
        if not fields:
            continue
        stamped = issubclass(model, audit.AuditStampedModel)
        rows = []
        for row in model._base_manager.only(*fields).iterator():  # noqa: SLF001
            values = [getattr(row, name) for name in fields]
            if all(value is None for value in values):
                continue
            for name, value in zip(fields, values, strict=True):
                if value is not None:
                    setattr(row, name, value + dt.timedelta(days=days))
            if stamped:
                row.modified_by, row.modified_on = audit.SYSTEM, now
            rows.append(row)
        update = [*fields, "modified_by", "modified_on"] if stamped else fields
        model._base_manager.bulk_update(rows, update, batch_size=200)  # noqa: SLF001
        changed += len(rows)
    return changed


@dataclass(frozen=True)
class FirstRunResult:
    ran: bool
    days: int
    rows: int


def first_run(today: dt.datetime | None = None) -> FirstRunResult:
    """The start-up job (R-orders-049): on the very first run only, guarded by the
    first-run flag, move every date forward by the days between the latest order
    date and today (never backwards; without orders nothing moves), then set the
    flag so it never runs again. Rows it changes are stamped System."""
    if first_run_done():
        return FirstRunResult(ran=False, days=0, rows=0)
    today = vbacompat.date() if today is None else today
    latest = Order.objects.aggregate(latest=Max("order_date"))["latest"]
    days = (today.date() - latest.date()).days if latest is not None else 0
    rows = 0
    with transaction.atomic(), audit.acting_as(None):
        if days > 0:
            rows = shift_dates(days)
        _set_first_run_flag()
    return FirstRunResult(ran=True, days=max(days, 0), rows=rows)
