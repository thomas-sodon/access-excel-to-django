"""Employees: the signed-in employee and an employee's full name.

The signed-in employee (the original's Get_UserID) is the salesperson of a new order
(orders, R-orders-001), the submitter and approver of a purchase order (purchasing,
R-purchasing-004, R-purchasing-005) and the name on every audit stamp (all areas,
R-orders-031, R-inventory-028, R-purchasing-027). A web user is linked to the
employee whose e-mail address equals the user's e-mail address, ignoring case (the
lowest employee number when several match). A user without an employee record still
signs in; their stamps carry their own name, or their e-mail address when the name is
blank.

The full name, first name then last name (the original's FullNameFNLN), is used by
the orders area (employee lists and choices, order lists, the invoice's salesperson),
the reports area (sales per employee) and the purchasing area (submitter and approver
names). The original joins the parts with " " and treats a blank part as empty text,
so the space is always there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from django.db.models import CharField
from django.db.models import F
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.db.models.functions import Concat

from northwind.legacy import audit
from northwind.legacy.models import Employee

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from django.db.models import QuerySet

FULL_NAME = "full_name_fnln"


def full_name_expression(prefix: str = "") -> Concat:
    """FirstName & " " & LastName (R-orders-043). `prefix` reaches the employee
    through a relation ("employee__" from an Order queryset, "submitted_by__" from a
    PurchaseOrder queryset)."""
    return Concat(
        Coalesce(F(f"{prefix}first_name"), Value("")),
        Value(" "),
        Coalesce(F(f"{prefix}last_name"), Value("")),
        output_field=CharField(),
    )


def with_full_name(
    queryset: QuerySet,
    prefix: str = "",
    name: str = FULL_NAME,
) -> QuerySet:
    """Annotate the full name (default name `full_name_fnln`) (R-orders-043)."""
    return queryset.annotate(**{name: full_name_expression(prefix)})


def full_name(employee: Employee | None) -> str | None:
    """FirstName & " " & LastName of one employee; None without an employee
    (R-orders-043)."""
    if employee is None:
        return None
    return f"{employee.first_name or ''} {employee.last_name or ''}"


def signed_in_employee(user: Any) -> Employee | None:
    """The employee record of a signed-in web user, by e-mail address; None for an
    anonymous user or a user without an employee record (R-orders-001,
    R-purchasing-004)."""
    email = (getattr(user, "email", "") or "").strip()
    if not getattr(user, "is_authenticated", False) or not email:
        return None
    return Employee.objects.filter(email_address__iexact=email).order_by("pk").first()


def stamp_name(user: Any) -> str:
    """The audit stamp name of a request's user (R-orders-031): the employee's first
    and last name, else the user's own name or e-mail address; System for nobody."""
    employee = signed_in_employee(user)
    if employee is not None:
        return audit.employee_full_name(employee.first_name, employee.last_name)
    if not getattr(user, "is_authenticated", False):
        return audit.SYSTEM
    name = (getattr(user, "name", "") or "").strip()
    return name or (getattr(user, "email", "") or "").strip() or audit.SYSTEM


def acting_for(user: Any) -> AbstractContextManager[None]:
    """Stamp the rows written in the block with the user's stamp name: wrap every
    service write in `with acting_for(request.user):` (R-orders-031)."""
    return audit.acting_as(stamp_name(user))
