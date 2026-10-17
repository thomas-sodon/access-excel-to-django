"""Screens of the Sales and Catalog Reports area.

Every view signs in first (anonymous users go to the sign-in page) and then checks
the role: the roles of core/local/roles.py are Django groups with permissions, so a
user passes when one of their groups grants the view's permission and gets 403
otherwise. The sales reports need the right to view orders, the catalog the right
to view products; every role of Northwind has both (R-orders-050).

- ReportSelectionView: the report selection page (frmReports), the main menu's
  Reports entry (R-reports-016). Choosing a report swaps the criteria with HTMX.
- SalesReportView: the three sales reports as an HTML view and an A4 PDF; the sales
  per employee report is interactive (filter by salesperson, R-reports-009).
- CatalogView and CatalogPartView: the product catalog and its sub-reports.

The area writes nothing, so no view calls a write service.
"""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.views.generic import TemplateView

from . import services
from .forms import PeriodForm
from .reports.pdf import pdf_response

SALES_PERMISSION = "legacy.view_order"
CATALOG_PERMISSION = "legacy.view_product"
#: The catalog's table of contents from the user's last PDF generation
#: (R-reports-013); the catalog itself is never stored (Q-reports-005).
TOC_SESSION_KEY = "reports.catalog_toc"


def report_url(name: str) -> str:
    return reverse(f"reports:report_{name}")


def selection_url(name: str | None = None, **query: str) -> str:
    params = {"report": name, **query} if name else query
    url = reverse("reports:form_frmReports")
    return f"{url}?{urlencode(params)}" if params else url


class ReportsAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Sign-in, then the role check."""

    permission_required = (SALES_PERMISSION,)


class ReportSelectionView(ReportsAccessMixin, TemplateView):
    """The report selection page: the monthly sales per employee report is chosen
    when it opens (R-reports-001); a sales report shows the dates with their
    defaults, the catalog hides them (R-reports-002); Preview opens the chosen
    report (R-reports-016)."""

    template_name = "reports/selection.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        try:
            selection = services.report_selection(self.request.GET.get("report"))
        except ValidationError as error:
            raise Http404(" ".join(error.messages)) from error
        initial = {}
        if selection.period is not None:
            initial = {
                "start": selection.period.start.date(),
                "end": selection.period.end.date(),
            }
        context.update(
            selection=selection,
            reports=[
                {"kind": kind, "url": selection_url(kind.name)}
                for kind in services.REPORTS.values()
            ],
            form=PeriodForm(initial=initial),
            preview_url=report_url(selection.report.name),
        )
        return context

    def get_template_names(self) -> list[str]:
        if self.request.htmx:
            return [f"{self.template_name}#selection"]
        return [self.template_name]


def _employee_id(value: str | None) -> int:
    try:
        return max(int(value or 0), 0)
    except ValueError:
        return 0


class SalesReportView(ReportsAccessMixin, TemplateView):
    """One sales report for the period of the request (start and end, ISO dates;
    blank or missing dates take the default period, R-reports-003). ?format=pdf
    returns it as an A4 PDF. A period without data goes back to the selection page
    with the no-data message, and the report does not open (R-reports-008)."""

    report_name = services.SALES_BY_EMPLOYEE
    template_name = "reports/sales_report.html"
    pdf_template_name = "reports/sales_report_pdf.html"

    def get(self, request, *args, **kwargs):
        form = PeriodForm(request.GET)
        if not form.is_valid():
            messages.error(request, "Enter the start and end dates as dates.")
            return redirect(selection_url(self.report_name))
        try:
            period = services.sales_report_period(
                form.cleaned_data["start"],
                form.cleaned_data["end"],
            )
            report = services.sales_report(
                self.report_name,
                period,
                _employee_id(request.GET.get("employee")),
            )
        except ValidationError as error:
            messages.warning(request, " ".join(error.messages))
            return redirect(selection_url(self.report_name))
        query = {**period.as_query()}
        if report.employee_id:
            query["employee"] = str(report.employee_id)
        context = self.get_context_data(
            report=report,
            pdf_url=f"{request.path}?{urlencode({**query, 'format': 'pdf'})}",
            back_url=selection_url(self.report_name),
        )
        if request.GET.get("format") == "pdf":
            return pdf_response(
                request,
                self.pdf_template_name,
                context,
                filename=f"{self.report_name}.pdf",
            )
        if request.htmx:
            return self.response_class(
                request=request,
                template=[f"{self.template_name}#report-body"],
                context=context,
            )
        return self.render_to_response(context)


def _stored_toc(request) -> list[services.TocEntry] | None:
    stored = request.session.get(TOC_SESSION_KEY)
    if stored is None:
        return None
    return [services.TocEntry(title, page) for title, page in stored]


class CatalogView(ReportsAccessMixin, TemplateView):
    """The product catalog as a print preview, ?format=pdf as the A4 PDF.

    Generating the PDF builds the table of contents (R-reports-013) and keeps it in
    the user's session, so the preview shows it afterwards; until then the preview
    shows the note that asks for the PDF. A catalog without products still opens,
    with the no-data warning (R-reports-015)."""

    permission_required = (CATALOG_PERMISSION,)
    template_name = "reports/catalog.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("format") == "pdf":
            result = services.product_catalog_pdf()
            request.session[TOC_SESSION_KEY] = [
                [entry.title, entry.page] for entry in result.toc
            ]
            response = HttpResponse(result.pdf, content_type="application/pdf")
            response["Content-Disposition"] = 'inline; filename="rptProductCatalog.pdf"'
            return response
        catalog = services.product_catalog(toc=_stored_toc(request))
        if catalog.no_data:
            messages.warning(request, catalog.no_data)
        return self.render_to_response(
            self.get_context_data(
                catalog=catalog,
                pdf_url=f"{request.path}?format=pdf",
            ),
        )


class CatalogPartView(ReportsAccessMixin, TemplateView):
    """One sub-report of the catalog on its own page (the table of contents, the
    quality and gastronomic pages, the order form and its shipper list)."""

    permission_required = (CATALOG_PERMISSION,)
    part = "quality"
    source = "srptQuality"
    template_name = "reports/catalog_part.html"
    pdf_template_name = "reports/catalog_part_pdf.html"

    def get(self, request, *args, **kwargs):
        catalog = services.product_catalog(toc=_stored_toc(request))
        context = self.get_context_data(
            catalog=catalog,
            part_template=f"reports/_catalog_parts.html#{self.part}",
            pdf_url=f"{request.path}?format=pdf",
            back_url=report_url(services.PRODUCT_CATALOG),
        )
        if request.GET.get("format") == "pdf":
            return pdf_response(
                request,
                self.pdf_template_name,
                context,
                filename=f"{self.source}.pdf",
            )
        return self.render_to_response(context)
