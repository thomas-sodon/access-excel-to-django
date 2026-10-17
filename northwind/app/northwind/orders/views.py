"""Screens of the Orders, Invoicing and Shipping area.

Every view signs in first (anonymous users go to the sign-in page) and then checks
the role: the roles of core/local/roles.py are Django groups with permissions, so a
user passes when one of their groups grants the view's permission on the table it
shows or writes, and gets 403 otherwise. Writes go through services.py; a refused
action shows the service's message, which names the rule.

URL names follow the contract (docs/contracts.md#feature-app-contract):
form_<original form> and report_<original report>; see urls.py.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import DetailView
from django.views.generic import TemplateView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from northwind.domain.people import signed_in_employee
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.choices import TaxStatusCode
from northwind.legacy.models import Company
from northwind.legacy.models import Contact
from northwind.legacy.models import Employee
from northwind.legacy.models import EmployeePrivilege
from northwind.legacy.models import Order
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import Title

from . import queries
from . import services
from .filters import CompanyFilter
from .filters import EmployeeFilter
from .filters import OrderFilter
from .forms import CompanyForm
from .forms import ContactForm
from .forms import EmployeeForm
from .forms import OrderLineForm
from .forms import PaymentForm
from .forms import PrivilegeGrantForm
from .forms import ShipForm
from .forms import TitleForm
from .forms import order_form_class
from .tables import CompanyTable
from .tables import EmployeeTable
from .tables import OrderTable

YES = "yes"


class AreaAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Sign-in, then the role check on `<app_label>.<action>_<model>`. A POST checks
    `post_action` when the view sets one."""

    action = "view"
    post_action: str | None = None

    def get_permission_required(self):
        opts = self.model._meta  # noqa: SLF001 (Django's documented Options API)
        action = self.action
        if self.post_action and self.request.method == "POST":
            action = self.post_action
        return (f"{opts.app_label}.{action}_{opts.model_name}",)


class HtmxPartialMixin:
    """A full page normally; only the named partial for an HTMX request."""

    partial_name = ""

    def get_template_names(self):
        names = super().get_template_names()
        if self.request.htmx and self.partial_name:
            return [f"{names[0]}#{self.partial_name}"]
        return names


def add_service_error(form, error: ValidationError) -> None:
    """Show a service's refusal on the form: on the fields it names when the form has
    them, else above the form."""
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


def flash_errors(request, error: ValidationError) -> None:
    for message in error.messages:
        messages.error(request, message)


def safe_next(request, default: str) -> str:
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}):
        return target
    return default


class ServiceFormView(AreaAccessMixin, View):
    """A form page whose save goes through a service. Subclasses give
    get_object(), get_form(data) and save(form) -> redirect URL."""

    template_name = "orders/form.html"
    title = ""
    object = None

    def get_object(self):
        return None

    def get_form(self, data=None):
        raise NotImplementedError

    def save(self, form) -> str:
        raise NotImplementedError

    def get_cancel_url(self) -> str:
        return reverse("orders:form_frmOrderList")

    def get_context(self, form, **extra):
        return {
            "form": form,
            "object": self.object,
            "title": self.title,
            "cancel_url": self.get_cancel_url(),
            **extra,
        }

    def render_form(self, form, **extra):
        return render(self.request, self.template_name, self.get_context(form, **extra))

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_form(self.get_form())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form(request.POST)
        if form.is_valid():
            try:
                url = self.save(form)
            except ValidationError as error:
                add_service_error(form, error)
            else:
                return HttpResponseRedirect(url)
        return self.render_form(form)


