"""rptInvoice: the printable invoice of one order (R-orders-020), as an HTML print
view and, with ?format=pdf, an A4 PDF rendered by django-weasyprint.

The invoice reads the area's invoice query (queries.invoice_lines, the qryInvoice
unit) and its amounts from services.order_amounts. The date shown is the day it is
printed (Q-orders-001). Opening it never changes the order (R-orders-019). An order
without lines has nothing to print (R-orders-021): the page says so, and the PDF link
returns to the order with that message.
"""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DetailView
from django_weasyprint.views import WeasyTemplateResponse

from northwind.legacy.models import Order
from northwind.orders import services
from northwind.orders.views import AreaAccessMixin

NOTHING_TO_PRINT = "R-orders-021: there is nothing to print: the order has no lines."


class InvoiceView(AreaAccessMixin, DetailView):
    model = Order
    template_name = "orders/reports/invoice.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = services.invoice_for(self.object)
        context["nothing_to_print"] = NOTHING_TO_PRINT
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get("format") != "pdf":
            return super().render_to_response(context, **response_kwargs)
        if context["invoice"] is None:
            messages.warning(self.request, NOTHING_TO_PRINT)
            return HttpResponseRedirect(
                reverse("orders:form_frmOrderDetails", kwargs={"pk": self.object.pk}),
            )
        return WeasyTemplateResponse(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            filename=f"invoice-{self.object.pk}.pdf",
            attachment=False,
        )
