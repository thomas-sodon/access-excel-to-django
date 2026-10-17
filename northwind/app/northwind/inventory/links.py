"""Links from this area's screens to the screens of other areas (the original's
click-to-open handlers: an order, a purchase order, a vendor's company page).

Each area names its kept forms form_<id> (docs/contracts.md#feature-app-contract).
An area that is not installed (MP_ONLY_AREAS, or not built yet) has no URL, so the
link is left out instead of failing.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.urls import NoReverseMatch
from django.urls import reverse


def other_area_url(name: str, pk: int | None) -> str | None:
    """The URL of another area's screen for one record, or None when that screen is
    not installed."""
    if pk is None:
        return None
    try:
        return reverse(name, kwargs={"pk": pk})
    except NoReverseMatch:
        return None


def reorder_entry_url(product_pk: int) -> str:
    """Where the product page's Reorder button goes (R-inventory-018).

    With the purchasing area installed it opens that area's vendor dialog
    (purchasing:form_frmSelectVendorDialog) with `next` set to this area's reorder
    screen. The dialog returns there with `vendor=<id>` added (or skips itself for a
    product with one vendor), and the reorder screen preselects that vendor. Without
    the purchasing area the button opens the reorder screen, which asks for the
    vendor itself."""
    reorder = reverse("inventory:product_reorder", kwargs={"pk": product_pk})
    dialog = other_area_url("purchasing:form_frmSelectVendorDialog", product_pk)
    if dialog is None:
        return reorder
    return f"{dialog}?{urlencode({'next': reorder})}"
