"""Screens of the Purchasing and receiving area.

Every view signs in first (anonymous users go to the sign-in page) and then checks
the role: the roles of core/local/roles.py are Django groups with permissions
(core.roles keeps them in step), so a user passes when one of their groups grants
the view's permission and gets 403 otherwise. Writes go through services; a refused
action comes back as an error message naming its rule.

The kept forms (analysis/keep-drop.md) and their URL names:

- frmPurchaseOrderList: form_frmPurchaseOrderList, the list with search, filters
  and the count and total-cost footer (HTMX partial updates).
- frmPurchaseOrderDetails: form_frmPurchaseOrderDetails (the purchase order with
  its workflow steps, amounts and actions), create, update, the workflow actions,
  delete and print (?format=pdf for an A4 PDF).
- sfrmPurchaseOrderLineItems: form_sfrmPurchaseOrderLineItems (the lines partial),
  line_add, line_defaults (fills quantity and unit cost when a product is chosen),
  line_update and line_delete.
- frmSelectVendorDialog: form_frmSelectVendorDialog, the vendor choice of a reorder.
- sfrmCompanyDetail_VendorPurchaseOrders: form_sfrmCompanyDetail_VendorPurchaseOrders,
  a vendor's purchase orders (a partial for the company page).
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView
from django_filters.views import FilterView
from django_tables2 import RequestConfig
from django_tables2 import SingleTableMixin
from django_weasyprint.views import WeasyTemplateResponse

from northwind.legacy.models import Company
from northwind.legacy.models import Product
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail

from . import queries
from . import services
from .filters import PurchaseOrderListFilter
from .forms import CloseForm
from .forms import LineForm
from .forms import PurchaseOrderForm
from .forms import ReceiveForm
from .forms import VendorChoiceForm
from .tables import PurchaseOrderListTable
from .tables import VendorPurchaseOrderTable

VIEW_PO = "legacy.view_purchaseorder"
ADD_PO = "legacy.add_purchaseorder"
CHANGE_PO = "legacy.change_purchaseorder"
DELETE_PO = "legacy.delete_purchaseorder"
VIEW_LINE = "legacy.view_purchaseorderdetail"
ADD_LINE = "legacy.add_purchaseorderdetail"
CHANGE_LINE = "legacy.change_purchaseorderdetail"
DELETE_LINE = "legacy.delete_purchaseorderdetail"


class AreaAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Sign-in, then the role check on the view's permission."""

    permission_required = VIEW_PO


def report_refusal(request, error: ValidationError) -> None:
    for message in error.messages:
        messages.error(request, message)


def detail_url(pk: int) -> str:
    return reverse("purchasing:form_frmPurchaseOrderDetails", kwargs={"pk": pk})


# ------------------------------------------------------------------ the list


class PurchaseOrderListView(AreaAccessMixin, SingleTableMixin, FilterView):
    """frmPurchaseOrderList: every purchase order, newest first, with the count and
    the sum of the total cost in the footer (R-purchasing-025). An HTMX request
    gets only the table partial."""

    model = PurchaseOrder
    table_class = PurchaseOrderListTable
    filterset_class = PurchaseOrderListFilter
    template_name = "purchasing/list.html"
    table_pagination = {"per_page": 25}

    def get_queryset(self):
        return queries.purchase_order_list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = self.object_list
        totals = [row.total_cost for row in rows]
        context["po_count"] = len(totals)
        context["po_total_cost"] = sum(totals) if totals else None
        return context

    def get_template_names(self):
        if self.request.htmx:
            return [f"{self.template_name}#po-table"]
        return [self.template_name]


# ------------------------------------------------------- the purchase order


def lines_context(po: PurchaseOrder, line_form: LineForm | None = None) -> dict:
    """What the line items partial shows (sfrmPurchaseOrderLineItems)."""
    lines = (
        queries.purchase_order_lines(po)
        .select_related("product")
        .annotate(amount=queries.line_amount_expression())
    )
    editable = services.lines_editable(po)
    if editable and line_form is None:
        line_form = LineForm(purchase_order=po)
    return {
        "object": po,
        "lines": lines,
        "amounts": services.purchase_order_amounts(po),
        "lines_editable": editable,
        "line_form": line_form if editable else None,
    }


