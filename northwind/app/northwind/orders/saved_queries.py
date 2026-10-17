"""Equivalence units of the Orders, Invoicing and Shipping area
(docs/contracts.md#harness).

One function per unit of goldens/manifest.json whose area is orders, registered under
the unit id. Each returns one tuple per row with the manifest's columns in order,
computed from the database through queries.py, the ORM and the domain functions; none
reads golden files or branches on the dataset, a seed or row ids. The order lists
come out in the original's sort order; the harness normalises row order anyway.

The area has no document units (documents are the workbook engagements' units); the
invoice is rendered by reports/invoice.py.
"""

from __future__ import annotations

from django.db.models import F
from django.db.models import Min

from northwind.core.saved_queries import saved_query
from northwind.domain.sales import with_order_total
from northwind.legacy.models import CompanyType
from northwind.legacy.models import Contact
from northwind.legacy.models import EmployeePrivilege
from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import OrderDetailStatus
from northwind.legacy.models import OrderStatus
from northwind.legacy.models import Privilege
from northwind.legacy.models import State
from northwind.legacy.models import TaxStatus
from northwind.legacy.models import Title

from . import queries
from .queries import COMPANY_FIELDS
from .queries import CONTACT_FIELDS
from .queries import EMPLOYEE_FIELDS_AFTER_ATTACHMENTS
from .queries import EMPLOYEE_FIELDS_BEFORE_ATTACHMENTS
from .queries import EMPLOYEE_PRIVILEGE_FIELDS
from .queries import LINE_FIELDS
from .queries import ORDER_FIELDS

Params = dict[str, str]

#: The employee screen's current employee, the supervisor list's parameter.
SUPERVISOR_PARAM = "Forms!frmEmployeeList!EmployeeID"

ORDER_LIST_FIELDS = (
    *ORDER_FIELDS,
    "full_name_fnln",
    "company_name",
    "order_total",
    "order_status_name",
    "order_detail_status_name",
)


def _rows(queryset, fields) -> list[tuple]:
    return list(queryset.values_list(*fields))


def _with_order_date_only(rows: list[tuple]) -> list[tuple]:
    """Append the order date without its time (the order date is column 4)."""
    return [(*row, queries.date_only(row[3])) for row in rows]


# ---------------------------------------------------------------- companies


@saved_query("qryCompanies")
def qry_companies(params: Params) -> list[tuple]:
    """Every company with its one-line business address (R-orders-039)."""
    return _rows(queries.companies(), (*COMPANY_FIELDS, "business_address"))


@saved_query("qryCompanyList")
def qry_company_list(params: Params) -> list[tuple]:
    """Companies with type and tax status names and the address (R-orders-039)."""
    fields = (
        "company_id",
        "company_name",
        "company_type_name",
        "business_phone",
        "address",
        "city",
        "state_id",
        "zip",
        "website",
        "notes",
        "tax_status_name",
        "added_by",
        "added_on",
        "modified_by",
        "modified_on",
        "business_address",
        "company_type_id",
        "standard_tax_status_id",
    )
    return _rows(queries.company_list(), fields)


@saved_query("qryContacts")
def qry_contacts(params: Params) -> list[tuple]:
    """Contacts by last then first name (R-orders-039)."""
    contacts = Contact.objects.order_by("last_name", "first_name", "pk")
    return _rows(contacts, CONTACT_FIELDS)


@saved_query("qryCustomers")
def qry_customers(params: Params) -> list[tuple]:
    """Companies whose type is Customer (R-orders-003)."""
    return _rows(queries.customers(), COMPANY_FIELDS)


@saved_query("qryShippers")
def qry_shippers(params: Params) -> list[tuple]:
    """Companies whose type is Shipper (R-orders-003)."""
    return _rows(queries.shippers(), COMPANY_FIELDS)


@saved_query("qrycboCustomers")
def qry_cbo_customers(params: Params) -> list[tuple]:
    """The customer choice list, by name (R-orders-003)."""
    return _rows(queries.customers(), ("company_id", "company_name"))


@saved_query("qrycboShippers")
def qry_cbo_shippers(params: Params) -> list[tuple]:
    """The shipper choice list, by name (R-orders-003)."""
    return _rows(queries.shippers(), ("company_id", "company_name"))


