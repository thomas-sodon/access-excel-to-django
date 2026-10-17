"""Links from this area's screens to the screens of other areas (the original's
click-to-open handlers: an order, a purchase order, a vendor's company page).

Each area names its kept forms form_<id> (docs/contracts.md#feature-app-contract).
An area that is not installed (MP_ONLY_AREAS, or not built yet) has no URL, so the
link is left out instead of failing.
"""

from __future__ import annotations

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