class ConfirmView(AreaAccessMixin, View):
    """A confirmation page (GET) and the confirmed action (POST)."""

    template_name = "orders/confirm.html"
    title = ""

    def get_object(self):
        raise NotImplementedError

    def question(self) -> str:
        raise NotImplementedError

    def refusal(self) -> str | None:
        """A reason the action is refused before asking, or None."""
        return None

    def perform(self) -> str:
        """Do the confirmed action through its service; return the next URL."""
        raise NotImplementedError

    def get_cancel_url(self) -> str:
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = {
            "object": self.object,
            "title": self.title,
            "question": self.question(),
            "refusal": self.refusal(),
            "cancel_url": self.get_cancel_url(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            url = self.perform()
        except ValidationError as error:
            flash_errors(request, error)
            return HttpResponseRedirect(self.get_cancel_url())
        return HttpResponseRedirect(url)


# ================================================================ orders


class OrderListView(AreaAccessMixin, HtmxPartialMixin, SingleTableMixin, FilterView):
    """frmOrderList: the order list with its four filters (R-orders-024,
    R-orders-025) and a footer with the count and sum of the orders shown
    (R-orders-026). The list opens on Open orders; an HTMX request gets only the
    table partial."""

    model = Order
    table_class = OrderTable
    filterset_class = OrderFilter
    template_name = "orders/order_list.html"
    partial_name = "record-table"
    table_pagination = {"per_page": 25}

    def get_queryset(self):
        return queries.order_list()

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        data = kwargs["data"].copy() if kwargs["data"] is not None else {}
        if not data.get("show"):
            data["show"] = services.DEFAULT_ORDER_FILTER
        kwargs["data"] = data
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        count, total = services.order_list_footer(self.object_list)
        show = self.filterset.data.get("show")
        context.update(
            footer_count=count,
            footer_total=total,
            no_recent_orders=show == "recent" and count == 0,
        )
        return context


class StartView(OrderListView):
    """frmLogin: the sign-in itself is the foundation's; after signing in, the order
    list is the first screen (R-orders-050)."""


class OrderDetailView(AreaAccessMixin, DetailView):
    """frmOrderDetails: the order with its lines, amounts (R-orders-022), history
    (R-orders-032) and the next workflow action highlighted (R-orders-030)."""

    model = Order
    template_name = "orders/order_detail.html"

    def get_queryset(self):
        return queries.orders_with_names().select_related(
            "customer",
            "shipper",
            "tax_status",
            "order_status",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        context.update(order_context(order))
        context.update(
            next_action=services.next_action(order),
            can_reprint=services.can_reprint_invoice(order),
            editable=bool(services.editable_order_fields(order)),
            ship_form=ShipForm(
                initial={
                    "shipped_date": order.shipped_date,
                    "shipper": order.shipper_id,
                },
            ),
            payment_form=PaymentForm(
                initial={
                    "payment_method": order.payment_method,
                    "paid_date": order.paid_date,
                },
            ),
            can_delete=order.order_status_id
            in (OrderStatusCode.NEW, OrderStatusCode.INVOICED),
        )
        return context


def order_context(order: Order, form: OrderLineForm | None = None) -> dict:
    """The order lines partial's context (sfrmOrderLineItems): lines with their
    price, the order's amounts (R-orders-022) and the add form while the order is
    New (R-orders-013)."""
    lines = (
        queries.order_lines().filter(order=order).select_related("order_detail_status")
    )
    lines_open = order.order_status_id == OrderStatusCode.NEW
    return {
        "order": order,
        "lines": [(line, services.line_price(line)) for line in lines],
        "lines_open": lines_open,
        "amounts": services.order_amounts(order),
        "line_form": form or (OrderLineForm() if lines_open else None),
    }


class OrderCreateView(ServiceFormView):
    """A new order, pre-filled (R-orders-001). Choosing the customer fills in its
    standard tax status (R-orders-002, an HTMX swap of that field)."""

    action = "add"
    model = Order
    template_name = "orders/order_form.html"
    title = "New order"

    def get_form(self, data=None):
        self.order = services.new_order(self.request.user)
        initial = {}
        customer = self.request.GET.get("customer")
        if data is None and customer and customer.isdigit():
            initial = {
                "customer": customer,
                "tax_status": services.customer_tax_status(int(customer)),
            }
        form = order_form_class(self.order)(data, instance=self.order, initial=initial)
        form.fields["customer"].widget.attrs.update(
            {
                "hx-get": reverse("orders:order_create"),
                "hx-target": "#div_id_tax_status",
                "hx-select": "#div_id_tax_status",
                "hx-swap": "outerHTML",
                "hx-include": "this",
            },
        )
        return form

    def save(self, form) -> str:
        order = services.save_order(
            self.order,
            form.cleaned_data,
            user=self.request.user,
        )
        messages.success(self.request, f"Order {order.pk} saved; add its lines.")
        return reverse("orders:form_frmOrderDetails", kwargs={"pk": order.pk})


class OrderUpdateView(ServiceFormView):
    """Edit the order header: only the fields its status leaves open
    (R-orders-014)."""

    action = "change"
    model = Order
    template_name = "orders/order_form.html"

    def get_object(self):
        order = get_object_or_404(Order, pk=self.kwargs["pk"])
        self.title = f"Order {order.pk}"
        return order

    def get_cancel_url(self) -> str:
        return reverse("orders:form_frmOrderDetails", kwargs={"pk": self.object.pk})

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not services.editable_order_fields(self.object):
            messages.info(
                request,
                "R-orders-014: nothing on a Closed order can be edited.",
            )
            return HttpResponseRedirect(self.get_cancel_url())
        return self.render_form(self.get_form())

    def get_form(self, data=None):
        return order_form_class(self.object)(data, instance=self.object)

    def save(self, form) -> str:
        services.save_order(self.object, form.cleaned_data, user=self.request.user)
        messages.success(self.request, "Order saved.")
        return self.get_cancel_url()


class OrderActionView(AreaAccessMixin, View):
    """The order's workflow actions: create invoice, ship, receive payment and close
    (R-orders-015 to R-orders-018, R-orders-030). Creating the invoice opens it."""

    action = "change"
    model = Order
    http_method_names = ["post"]

    def post(self, request, pk: int, verb: str):
        order = get_object_or_404(Order, pk=pk)
        detail = reverse("orders:form_frmOrderDetails", kwargs={"pk": pk})
        try:
            url = self.perform(order, verb) or detail
        except ValidationError as error:
            flash_errors(request, error)
            return HttpResponseRedirect(detail)
        return HttpResponseRedirect(url)

    def perform(self, order: Order, verb: str) -> str | None:
        user = self.request.user
        data = self.request.POST
        if verb == "invoice":
            services.create_invoice(order, user=user)
            messages.success(self.request, f"Order {order.pk} invoiced.")
            return reverse("orders:report_rptInvoice", kwargs={"pk": order.pk})
        if verb == "ship":
            form = ShipForm(data)
            form.is_valid()
            services.ship_order(
                order,
                shipped_date=form.cleaned_data.get("shipped_date"),
                shipper=form.cleaned_data.get("shipper"),
                user=user,
            )
        elif verb == "pay":
            form = PaymentForm(data)
            form.is_valid()
            services.receive_payment(
                order,
                payment_method=form.cleaned_data.get("payment_method") or None,
                paid_date=form.cleaned_data.get("paid_date"),
                user=user,
            )
        elif verb == "close":
            services.close_order(
                order,
                confirmed=data.get("confirmed") == YES,
                user=user,
            )
        else:
            msg = f"unknown action {verb}"
            raise ValidationError(msg)
        messages.success(self.request, f"Order {order.pk} is now {order.order_status}.")
        return None


class OrderDeleteView(ConfirmView):
    """Delete an order after confirmation (R-orders-011, R-orders-012)."""

    action = "delete"
    model = Order
    title = "Delete order"

    def get_object(self):
        return get_object_or_404(Order, pk=self.kwargs["pk"])

    def question(self) -> str:
        return f"Delete order {self.object.pk} and all its lines?"

    def refusal(self) -> str | None:
        if self.object.order_status_id in (
            OrderStatusCode.NEW,
            OrderStatusCode.INVOICED,
        ):
            return None
        return "R-orders-012: only a New or Invoiced order can be deleted."

    def get_cancel_url(self) -> str:
        return reverse("orders:form_frmOrderDetails", kwargs={"pk": self.object.pk})

    def perform(self) -> str:
        services.delete_order(self.object, user=self.request.user)
        messages.success(self.request, "Order deleted.")
        return reverse("orders:form_frmOrderList")


# ---------------------------------------------------------------- order lines


class OrderLinesView(AreaAccessMixin, View):
    """sfrmOrderLineItems: the order's lines with the add form. The category list
    narrows the products (R-orders-008); adding goes through save_order_line."""

    model = OrderDetail
    post_action = "add"
    template_name = "orders/order_lines.html"

    def render_lines(self, order, form=None):
        context = order_context(order, form)
        if not self.request.htmx:
            return render(self.request, self.template_name, context)
        # The swap replaces #order-lines; the amounts beside it on the order screen
        # come along out of band, so they follow the lines (R-orders-022).
        lines = render_to_string(
            f"{self.template_name}#order-lines",
            context,
            request=self.request,
        )
        amounts = render_to_string(
            f"{self.template_name}#order-amounts",
            {**context, "amounts_oob": True},
            request=self.request,
        )
        return HttpResponse(lines + amounts)

    def get(self, request, pk: int):
        order = get_object_or_404(Order, pk=pk)
        category = request.GET.get("category") or None
        form = None
        if category is not None or "product" in request.GET:
            form = OrderLineForm(initial=request.GET.dict(), category=category)
        return self.render_lines(order, form)

    def post(self, request, pk: int):
        order = get_object_or_404(Order, pk=pk)
        form = OrderLineForm(
            request.POST,
            category=request.POST.get("category") or None,
        )
        if form.is_valid():
            try:
                services.save_order_line(
                    order,
                    None,
                    form.cleaned_data,
                    user=request.user,
                )
            except ValidationError as error:
                add_service_error(form, error)
            else:
                if not request.htmx:
                    return HttpResponseRedirect(
                        reverse("orders:form_frmOrderDetails", kwargs={"pk": pk}),
                    )
                form = None
        return self.render_lines(order, form)


class OrderLineUpdateView(ServiceFormView):
    """Change one order line (R-orders-006 to R-orders-010, R-orders-013)."""

    action = "change"
    model = OrderDetail
    title = "Order line"

    def get_object(self):
        return get_object_or_404(
            OrderDetail,
            pk=self.kwargs["line"],
            order_id=self.kwargs["pk"],
        )

    def get_cancel_url(self) -> str:
        return reverse(
            "orders:form_frmOrderDetails",
            kwargs={"pk": self.object.order_id},
        )

    def get_form(self, data=None):
        line = self.object
        initial = {
            "category": line.product.product_category_id,
            "product": line.product_id,
            "quantity": line.quantity,
            "discount": line.discount,
        }
        category = (data or {}).get("category") or None
        form = OrderLineForm(data, initial=initial, category=category)
        form.helper.form_tag = True
        form.helper.add_input(_submit("Save"))
        return form

    def save(self, form) -> str:
        services.save_order_line(
            self.object.order,
            self.object,
            form.cleaned_data,
            user=self.request.user,
        )
        return self.get_cancel_url()


def _submit(label: str):
    from crispy_forms.layout import Submit  # noqa: PLC0415

    return Submit("save", label)


class OrderLineDeleteView(ConfirmView):
    """Delete one order line after confirmation (R-orders-010, R-orders-013)."""

    action = "delete"
    model = OrderDetail
    title = "Delete order line"

    def get_object(self):
        return get_object_or_404(
            OrderDetail,
            pk=self.kwargs["line"],
            order_id=self.kwargs["pk"],
        )

    def question(self) -> str:
        line = self.object
        return f"Delete the line for {line.product} from order {line.order_id}?"

    def get_cancel_url(self) -> str:
        return reverse(
            "orders:form_frmOrderDetails",
            kwargs={"pk": self.object.order_id},
        )

    def perform(self) -> str:
        services.delete_order_line(self.object, user=self.request.user)
        messages.success(self.request, "Order line deleted.")
        return self.get_cancel_url()


# ================================================================ companies


class CompanyListView(AreaAccessMixin, HtmxPartialMixin, SingleTableMixin, FilterView):
    """frmCompanyList: the read-only company list filtered to Customers, Shippers,
    Vendors or all, the heading following the filter (R-orders-037)."""

    model = Company
    table_class = CompanyTable
    filterset_class = CompanyFilter
    template_name = "orders/company_list.html"
    partial_name = "record-table"
    table_pagination = {"per_page": 25}

    def get_queryset(self):
        return queries.company_list()

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        data = kwargs["data"].copy() if kwargs["data"] is not None else {}
        data["show"] = services.company_filter(data.get("show"))[0]
        kwargs["data"] = data
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        show, heading, _type = services.company_filter(self.filterset.data.get("show"))
        context.update(show=show, heading=heading)
        return context


class CompanyDetailView(AreaAccessMixin, DetailView):
    """frmCompanyDetail: titled with the company type, with the related list that
    fits the type (R-orders-035), the contacts and the record history
    (R-orders-032)."""

    model = Company
    template_name = "orders/company_detail.html"

    def get_queryset(self):
        return queries.company_list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.object
        related = services.company_related_list(company.company_type_id)
        context.update(company_orders_context(company))
        context.update(
            related=related[0] if related else None,
            related_heading=related[1] if related else "",
            contacts=company.contacts.order_by("last_name", "first_name"),
            contact_form=ContactForm(),
        )
        return context


def company_orders_context(company: Company) -> dict:
    """The company screen's order lists (R-orders-028)."""
    return {
        "company": company,
        "customer_orders": queries.customer_orders().filter(customer=company),
        "shipper_orders": queries.shipper_orders().filter(shipper=company),
        "purchase_orders": PurchaseOrder.objects.filter(vendor=company).order_by(
            "-purchase_order_id",
        ),
    }


class CompanyFormMixin:
    """Saving a company asks for confirmation first; answering no discards the
    changes (R-orders-036)."""

    template_name = "orders/company_form.html"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form(request.POST)
        if not form.is_valid():
            return self.render_form(form)
        if request.POST.get("confirmed") != YES:
            return self.render_form(form, confirm=True)
        try:
            company = services.save_company(
                self.object or Company(),
                form.cleaned_data,
                confirmed=True,
                user=request.user,
            )
        except ValidationError as error:
            add_service_error(form, error)
            return self.render_form(form)
        messages.success(request, "Company saved.")
        return HttpResponseRedirect(
            reverse("orders:form_frmCompanyDetail", kwargs={"pk": company.pk}),
        )


class CompanyCreateView(CompanyFormMixin, ServiceFormView):
    """A new company; from the list it takes the list's filtered type
    (R-orders-037), and a name typed in the order's customer field fills in its name
    (R-orders-038). Tax Exempt until the user picks another (R-orders-048)."""

    action = "add"
    model = Company
    title = "New company"

    def get_cancel_url(self) -> str:
        return reverse("orders:form_frmCompanyList")

    def get_form(self, data=None):
        _show, _heading, company_type = services.company_filter(
            self.request.GET.get("show"),
        )
        initial = {"standard_tax_status": TaxStatusCode.TAX_EXEMPT}
        if company_type is not None:
            initial["company_type"] = company_type
        if self.request.GET.get("name"):
            initial["company_name"] = self.request.GET["name"]
        return CompanyForm(data, initial=initial)


class CompanyUpdateView(CompanyFormMixin, ServiceFormView):
    action = "change"
    model = Company

    def get_object(self):
        company = get_object_or_404(Company, pk=self.kwargs["pk"])
        self.title = f"{company.company_type}: {company}"
        return company

    def get_cancel_url(self) -> str:
        return reverse("orders:form_frmCompanyDetail", kwargs={"pk": self.object.pk})

    def get_form(self, data=None):
        return CompanyForm(data, instance=self.object)


class CompanyDeleteView(ConfirmView):
    """Delete a company with its contacts and vendor-product links; refused while it
    has orders or purchase orders (R-orders-033)."""

    action = "delete"
    model = Company
    title = "Delete company"

    def get_object(self):
        company = get_object_or_404(Company, pk=self.kwargs["pk"])
        self.links = services.company_links(company)
        return company

    def question(self) -> str:
        return (
            f"Delete {self.object}? Its {self.links.contacts} contacts and "
            f"{self.links.vendor_products} vendor-product links are deleted too."
        )

    def refusal(self) -> str | None:
        if not self.links.active:
            return None
        return (
            f"R-orders-033: {self.object} cannot be deleted: it has "
            f"{self.links.customer_orders} orders as customer, "
            f"{self.links.shipper_orders} orders as shipper and "
            f"{self.links.purchase_orders} purchase orders."
        )

    def get_cancel_url(self) -> str:
        return reverse("orders:form_frmCompanyDetail", kwargs={"pk": self.object.pk})

    def perform(self) -> str:
        services.delete_company(self.object, confirmed=True, user=self.request.user)
        messages.success(self.request, "Company deleted.")
        return reverse("orders:form_frmCompanyList")


class CompanyContactsView(AreaAccessMixin, View):
    """sfrmCompanyDetail_Contacts: the company's contacts with the add form."""

    model = Contact
    post_action = "add"
    template_name = "orders/company_contacts.html"

    def render_contacts(self, company, form=None):
        template = self.template_name
        if self.request.htmx:
            template = f"{template}#contacts"
        context = {
            "company": company,
            "contacts": company.contacts.order_by("last_name", "first_name"),
            "contact_form": form or ContactForm(),
        }
        return render(self.request, template, context)

    def get(self, request, pk: int):
        return self.render_contacts(get_object_or_404(Company, pk=pk))

    def post(self, request, pk: int):
        company = get_object_or_404(Company, pk=pk)
        form = ContactForm(request.POST)
        if form.is_valid():
            try:
                services.save_contact(
                    Contact(company=company),
                    form.cleaned_data,
                    user=request.user,
                )
            except ValidationError as error:
                add_service_error(form, error)
            else:
                if not request.htmx:
                    return HttpResponseRedirect(
                        reverse("orders:form_frmCompanyDetail", kwargs={"pk": pk}),
                    )
                form = None
        return self.render_contacts(company, form)


class ContactUpdateView(ServiceFormView):
    action = "change"
    model = Contact
    title = "Contact"

    def get_object(self):
        return get_object_or_404(Contact, pk=self.kwargs["pk"])

    def get_cancel_url(self) -> str:
        return reverse(
            "orders:form_frmCompanyDetail",
            kwargs={"pk": self.object.company_id},
        )

    def get_form(self, data=None):
        return ContactForm(data, instance=self.object)

    def save(self, form) -> str:
        services.save_contact(self.object, form.cleaned_data, user=self.request.user)
        return self.get_cancel_url()


class ContactDeleteView(ConfirmView):
    action = "delete"
    model = Contact
    title = "Delete contact"

    def get_object(self):
        return get_object_or_404(Contact, pk=self.kwargs["pk"])

    def question(self) -> str:
        return f"Delete the contact {self.object}?"

    def get_cancel_url(self) -> str:
        return reverse(
            "orders:form_frmCompanyDetail",
            kwargs={"pk": self.object.company_id},
        )

    def perform(self) -> str:
        services.delete_contact(self.object, user=self.request.user)
        return self.get_cancel_url()


class CompanyOrdersView(AreaAccessMixin, View):
    """sfrmCompanyDetail_CustomerOrders and sfrmCompanyDetail_ShipperOrders: the
    orders of a customer, or the orders a shipper shipped (R-orders-028)."""

    model = Order
    template_name = "orders/company_orders.html"
    partial = "customer-orders"

    def get(self, request, pk: int):
        company = get_object_or_404(Company, pk=pk)
        context = company_orders_context(company)
        return render(request, f"{self.template_name}#{self.partial}", context)


class ShipperOrdersView(CompanyOrdersView):
    partial = "shipper-orders"


# ================================================================ employees


class EmployeeListView(AreaAccessMixin, HtmxPartialMixin, SingleTableMixin, FilterView):
    """frmEmployeeList: employees, last name first (R-orders-043)."""

    model = Employee
    table_class = EmployeeTable
    filterset_class = EmployeeFilter
    template_name = "orders/employee_list.html"
    partial_name = "record-table"
    table_pagination = {"per_page": 25}

    def get_queryset(self):
        return queries.employees()


class EmployeeDetailView(AreaAccessMixin, DetailView):
    """An employee with history (R-orders-032), privileges and recent orders
    (R-orders-027)."""

    model = Employee
    template_name = "orders/employee_detail.html"

    def get_queryset(self):
        return queries.employees().select_related("supervisor", "title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        context.update(
            recent_orders=queries.employee_recent_orders(employee),
            grants=employee.privilege_grants.select_related("privilege"),
        )
        return context


class EmployeeFormMixin:
    template_name = "orders/employee_form.html"

    def get_form(self, data=None):
        initial = {}
        if self.object is None and self.request.GET.get("title"):
            initial["title"] = self.request.GET["title"]
        return EmployeeForm(data, instance=self.object or Employee(), initial=initial)


class EmployeeCreateView(EmployeeFormMixin, ServiceFormView):
    """A new employee; once saved, the privilege screen opens for it
    (R-orders-042)."""

    action = "add"
    model = Employee
    title = "New employee"

    def get_cancel_url(self) -> str:
        return reverse("orders:form_frmEmployeeList")

    def save(self, form) -> str:
        employee = services.save_employee(
            Employee(),
            form.cleaned_data,
            user=self.request.user,
        )
        messages.success(self.request, f"{employee} saved; grant privileges if needed.")
        return reverse(
            "orders:form_sfrmEmployee_Privileges",
            kwargs={"pk": employee.pk},
        )


class EmployeeUpdateView(EmployeeFormMixin, ServiceFormView):
    action = "change"
    model = Employee

    def get_object(self):
        employee = get_object_or_404(Employee, pk=self.kwargs["pk"])
        self.title = str(employee)
        return employee

    def get_cancel_url(self) -> str:
        return reverse("orders:employee_detail", kwargs={"pk": self.object.pk})

    def save(self, form) -> str:
        services.save_employee(self.object, form.cleaned_data, user=self.request.user)
        messages.success(self.request, "Employee saved.")
        return self.get_cancel_url()


class EmployeeDeleteView(ConfirmView):
    """Delete an employee, refused with every reason (R-orders-040)."""

    action = "delete"
    model = Employee
    title = "Delete employee"

    def get_object(self):
        return get_object_or_404(Employee, pk=self.kwargs["pk"])

    def question(self) -> str:
        return f"Delete the employee {self.object}?"

    def refusal(self) -> str | None:
        reasons = services.employee_delete_reasons(self.object)
        if not reasons:
            return None
        return "R-orders-040: the employee cannot be deleted: " + " ".join(reasons)

    def get_cancel_url(self) -> str:
        return reverse("orders:employee_detail", kwargs={"pk": self.object.pk})

    def perform(self) -> str:
        services.delete_employee(self.object, confirmed=True, user=self.request.user)
        messages.success(self.request, "Employee deleted.")
        return reverse("orders:form_frmEmployeeList")


class RecentOrdersView(AreaAccessMixin, View):
    """sfrmOrders_MostRecent_ByEmployee: the employee's orders among the 20 most
    recent orders of all employees (R-orders-027)."""

    model = Order

    def get(self, request, pk: int):
        employee = get_object_or_404(Employee, pk=pk)
        context = {
            "employee": employee,
            "recent_orders": queries.employee_recent_orders(employee),
        }
        return render(request, "orders/employee_detail.html#recent-orders", context)


class EmployeePrivilegesView(AreaAccessMixin, View):
    """sfrmEmployee_Privileges: the employee's privileges, opened after a new
    employee is saved (R-orders-042). The foundation's roles (core/local/roles.py)
    give the matching web permissions."""

    model = EmployeePrivilege
    post_action = "add"
    template_name = "orders/employee_privileges.html"

    def get(self, request, pk: int, form=None):
        employee = get_object_or_404(Employee, pk=pk)
        context = {
            "employee": employee,
            "grants": employee.privilege_grants.select_related("privilege"),
            "form": form or PrivilegeGrantForm(),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk: int):
        employee = get_object_or_404(Employee, pk=pk)
        form = PrivilegeGrantForm(request.POST)
        if not form.is_valid():
            return self.get(request, pk, form=form)
        services.grant_privilege(
            employee,
            form.cleaned_data["privilege"],
            user=request.user,
        )
        return HttpResponseRedirect(
            reverse("orders:form_sfrmEmployee_Privileges", kwargs={"pk": pk}),
        )


class PrivilegeRevokeView(AreaAccessMixin, View):
    model = EmployeePrivilege
    action = "delete"
    http_method_names = ["post"]

    def post(self, request, pk: int):
        grant = get_object_or_404(EmployeePrivilege, pk=pk)
        employee_id = grant.employee_id
        services.revoke_privilege(grant, user=request.user)
        return HttpResponseRedirect(
            reverse("orders:form_sfrmEmployee_Privileges", kwargs={"pk": employee_id}),
        )


class TitleCreateView(ServiceFormView):
    """frmEmployeeTitles: add a title to the titles list, pre-filled with the typed
    value (R-orders-044)."""

    action = "add"
    model = Title
    title = "New title"

    def get_cancel_url(self) -> str:
        return safe_next(self.request, reverse("orders:form_frmEmployeeList"))

    def get_form(self, data=None):
        return TitleForm(data, initial={"title": self.request.GET.get("title", "")})

    def get_context(self, form, **extra):
        context = super().get_context(form, **extra)
        context["next"] = self.get_cancel_url()
        return context

    def save(self, form) -> str:
        title = services.add_title(
            form.cleaned_data.get("title"),
            user=self.request.user,
        )
        messages.success(self.request, f"Title {title} added.")
        return self.get_cancel_url()


class CredentialsView(AreaAccessMixin, TemplateView):
    """frmCredentials: the employee record the signed-in user works as. Accounts
    themselves are the foundation's (sign-in and user admin)."""

    model = Employee
    template_name = "orders/credentials.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["employee"] = signed_in_employee(self.request.user)
        return context