@saved_query("qrycboCompanyType")
def qry_cbo_company_type(params: Params) -> list[tuple]:
    """Company types by name (R-orders-047)."""
    types = CompanyType.objects.order_by("company_type", "pk")
    return _rows(types, ("company_type_id", "company_type"))


@saved_query("qrycboStates")
def qry_cbo_states(params: Params) -> list[tuple]:
    """States by state name (R-orders-047)."""
    return _rows(State.objects.order_by("state_name"), ("state_abbrev", "state_name"))


@saved_query("qrycboTaxStatus")
def qry_cbo_tax_status(params: Params) -> list[tuple]:
    """Tax statuses by code (R-orders-047)."""
    statuses = TaxStatus.objects.order_by("tax_status_id")
    return _rows(statuses, ("tax_status_id", "tax_status"))


# ---------------------------------------------------------------- employees


@saved_query("qryEmployees")
def qry_employees(params: Params) -> list[tuple]:
    """Employees with both full names, last name first in sort order (R-orders-043).
    The attachments column is not carried over (legacy/models.py), so it is blank."""
    fields = (
        *EMPLOYEE_FIELDS_BEFORE_ATTACHMENTS,
        *EMPLOYEE_FIELDS_AFTER_ATTACHMENTS,
        "full_name_fnln",
        "full_name_lnfn",
    )
    split = len(EMPLOYEE_FIELDS_BEFORE_ATTACHMENTS)
    return [
        (*row[:split], None, *row[split:])
        for row in queries.employees().values_list(*fields)
    ]


@saved_query("qrycboEmployees")
def qry_cbo_employees(params: Params) -> list[tuple]:
    """The employee choice list, first name first (R-orders-043)."""
    return _rows(queries.employee_choices(), ("employee_id", "full_name_fnln"))


@saved_query("qryEmployeeLogin")
def qry_employee_login(params: Params) -> list[tuple]:
    """Employees with their full name (the foundation's user admin replaces the
    screen behind it)."""
    fields = (
        "employee_id",
        "first_name",
        "last_name",
        "email_address",
        "job_title",
        "windows_user_name",
        "full_name_fnln",
    )
    return _rows(queries.employees(), fields)


@saved_query("qryEmployeeSupervisor")
def qry_employee_supervisor(params: Params) -> list[tuple]:
    """Every employee except the one being edited, with their full name
    (R-orders-041). Without an employee the list is empty."""
    text = (params.get(SUPERVISOR_PARAM) or "").strip()
    if not text:
        return []
    supervisors = queries.employees().exclude(pk=int(text))
    return _rows(supervisors, ("employee_id", "full_name_fnln"))


@saved_query("qryEmployeePrivileges")
def qry_employee_privileges(params: Params) -> list[tuple]:
    """Privilege grants, by the employee's first then last name."""
    grants = EmployeePrivilege.objects.order_by(
        "employee__first_name",
        "employee__last_name",
        "pk",
    )
    return _rows(grants, EMPLOYEE_PRIVILEGE_FIELDS)


@saved_query("qryPrivileges")
def qry_privileges(params: Params) -> list[tuple]:
    """Privilege names, by name."""
    privileges = Privilege.objects.order_by("privilege_name")
    return _rows(privileges, ("privilege_id", "privilege_name"))


@saved_query("qryTitle")
def qry_title(params: Params) -> list[tuple]:
    """The courtesy titles list (R-orders-044)."""
    return _rows(Title.objects.order_by("title"), ("title",))


# ---------------------------------------------------------------- orders


@saved_query("qryOrderTotal")
def qry_order_total(params: Params) -> list[tuple]:
    """Every order with its total; blank without lines (R-orders-023)."""
    orders = with_order_total(Order.objects.order_by("pk"))
    return _rows(orders, ("order_id", "order_total"))


@saved_query("qryOrder")
def qry_order(params: Params) -> list[tuple]:
    """Orders with their status name (the order screen's record source)."""
    orders = Order.objects.annotate(
        order_status_name=F("order_status__order_status_name"),
    ).order_by("pk")
    return _rows(orders, (*ORDER_FIELDS, "order_status_name"))


