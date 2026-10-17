"""The order-date period of the sales reports (R-reports-002, R-reports-003).

The original's report parameter functions give the sales queries their period: the
start and end dates of the report selection page, or, without that page, a default
derived from the latest order date. The default end date is the calendar date of
the latest order (midnight) and the start date the same day three calendar months
earlier (VBA DateAdd, so 31 May goes back to the last day of February). The queries
compare the full order date and time with both bounds, inclusive, so orders placed
on the end date after midnight are left out, as in the original (Q-reports-002).

Shared by saved_queries.py (the units run without the selection page, so they take
the default) and services.py (the screens).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db.models import Max

from northwind.core import vbacompat
from northwind.legacy.models import Order

if TYPE_CHECKING:
    import datetime as dt

PERIOD_RULE = "R-reports-003"
MONTHS_BACK = 3


@dataclass(frozen=True)
class Period:
    """Inclusive order-date bounds, both at midnight (Access dates)."""

    start: dt.datetime
    end: dt.datetime

    @property
    def caption(self) -> str:
        """The report header line (R-reports-007): the dates as Access prints
        them (short date, United States settings)."""
        return (
            f"Order dates between {vbacompat.format_(self.start, 'Short Date')} "
            f"and {vbacompat.format_(self.end, 'Short Date')}"
        )

    def as_query(self) -> dict[str, str]:
        """The period as the report URLs' query parameters (ISO dates)."""
        return {
            "start": self.start.date().isoformat(),
            "end": self.end.date().isoformat(),
        }


def as_midnight(value: dt.date | dt.datetime) -> dt.datetime:
    """DateValue: the calendar date of a date or date and time, at midnight."""
    return vbacompat.datevalue(value)


def latest_order_date() -> dt.datetime | None:
    """The calendar date of the most recent order date (DateValue(DMax(...)))."""
    latest = Order.objects.aggregate(latest=Max("order_date"))["latest"]
    return None if latest is None else as_midnight(latest)


def default_period() -> Period:
    """R-reports-003: from three calendar months before the latest order's date up to
    that date. Without any order there is nothing to derive it from."""
    end = latest_order_date()
    if end is None:
        msg = (
            f"{PERIOD_RULE}: there are no orders, so the report period cannot be "
            "set from the latest order date. Enter a start and an end date."
        )
        raise ValidationError(msg, code=PERIOD_RULE)
    return Period(start=vbacompat.dateadd("m", -MONTHS_BACK, end), end=end)
