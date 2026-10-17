"""The product catalog as a PDF (R-reports-013).

services.product_catalog_pdf renders the catalog twice: once to find on which page
each category section starts, then with those pages in the table of contents. This
module does the layout: render_document lays the catalog out as pages, and
anchor_pages reads the page of every element id, as the original's group header
recorded its page number while printing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from .pdf import render_document as render_template_document

if TYPE_CHECKING:
    import weasyprint

TEMPLATE = "reports/catalog_pdf.html"


def render_document(catalog: Any) -> weasyprint.Document:
    """The catalog (services.Catalog) laid out as A4 pages."""
    return render_template_document(TEMPLATE, {"catalog": catalog})


def anchor_pages(document: weasyprint.Document) -> dict[str, int]:
    """The page number (from 1) on which each element id first appears."""
    pages: dict[str, int] = {}
    for number, page in enumerate(document.pages, start=1):
        for anchor in page.anchors:
            pages.setdefault(anchor, number)
    return pages