@saved_query("qryOrderLineItems")
def qry_order_line_items(params: Params) -> list[tuple]:
    """Order lines with product and category names, in line order."""
    fields = (
        *LINE_FIELDS,
        "product_name",
        "product_category_id",
        "product_category_name",
    )
    return _rows(queries.order_lines(), fields)


@saved_query("qryOrderList_DetailStatus_Lowest")
def qry_order_list_detail_status_lowest(params: Params) -> list[tuple]:
    """Per order with lines, the lowest sort order among its lines' statuses
    (R-orders-024)."""
    lowest = (
        OrderDetail.objects.order_by()
        .values("order_id")
        .annotate(lowest=Min("order_detail_status__sort_order"))
        .order_by("order_id")
    )
    return [(row["order_id"], row["lowest"]) for row in lowest]


@saved_query("qryOrderList_DetailStatus")
def qry_order_list_detail_status(params: Params) -> list[tuple]:
    """Per order with lines, the name of its least advanced line status
    (R-orders-024)."""
    names = dict(
        OrderDetailStatus.objects.values_list("sort_order", "order_detail_status_name"),
    )
    return [
        (order_id, names[lowest])
        for order_id, lowest in qry_order_list_detail_status_lowest(params)
        if lowest in names
    ]


@saved_query("qryOrderList")
def qry_order_list(params: Params) -> list[tuple]:
    """The order list (R-orders-024)."""
    return _with_order_date_only(_rows(queries.order_list(), ORDER_LIST_FIELDS))


@saved_query("qryOrders_MostRecent")
def qry_orders_most_recent(params: Params) -> list[tuple]:
    """The 20 newest orders of the order list (R-orders-027)."""
    return _with_order_date_only(
        _rows(queries.most_recent_orders(), ORDER_LIST_FIELDS),
    )


@saved_query("qryCustomerOrderList")
def qry_customer_order_list(params: Params) -> list[tuple]:
    """Orders with salesperson, shipper, total and status for the company screen of
    a customer (R-orders-028); myCompanyID is the customer."""
    fields = (
        "order_id",
        "employee_id",
        "customer_id",
        "order_date",
        "shipped_date",
        "shipper_id",
        "shipping_fee",
        "tax_rate",
        "tax_status_id",
        "payment_method",
        "paid_date",
        "notes",
        "order_status_id",
        "added_by",
        "added_on",
        "modified_by",
        "modified_on",
        "full_name_fnln",
        "shipper_name",
        "order_total",
        "order_status_name",
    )
    return _rows(queries.customer_orders(), fields)


@saved_query("qryShipperOrderList")
def qry_shipper_order_list(params: Params) -> list[tuple]:
    """Orders with salesperson, total, status and customer for the company screen of
    a shipper (R-orders-028); myCompanyID is the shipper."""
    fields = (
        "order_id",
        "full_name_fnln",
        "order_date",
        "order_total",
        "order_status_name",
        "customer_id",
        "shipper_id",
        "customer_name",
    )
    return _rows(queries.shipper_orders().order_by("order_id"), fields)


@saved_query("qryInvoice")
def qry_invoice(params: Params) -> list[tuple]:
    """One row per invoice line: customer name and address, the order's columns,
    the salesperson and the line's product, quantity, price and discount
    (R-orders-020)."""
    order_columns = tuple(f"order__{name}" for name in ORDER_FIELDS)
    fields = (
        "company_name",
        "address",
        "city",
        "state_abbrev",
        "zip",
        *order_columns,
        "sales_person",
        "product_id",
        "quantity",
        "unit_price",
        "discount",
        "product_code",
        "product_name",
    )
    return _rows(queries.invoice_lines(), fields)


@saved_query("qrycboOrderStatus")
def qry_cbo_order_status(params: Params) -> list[tuple]:
    """Order statuses by sort order (R-orders-047)."""
    statuses = OrderStatus.objects.order_by("sort_order")
    return _rows(statuses, ("order_status_id", "order_status_name"))


@saved_query("qrycboOrderDetailStatus")
def qry_cbo_order_detail_status(params: Params) -> list[tuple]:
    """Order line statuses by sort order (R-orders-047)."""
    statuses = OrderDetailStatus.objects.order_by("sort_order")
    return _rows(statuses, ("order_detail_status_id", "order_detail_status_name"))
