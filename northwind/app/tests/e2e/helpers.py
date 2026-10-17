"""Shared steps and formats of the Northwind e2e workflows (not a test module).

The status names on the screens are the database's labels of the fixed codes
(legacy.choices), so the tests read them from the database rather than spelling them.
"""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP
from decimal import Decimal
from decimal import InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import expect

from northwind.core.management.commands.create_demo_users import ADMIN_EMAIL
from northwind.core.management.commands.create_demo_users import demo_email
from northwind.core.roles import role_names
from northwind.legacy.models import Employee

if TYPE_CHECKING:
    from playwright.sync_api import Download
    from playwright.sync_api import Locator
    from playwright.sync_api import Page

CENT = Decimal("0.01")


def no_op(*_args) -> None:
    """Stands in for shot or pause when a caller does not want them."""


def money(value: Decimal | float) -> str:
    """An amount as the order screens print it: two decimals, thousands commas."""
    return f"{Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP):,}"


def number(text: str) -> Decimal:
    """A figure read from the screen ("1,234.50", "12")."""
    cleaned = text.strip().replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation as error:
        msg = f"not a number on the screen: {text!r}"
        raise AssertionError(msg) from error


def local_input(moment: dt.datetime | None = None) -> str:
    """A value for a datetime-local input."""
    moment = moment or dt.datetime.now()  # noqa: DTZ005 (the app keeps naive times)
    return moment.strftime("%Y-%m-%dT%H:%M")


def open_from_list(page: Page, link: Locator) -> None:
    """Click a record's link on a list screen; the record's own screen opens as a
    whole page (one navigation bar, not a page nested inside the list)."""
    link.click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("nav.navbar")).to_have_count(1)


def read_pdf(download: Download) -> bytes:
    """The downloaded file's bytes, from Playwright's own temporary copy."""
    data = Path(download.path()).read_bytes()
    assert data.startswith(b"%PDF-"), f"{download.suggested_filename} is not a PDF"
    return data


def levels(page: Page) -> dict[str, int]:
    """The product page's stock levels table (inventory _levels.html)."""
    table = page.locator("#product-levels")
    figures = {}
    for row in table.locator("tbody tr").all():
        label = row.locator("th").inner_text().strip()
        figures[label] = int(number(row.locator("td").inner_text()))
    return {
        "to_sell": figures["Quantity to sell"],
        "no_stock": figures["No stock (waiting order lines)"],
        "allocated": figures["Allocated"],
        "on_order": figures["On order"],
        "reorder": figures["Suggested reorder quantity"],
    }


def scroll_to(locator: Locator) -> None:
    """Scroll so the element is at the top of the viewport (for a screenshot)."""
    locator.evaluate("element => element.scrollIntoView({block: 'start'})")


def link_employee(role: str) -> Employee:
    """Give the demo user of `role` an employee record, as an administrator does.

    A purchase order records the signed-in employee (the employee whose e-mail
    address is the sign-in e-mail) as submitter and approver, and refuses a user
    without one (R-purchasing-004, R-purchasing-005). create_demo_users makes no
    employees, so the first seed employee, by number, that no demo user has taken
    gets this role's sign-in e-mail address.
    """
    email = demo_email(role)
    linked = Employee.objects.filter(email_address__iexact=email).first()
    if linked is not None:
        return linked
    demo_addresses = [demo_email(name) for name in role_names()] + [ADMIN_EMAIL]
    employee = (
        Employee.objects.exclude(email_address__in=demo_addresses)
        .order_by("pk")
        .first()
    )
    assert employee is not None, "the seed has no employee to link"
    Employee.objects.filter(pk=employee.pk).update(email_address=email)
    employee.refresh_from_db()
    return employee


def sign_out(page: Page) -> None:
    page.get_by_role("link", name="Sign Out").click()
    page.get_by_role("button", name="Sign Out").click()
    page.wait_for_load_state()
