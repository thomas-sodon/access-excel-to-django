"""Template filters of the reports: amounts as the original reports print them."""

from django import template

from northwind.core import vbacompat

register = template.Library()


@register.filter
def currency(value):
    """Format(value, "Currency"); blank for a blank value."""
    if value is None or value == "":
        return ""
    return vbacompat.format_(value, "Currency")
