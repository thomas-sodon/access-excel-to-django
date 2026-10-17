"""Template filters of the Purchasing and receiving area."""

from __future__ import annotations

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def money(value) -> str:
    """A currency amount with two decimals and thousands separators, as the orders
    area shows it; blank stays blank. The stored value keeps its four decimals."""
    if value is None or value == "":
        return ""
    return f"{Decimal(value):,.2f}"
