"""Querysets of the Orders, Invoicing and Shipping area.

The saved queries (saved_queries.py), the screens (views.py) and the invoice
(reports/invoice.py) all read through these functions, so a list on screen and its
equivalence unit share one definition. Shared figures come from the domain app: the
order total and line amounts (domain.sales) and the employee's full name
(domain.people). Everything here is portable ORM: PostgreSQL and SQL Server.

Access's `&` joins text and treats a blank part as empty text; `amp()` does the same.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from django.db.models import CharField
from django.db.models import F
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.db.models.functions import Concat

from northwind.domain.people import full_name_expression
from northwind.domain.sales import order_total_expression
from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.models import Company
from northwind.legacy.models import Employee
from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail

if TYPE_CHECKING:
    from django.db.models import Expression
    from django.db.models import QuerySet

CUSTOMER = CompanyTypeCode.CUSTOMER
SHIPPER = CompanyTypeCode.SHIPPER
VENDOR = CompanyTypeCode.VENDOR
OWN_COMPANY = CompanyTypeCode.OWN_COMPANY

AUDIT_FIELDS = ("added_by", "added_on", "modified_by", "modified_on")

#: The columns of the Orders table, in the original's column order.
ORDER_FIELDS = (
    "order_id",
    "employee_id",
    "customer_id",
    "order_date",
    "invoice_date",
    "shipped_date",
    "shipper_id",
    "shipping_fee",
    "tax_rate",
    "tax_status_id",
    "payment_method",
    "paid_date",
    "notes",
    "order_status_id",
    *AUDIT_FIELDS,
)
#: The columns of the Companies table.
COMPANY_FIELDS = (
    "company_id",
    "company_name",
    "company_type_id",
    "business_phone",
    "address",
    "city",
    "state_id",
    "zip",
    "website",
    "notes",
    "standard_tax_status_id",
    *AUDIT_FIELDS,
)
#: The columns of the Contacts table.
CONTACT_FIELDS = (
    "contact_id",
    "company_id",
    "last_name",
    "first_name",
    "email_address",
    "job_title",
    "primary_phone",
    "secondary_phone",
    "notes",
    *AUDIT_FIELDS,
)
#: The columns of the Employees table before the attachments column.
EMPLOYEE_FIELDS_BEFORE_ATTACHMENTS = (
    "employee_id",
    "first_name",
    "last_name",
    "email_address",
    "job_title",
    "primary_phone",
    "secondary_phone",
    "title_id",
    "notes",
)
#: The columns of the Employees table after the attachments column.
EMPLOYEE_FIELDS_AFTER_ATTACHMENTS = (
    "supervisor_id",
    "windows_user_name",
    *AUDIT_FIELDS,
)
#: The columns of the OrderDetails table.
LINE_FIELDS = (
    "order_detail_id",
    "order_id",
    "product_id",
    "quantity",
    "unit_price",
    "discount",
    "order_detail_status_id",
    *AUDIT_FIELDS,
)
#: The columns of the EmployeePrivileges table.
EMPLOYEE_PRIVILEGE_FIELDS = (
    "employee_privilege_id",
    "employee_id",
    "privilege_id",
    *AUDIT_FIELDS,
)


def amp(*parts: Expression | str) -> Concat:
    """Access's `&`: join the parts as text, a blank part counting as empty text. A
    plain string is literal text; any other part is an expression."""
    expressions = [
        Value(part) if isinstance(part, str) else Coalesce(part, Value(""))
        for part in parts
    ]
    return Concat(*expressions, output_field=CharField())


def business_address_expression(prefix: str = "") -> Concat:
    """Street, two spaces, city, ", ", state, two spaces, zip (R-orders-039)."""
    return amp(
        F(f"{prefix}address"),
        "  ",
        F(f"{prefix}city"),
        ", ",
        F(f"{prefix}state_id"),
        "  ",
        F(f"{prefix}zip"),
    )


def full_name_lnfn_expression(prefix: str = "") -> Concat:
    """Last name, ", ", first name: the employee list's name (R-orders-043)."""
    return amp(F(f"{prefix}last_name"), ", ", F(f"{prefix}first_name"))


def date_only(value: dt.datetime | None) -> dt.datetime | None:
    """The date part of a date and time, at midnight (Access DateValue)."""
    if value is None:
        return None
    return dt.datetime.combine(value.date(), dt.time.min)


# ---------------------------------------------------------------- companies


def companies() -> QuerySet:
    """Every company with its business address, by name (R-orders-039)."""
    return Company.objects.annotate(
        business_address=business_address_expression(),
    ).order_by("company_name", "pk")


def company_list() -> QuerySet:
    """Companies with type and standard tax status names (R-orders-039)."""
    return companies().annotate(
        company_type_name=F("company_type__company_type"),
        tax_status_name=F("standard_tax_status__tax_status"),
    )


