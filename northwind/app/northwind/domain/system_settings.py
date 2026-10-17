"""Values of the system settings table (the original's GetSystemSetting).

Used by the orders area (a new order's default sales tax rate, R-orders-001) and the
purchasing area (the system-wide vendor tax rate, R-purchasing-010). Both rates are
stored as a whole number of thousandths and read divided by 1000, as a Single: the
value is the decimal text a Single shows (7 significant digits). A missing, blank or
non-numeric setting reads as 0, as the original's error path returned Empty.
"""

from __future__ import annotations

from decimal import Decimal
from decimal import InvalidOperation

from northwind.legacy.choices import SystemSettingCode
from northwind.legacy.models import SystemSetting

THOUSANDTHS = Decimal(1000)


def system_setting(code: int) -> str | None:
    """The stored text of one setting (SystemSettingCode), None when missing."""
    return (
        SystemSetting.objects.filter(pk=int(code))
        .values_list("setting_value", flat=True)
        .first()
    )


def _rate(code: int) -> float:
    text = (system_setting(code) or "").strip()
    try:
        value = Decimal(text) / THOUSANDTHS
    except InvalidOperation:
        return 0.0
    return float(f"{value:.7g}")


def sales_tax_rate() -> float:
    """The default sales tax rate of a new order (R-orders-001)."""
    return _rate(SystemSettingCode.SALES_TAX_RATE)


def vendor_tax_rate() -> float:
    """The vendor tax rate of every purchase order (R-purchasing-010)."""
    return _rate(SystemSettingCode.VENDOR_TAX_RATE)