class PurchaseOrderDetailView(AreaAccessMixin, DetailView):
    """frmPurchaseOrderDetails: the purchase order, its workflow steps (which are
    done, R-purchasing-003), its amounts (R-purchasing-010), its lines and the
    actions its status allows, with who created and last changed it
    (R-purchasing-027)."""

    model = PurchaseOrder
    template_name = "purchasing/detail.html"

    def get_queryset(self):
        return queries.purchase_orders().select_related("vendor", "status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        po = self.object
        context.update(lines_context(po))
        context.update(
            {
                "steps": services.steps_done(po),
                "status": services.Status(po.status_id).label,
                "can_edit": bool(services.editable_fields(po)),
                "can_delete": po.status_id in services.WORKFLOW[:2],
                "can_approve": services.can_approve(self.request.user),
                "is_employee": (
                    services.acting_employee(self.request.user) is not None
                ),
                "receive_form": ReceiveForm(purchase_order=po),
                "close_form": CloseForm(purchase_order=po),
            },
        )
        return context


class PurchaseOrderFormMixin:
    """Create and edit the purchase order header through services."""

    form_class = PurchaseOrderForm
    template_name = "purchasing/form.html"
    object = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object or PurchaseOrder()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        return context

    def form_valid(self, form):
        try:
            self.object = services.save_purchase_order(
                self.object or PurchaseOrder(),
                form.cleaned_data,
                user=self.request.user,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "The purchase order is saved.")
        return HttpResponseRedirect(detail_url(self.object.pk))


class PurchaseOrderCreateView(AreaAccessMixin, PurchaseOrderFormMixin, FormView):
    """A new purchase order: choose the vendor (R-purchasing-015); it starts New
    (R-purchasing-001)."""

    permission_required = ADD_PO


class PurchaseOrderUpdateView(AreaAccessMixin, PurchaseOrderFormMixin, FormView):
    """Edit the fields the status still allows (R-purchasing-011); a Closed
    purchase order is read-only."""

    permission_required = CHANGE_PO

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(PurchaseOrder, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not services.editable_fields(self.object):
            messages.info(
                request,
                f"{services.R_011}: a Closed purchase order is read-only.",
            )
            return HttpResponseRedirect(detail_url(self.object.pk))
        return super().get(request, *args, **kwargs)


class PurchaseOrderActionView(AreaAccessMixin, View):
    """A workflow action on one purchase order (POST only)."""

    permission_required = CHANGE_PO
    http_method_names = ["post"]
    success_message = "The new status is set."

    def act(self, request, po: PurchaseOrder):
        raise NotImplementedError

    def post(self, request, pk: int):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        try:
            result = self.act(request, po)
        except ValidationError as error:
            report_refusal(request, error)
        else:
            if isinstance(result, str):
                messages.success(request, result)
            elif self.success_message:
                messages.success(request, self.success_message)
        return HttpResponseRedirect(self.get_success_url(po))

    def get_success_url(self, po: PurchaseOrder) -> str:
        return detail_url(po.pk)


class SubmitView(PurchaseOrderActionView):
    def act(self, request, po):
        services.submit_purchase_order(po, user=request.user)


class ApproveView(PurchaseOrderActionView):
    def act(self, request, po):
        services.approve_purchase_order(po, user=request.user)


class ReceiveView(PurchaseOrderActionView):
    def act(self, request, po):
        form = ReceiveForm(request.POST)
        confirmed = form.is_valid() and form.cleaned_data["confirm"]
        services.receive_purchase_order(po, confirmed=confirmed, user=request.user)


class CloseView(PurchaseOrderActionView):
    def act(self, request, po):
        form = CloseForm(request.POST)
        if not form.is_valid():
            raise services.refuse(
                services.R_009,
                "the shipping fee must be an amount.",
            )
        services.close_purchase_order(
            po,
            shipping_fee=form.cleaned_data["shipping_fee"],
            payment_method=form.cleaned_data["payment_method"] or None,
            user=request.user,
        )


class DeleteView(PurchaseOrderActionView):
    permission_required = DELETE_PO
    deleted = False

    def act(self, request, po):
        services.delete_purchase_order(po, user=request.user)
        self.deleted = True
        return "The purchase order and its lines are deleted."

    def get_success_url(self, po):
        if self.deleted:
            return reverse("purchasing:form_frmPurchaseOrderList")
        return detail_url(po.pk)


class AddNoStockView(PurchaseOrderActionView):
    permission_required = ADD_LINE

    def act(self, request, po):
        added = services.add_no_stock_lines(po, user=request.user)
        return f"{added} No Stock product line(s) added."


class PurchaseOrderPrintView(AreaAccessMixin, DetailView):
    """The purchase order on one A4 page; ?format=pdf returns it as a PDF
    (django-weasyprint)."""

    model = PurchaseOrder
    template_name = "purchasing/print.html"

    def get_queryset(self):
        return queries.purchase_orders().select_related("vendor", "status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(lines_context(self.object))
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get("format") == "pdf":
            return WeasyTemplateResponse(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                filename=f"purchase-order-{self.object.pk}.pdf",
                attachment=False,
            )
        return super().render_to_response(context, **response_kwargs)


# ------------------------------------------------------------------- lines


class LineItemsView(AreaAccessMixin, DetailView):
    """sfrmPurchaseOrderLineItems: the lines of one purchase order with the
    subtotal; a full page, or only the partial for HTMX."""

    model = PurchaseOrder
    permission_required = VIEW_LINE
    template_name = "purchasing/lines.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(lines_context(self.object))
        return context

    def get_template_names(self):
        if self.request.htmx:
            return ["purchasing/lines.html#lines"]
        return [self.template_name]


class LineFormMixin(AreaAccessMixin):
    """Shared by the add and edit line views: the result is the lines partial for
    HTMX, else a redirect to the purchase order. Warnings never stop a save
    (R-purchasing-019)."""

    template_name = "purchasing/line_form.html"

    def lines_response(self, request, po, line_form=None):
        context = lines_context(po, line_form)
        return self.response_class(
            request=request,
            template=["purchasing/lines.html#lines"],
            context=context,
        )

    def finish(self, request, po, result):
        for warning in result.warnings:
            messages.warning(request, warning)
        if request.htmx:
            return self.lines_response(request, po)
        messages.success(request, "The line is saved.")
        return HttpResponseRedirect(detail_url(po.pk))

    def refused(self, request, po, form, error):
        form.add_error(None, error)
        if request.htmx:
            return self.lines_response(request, po, form)
        return self.render_to_response(self.get_context_data(form=form))


class LineAddView(LineFormMixin, FormView):
    """Add a line (R-purchasing-012, R-purchasing-013, R-purchasing-019,
    R-purchasing-020)."""

    permission_required = ADD_LINE
    form_class = LineForm

    def dispatch(self, request, *args, **kwargs):
        self.purchase_order = get_object_or_404(PurchaseOrder, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["purchase_order"] = self.purchase_order
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.purchase_order
        context["action"] = reverse(
            "purchasing:line_add",
            kwargs={"pk": self.purchase_order.pk},
        )
        return context

    def form_valid(self, form):
        po = self.purchase_order
        data = form.cleaned_data
        try:
            result = services.add_purchase_order_line(
                po,
                data.get("product"),
                data.get("quantity"),
                data.get("unit_cost"),
                user=self.request.user,
            )
        except ValidationError as error:
            return self.refused(self.request, po, form, error)
        return self.finish(self.request, po, result)


class LineDefaultsView(AreaAccessMixin, View):
    """Choosing a product fills in the quantity with its reorder quantity and the
    unit cost with its standard unit cost (R-purchasing-018): returns the line form
    partial with those values, which the user may still change."""

    permission_required = ADD_LINE

    def get(self, request, pk: int):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        initial = {}
        product_id = request.GET.get("product") or ""
        product = (
            queries.vendor_products(po.vendor_id).filter(pk=product_id).first()
            if product_id.isdigit()
            else None
        )
        if product is not None:
            quantity, cost = services.line_defaults(product)
            initial = {"product": product, "quantity": quantity, "unit_cost": cost}
        form = LineForm(purchase_order=po, initial=initial)
        return TemplateView.response_class(
            request=request,
            template=["purchasing/lines.html#line-form"],
            context={"object": po, "line_form": form, "lines_editable": True},
        )


class LineUpdateView(LineFormMixin, FormView):
    """Change a line while the purchase order is New (R-purchasing-012)."""

    permission_required = CHANGE_LINE
    form_class = LineForm

    def dispatch(self, request, *args, **kwargs):
        self.line = get_object_or_404(PurchaseOrderDetail, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.line
        kwargs["purchase_order"] = self.line.purchase_order
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.line.purchase_order
        context["line"] = self.line
        context["action"] = reverse(
            "purchasing:line_update",
            kwargs={"pk": self.line.pk},
        )
        return context

    def form_valid(self, form):
        po = self.line.purchase_order
        data = form.cleaned_data
        try:
            result = services.update_purchase_order_line(
                self.line,
                data.get("product"),
                data.get("quantity"),
                data.get("unit_cost"),
                user=self.request.user,
            )
        except ValidationError as error:
            return self.refused(self.request, po, form, error)
        return self.finish(self.request, po, result)


class LineDeleteView(AreaAccessMixin, View):
    """Delete a line while the purchase order is New (R-purchasing-012)."""

    permission_required = DELETE_LINE
    http_method_names = ["post"]

    def post(self, request, pk: int):
        line = get_object_or_404(PurchaseOrderDetail, pk=pk)
        po = line.purchase_order
        try:
            services.delete_purchase_order_line(line, user=request.user)
        except ValidationError as error:
            report_refusal(request, error)
        if request.htmx:
            return TemplateView.response_class(
                request=request,
                template=["purchasing/lines.html#lines"],
                context=lines_context(po),
            )
        return HttpResponseRedirect(detail_url(po.pk))


# ------------------------------------------------------------ vendor dialog


class SelectVendorView(AreaAccessMixin, FormView):
    """frmSelectVendorDialog (R-purchasing-023): the vendors supplying the product,
    by name. OK without a choice is refused with a prompt, Cancel ends the reorder
    without creating anything, a product with one vendor skips the dialog and a
    product without a vendor cannot be reordered. On OK the dialog returns to the
    caller (`next`) with `vendor=<id>` added; the caller (the inventory area's
    reorder) creates the purchase order line."""

    permission_required = ADD_PO
    form_class = VendorChoiceForm
    template_name = "purchasing/select_vendor.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def next_url(self) -> str:
        candidate = self.request.POST.get("next") or self.request.GET.get("next") or ""
        if candidate and url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return candidate
        return reverse("purchasing:form_frmPurchaseOrderList")

    def chosen(self, vendor: Company) -> HttpResponseRedirect:
        target = self.next_url()
        joiner = "&" if "?" in target else "?"
        query = urlencode({"product": self.product.pk, "vendor": vendor.pk})
        return HttpResponseRedirect(f"{target}{joiner}{query}")

    def get(self, request, *args, **kwargs):
        try:
            choices = services.vendor_choices(self.product)
        except ValidationError as error:
            report_refusal(request, error)
            return HttpResponseRedirect(self.next_url())
        if len(choices) == 1:
            return self.chosen(choices[0])
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["product"] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.product
        context["next"] = self.next_url()
        return context

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            messages.info(request, "The reorder is cancelled; nothing was created.")
            return HttpResponseRedirect(self.next_url())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            vendor = services.choose_vendor(self.product, form.cleaned_data["vendor"])
        except ValidationError as error:
            form.add_error("vendor", error)
            return self.form_invalid(form)
        return self.chosen(vendor)


# ------------------------------------------------- vendor's purchase orders


class VendorPurchaseOrdersView(AreaAccessMixin, TemplateView):
    """sfrmCompanyDetail_VendorPurchaseOrders (R-purchasing-026): a vendor's
    purchase orders that have a submitter, with their count; each number opens the
    purchase order. HTMX gets the partial (for the company page)."""

    template_name = "purchasing/vendor_purchase_orders.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = get_object_or_404(Company, pk=kwargs["pk"])
        rows = queries.vendor_purchase_orders(vendor).order_by("-purchase_order_id")
        table = VendorPurchaseOrderTable(rows)
        RequestConfig(self.request, paginate={"per_page": 25}).configure(table)
        context.update({"vendor": vendor, "table": table, "po_count": rows.count()})
        return context

    def get_template_names(self):
        if self.request.htmx:
            return [f"{self.template_name}#vendor-pos"]
        return [self.template_name]