def customers() -> QuerySet:
    """Companies whose type is Customer, by name (R-orders-003)."""
    return Company.objects.filter(company_type_id=CUSTOMER).order_by(
        "company_name",
        "pk",
    )


def shippers() -> QuerySet:
    """Companies whose type is Shipper, by name (R-orders-003)."""
    return Company.objects.filter(company_type_id=SHIPPER).order_by(
        "company_name",
        "pk",
    )


def own_company() -> Company | None:
    """The trading company itself (company type Own company, R-orders-020)."""
    return Company.objects.filter(company_type_id=OWN_COMPANY).order_by("pk").first()


# ---------------------------------------------------------------- employees


def employees() -> QuerySet:
    """Employees with both forms of the full name, sorted last name first
    (R-orders-043)."""
    return Employee.objects.annotate(
        full_name_fnln=full_name_expression(),
        full_name_lnfn=full_name_lnfn_expression(),
    ).order_by("full_name_lnfn", "pk")


def employee_choices() -> QuerySet:
    """Employees for a choice list, sorted by first then last name (R-orders-043)."""
    return Employee.objects.annotate(full_name_fnln=full_name_expression()).order_by(
        "full_name_fnln",
        "pk",
    )


# ---------------------------------------------------------------- orders


def lowest_line_status_name() -> Subquery:
    """The name of the least advanced status among an order's lines: the status with
    the lowest sort order; null without lines (R-orders-024)."""
    lines = (
        OrderDetail.objects.filter(order_id=OuterRef("pk"))
        .order_by("order_detail_status__sort_order")
        .values("order_detail_status__order_detail_status_name")[:1]
    )
    return Subquery(lines, output_field=CharField())


def orders_with_names() -> QuerySet:
    """Orders with salesperson name, order total and status name."""
    return Order.objects.annotate(
        full_name_fnln=full_name_expression("employee__"),
        order_total=order_total_expression(),
        order_status_name=F("order_status__order_status_name"),
    )


def order_list() -> QuerySet:
    """The order list: orders of Customer-type companies, newest order number first,
    with customer name, salesperson, total, status and the lowest line status
    (R-orders-024)."""
    return (
        orders_with_names()
        .filter(customer__company_type_id=CUSTOMER)
        .annotate(
            company_name=F("customer__company_name"),
            order_detail_status_name=lowest_line_status_name(),
        )
        .order_by("-order_id")
    )


def most_recent_orders(limit: int = 20) -> QuerySet:
    """The `limit` newest orders of the order list (R-orders-027)."""
    return order_list()[:limit]


def employee_recent_orders(employee: Employee | int, limit: int = 20) -> list[Order]:
    """The employee's orders among the `limit` newest orders of all employees
    (R-orders-027): an employee without an order among them sees none."""
    employee_id = employee.pk if isinstance(employee, Employee) else int(employee)
    return [o for o in most_recent_orders(limit) if o.employee_id == employee_id]


def customer_orders() -> QuerySet:
    """Orders with salesperson, shipper name (only a Shipper-type company), total and
    status, newest first: the customer's orders on the company screen
    (R-orders-028)."""
    shipper_name = Subquery(
        Company.objects.filter(
            pk=OuterRef("shipper_id"),
            company_type_id=SHIPPER,
        ).values("company_name")[:1],
        output_field=CharField(),
    )
    return orders_with_names().annotate(shipper_name=shipper_name).order_by("-order_id")


def shipper_orders() -> QuerySet:
    """Orders of Customer-type customers with salesperson, total, status and customer
    name: the shipper's orders on the company screen (R-orders-028)."""
    return (
        orders_with_names()
        .filter(customer__company_type_id=CUSTOMER)
        .annotate(customer_name=F("customer__company_name"))
        .order_by("-order_id")
    )


def order_lines() -> QuerySet:
    """Order lines with product name, product category and category name, in line
    order (the order lines grid)."""
    return OrderDetail.objects.annotate(
        product_name=F("product__product_name"),
        product_category_id=F("product__product_category_id"),
        product_category_name=F("product__product_category__product_category_name"),
    ).order_by("order_detail_id")


def invoice_lines() -> QuerySet:
    """One row per order line of orders of Customer-type companies, with the
    customer's name and address, the salesperson's full name and the product code and
    name (R-orders-020)."""
    return (
        OrderDetail.objects.filter(order__customer__company_type_id=CUSTOMER)
        .annotate(
            company_name=F("order__customer__company_name"),
            address=F("order__customer__address"),
            city=F("order__customer__city"),
            state_abbrev=F("order__customer__state_id"),
            zip=F("order__customer__zip"),
            sales_person=full_name_expression("order__employee__"),
            product_code=F("product__product_code"),
            product_name=F("product__product_name"),
        )
        .order_by("order_id", "order_detail_id")
    )
