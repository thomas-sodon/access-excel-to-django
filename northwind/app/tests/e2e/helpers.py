"""Shared steps and formats of the Northwind e2e workflows (not a test module).

The status names on the screens are the database's labels of the fixed codes
(legacy.choices), so the tests read them from the database rather than spelling them.
"""

from __future__ import annotations

import datetime as dt
import re
import zlib
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


_OBJECT = re.compile(rb"(\d+)\s+0\s+obj\b(.*?)\bendobj", re.DOTALL)
_STREAM_START = re.compile(rb"\bstream\r?\n")
_DIRECT_LENGTH = re.compile(rb"/Length\s+(\d+)(?!\s+\d+\s+R)")
_HEX = rb"<([0-9a-fA-F]+)>"
_TEXT_OPERATOR = re.compile(
    rb"/([^\s/\[\]<>()]+)\s+[\d.]+\s+Tf|\[(.*?)\]\s*TJ|<([0-9a-fA-F]*)>\s*Tj",
    re.DOTALL,
)


def _pdf_objects(data: bytes) -> dict[int, tuple[bytes, bytes | None]]:
    """Object number -> (dictionary text, decoded stream or None), including the
    objects packed in object streams."""
    objects: dict[int, tuple[bytes, bytes | None]] = {}
    for match in _OBJECT.finditer(data):
        body = match.group(2)
        start = _STREAM_START.search(body)
        if start is None:
            objects[int(match.group(1))] = (body, None)
            continue
        head = body[: start.start()]
        length = _DIRECT_LENGTH.search(head)
        end = start.end() + int(length.group(1)) if length else body.rfind(b"endstream")
        raw = body[start.end() : end]
        if b"/FlateDecode" in head:
            raw = zlib.decompressobj().decompress(raw)
        objects[int(match.group(1))] = (head, raw)
    for head, raw in list(objects.values()):
        if raw is None or b"/ObjStm" not in head:
            continue
        first = int(re.search(rb"/First\s+(\d+)", head).group(1))
        numbers = [int(n) for n in raw[:first].split()]
        pairs = list(zip(numbers[0::2], numbers[1::2], strict=True))
        ends = [offset for _, offset in pairs[1:]] + [len(raw) - first]
        for (number_, offset), end in zip(pairs, ends, strict=True):
            objects.setdefault(number_, (raw[first + offset : first + end], None))
    return objects


def _to_unicode(cmap: bytes) -> dict[int, str]:
    table: dict[int, str] = {}
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", cmap, re.DOTALL):
        for source, target in re.findall(_HEX + rb"\s*" + _HEX, block):
            table[int(source, 16)] = bytes.fromhex(target.decode()).decode("utf-16-be")
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", cmap, re.DOTALL):
        pattern = _HEX + rb"\s*" + _HEX + rb"\s*" + _HEX
        for low, high, target in re.findall(pattern, block):
            base = int(target, 16)
            for step, code in enumerate(range(int(low, 16), int(high, 16) + 1)):
                table[code] = chr(base + step)
    return table


def pdf_text(data: bytes) -> str:
    """The text a reader sees in a PDF that WeasyPrint wrote, one line per text run.

    WeasyPrint draws text as two-byte glyph codes of embedded fonts; each font's
    ToUnicode map turns them back into characters. Reads only the bytes in memory.
    """
    objects = _pdf_objects(data)
    fonts: dict[bytes, dict[int, str]] = {}
    # A font resource is a name that refers to a font with a ToUnicode map, whether
    # the page's font dictionary is inline or an object of its own.
    for head, _ in objects.values():
        for name, ref in re.findall(rb"/([^\s/\[\]<>()]+)\s+(\d+)\s+0\s+R", head):
            font = objects.get(int(ref), (b"", None))[0]
            cmap_ref = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", font)
            if cmap_ref and name != b"ToUnicode":
                cmap = objects.get(int(cmap_ref.group(1)), (b"", None))[1]
                fonts[name] = _to_unicode(cmap or b"")
    runs = []
    for _, content in objects.values():
        if not content or b"BT" not in content:
            continue
        table: dict[int, str] = {}
        for match in _TEXT_OPERATOR.finditer(content):
            if match.group(1) is not None:
                table = fonts.get(match.group(1), {})
                continue
            hexes = re.findall(_HEX, match.group(2) or b"") or [match.group(3)]
            codes = b"".join(bytes.fromhex(h.decode()) for h in hexes)
            runs.append(
                "".join(
                    table.get(int.from_bytes(codes[i : i + 2], "big"), "")
                    for i in range(0, len(codes) - 1, 2)
                ),
            )
    return "\n".join(runs)


def frame(page: Page, top: Locator, *whole: Locator) -> None:
    """Scroll `top` to the top of the viewport and check that the user sees each of
    `whole` entirely (for a screenshot that cuts off no form or button)."""
    scroll_to(top)
    for locator in whole:
        expect(locator).to_be_in_viewport(ratio=1)


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
