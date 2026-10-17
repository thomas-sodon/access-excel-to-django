"""A4 PDFs of the area's reports (django-weasyprint).

WeasyPrint resolves the pages' stylesheet and script links against a base URL.
django-weasyprint's default base URL is the request's own host, which makes
WeasyPrint fetch /static/... over HTTP from the server it runs in (and fail where
there is no network, as in tests). With a file:/// base URL, django-weasyprint's
DjangoURLFetcher serves STATIC_URL paths straight from the static file finders, so
a report renders offline with its local stylesheet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import weasyprint
from django.template.loader import render_to_string
from django_weasyprint.utils import DjangoURLFetcher
from django_weasyprint.views import WeasyTemplateResponse

if TYPE_CHECKING:
    from django.http import HttpRequest

BASE_URL = "file:///"


class PdfResponse(WeasyTemplateResponse):
    """A template rendered to a PDF, with static files read from disk."""

    def get_base_url(self) -> str:
        return BASE_URL


def pdf_response(
    request: HttpRequest,
    template: str | list[str],
    context: dict[str, Any],
    filename: str,
) -> PdfResponse:
    """The template as an inline A4 PDF (the page size is in reports.css)."""
    return PdfResponse(
        request=request,
        template=template,
        context=context,
        filename=filename,
        attachment=False,
    )


def render_document(
    template: str,
    context: dict[str, Any],
    request: HttpRequest | None = None,
) -> weasyprint.Document:
    """Lay the template out as PDF pages without writing them, so a caller can read
    the pages (and their anchors) before producing the file."""
    html = render_to_string(template, context, request=request)
    return weasyprint.HTML(
        string=html,
        base_url=BASE_URL,
        url_fetcher=DjangoURLFetcher(),
    ).render()
