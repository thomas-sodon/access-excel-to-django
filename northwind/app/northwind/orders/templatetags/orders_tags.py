"""Template filters of the Orders, Invoicing and Shipping area."""

from __future__ import annotations

from decimal import Decimal

from django import template

from northwind.orders import services

register = template.Library()


@register.filter
def money(value) -> str:
    """A currency amount with two decimals and thousands separators; blank stays
    blank."""
    if value is None or value == "":
        return ""
    return f"{Decimal(value):,.2f}"


@register.filter
def percent(value) -> str:
    """A discount or tax rate as a whole percentage."""
    if value is None or value == "":
        return ""
    return f"{float(value):.0%}"


@register.filter
def phone(value) -> str:
    """A stored phone number shown as 3-3-4 digits (R-orders-045)."""
    return services.format_phone(value)


@register.filter
def history(instance) -> str:
    """The record's one-line history (R-orders-032)."""
    return services.record_history(instance)
