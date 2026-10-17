"""Screens of the Products and Inventory area (keep-drop.md: inventory.views).

- frmProductList: the product list with search, filters and the stock figures, an
  HTMX table partial and the .xlsx download (R-inventory-023, R-inventory-024).
- frmProductDetail: the product page with its levels (R-inventory-021,
  R-inventory-022), create, edit, delete (R-inventory-016) and reorder
  (R-inventory-017 to R-inventory-020), and its panels, each its own URL that HTMX
  loads into the page: sfrmProductDetail_Orders, sfrmProductDetail_PurchaseOrders,
  sfrmProductDetail_StockTake (R-inventory-008 to R-inventory-011) and
  sfrmProductDetail_Vendors (R-inventory-029).
- sfrmProductCategories: the categories (R-inventory-014, R-inventory-015).

Every view signs in first (anonymous users go to the sign-in page) and then checks
the role: the roles of core/local/roles.py are Django groups with permissions, so a
user passes when one of their groups grants the view's permission and gets 403
otherwise. Writes go through services.py.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import UpdateView
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from django_filters.views import FilterView
from django_tables2 import RequestConfig
from django_tables2 import SingleTableMixin
from django_tables2 import SingleTableView

from northwind.legacy.models import Product
from northwind.legacy.models import ProductCategory
from northwind.legacy.models import ProductVendor

from . import queries
from . import services
from .filters import ProductFilter
from .forms import CategoryForm
from .forms import ConfirmForm
from .forms import ProductForm
from .forms import ReorderForm
from .forms import StockTakeForm
from .forms import VendorLinkForm
from .links import other_area_url
from .reports import product_list_export
from .tables import CategoryTable
from .tables import ProductOrderTable
from .tables import ProductPurchaseOrderTable
from .tables import ProductTable
from .tables import StockTakeTable


class InventoryAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Sign-in, then the role check: `permission_required` for reading and, when
    set, `post_permission` for a POST."""

    permission_required: tuple[str, ...] = ("legacy.view_product",)
    post_permission: str | None = None

    def get_permission_required(self):
        if self.request.method == "POST" and self.post_permission:
            return (self.post_permission,)
        return tuple(self.permission_required)


def _refusal(form, error: ValidationError) -> None:
    form.add_error(None, error)


# ---------------------------------------------------------------- frmProductList


class ProductListView(InventoryAccessMixin, SingleTableMixin, FilterView):
    """frmProductList; an HTMX request gets only the table partial."""

    model = Product
    table_class = ProductTable
    filterset_class = ProductFilter
    template_name = "inventory/product_list.html"
    table_pagination = {"per_page": 25}

    def get_queryset(self):
        return queries.product_list()

    def get_template_names(self):
        if self.request.htmx:
            return [f"{self.template_name}#product-table"]
        return [self.template_name]


class ProductExportView(InventoryAccessMixin, View):
    """The product list as an .xlsx download (R-inventory-024)."""

    def get(self, request, *args, **kwargs):
        response = HttpResponse(
            product_list_export.workbook_bytes(),
            content_type=product_list_export.XLSX_CONTENT_TYPE,
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{product_list_export.FILENAME}"'
        )
        return response


# ---------------------------------------------------------------- frmProductDetail


class ProductDetailView(InventoryAccessMixin, DetailView):
    """frmProductDetail: the product, its levels and its panels. `?find=<id>` jumps
    to another product (the original's find-product box)."""

    model = Product
    template_name = "inventory/product_detail.html"

    def get(self, request, *args, **kwargs):
        target = request.GET.get("find", "").strip()
        if target.isdigit():
            found = Product.objects.filter(pk=int(target)).first()
            if found is not None:
                return redirect("inventory:form_frmProductDetail", pk=found.pk)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Product.objects.select_related("product_category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        levels = services.product_stock_levels(self.object)
        context.update(
            levels=levels,
            attention=services.needs_reorder_attention(self.object, levels),
            actions=services.product_actions(self.object),
            find_choices=queries.all_products_by_name().values_list(
                "pk",
                "product_name",
            ),
        )
        return context


class ProductFormMixin:
    """Save through services.save_product; a refused save shows its message."""

    model = Product
    form_class = ProductForm
    template_name = "inventory/product_form.html"

    def form_valid(self, form):
        try:
            self.object = services.save_product(
                form.instance,
                form.cleaned_data,
                user=self.request.user,
            )
        except ValidationError as error:
            _refusal(form, error)
            return self.form_invalid(form)
        messages.success(self.request, f"Saved {self.object.product_code}.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("inventory:form_frmProductDetail", kwargs={"pk": self.object.pk})


class ProductCreateView(InventoryAccessMixin, ProductFormMixin, CreateView):
    """A new product shows zero levels and no history or actions (R-inventory-022)."""

    permission_required = ("legacy.add_product",)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = Product()
        context.update(
            levels=services.product_stock_levels(product),
            actions=services.product_actions(product),
        )
        return context


class ProductUpdateView(InventoryAccessMixin, ProductFormMixin, UpdateView):
    permission_required = ("legacy.change_product",)


class ProductDeleteView(InventoryAccessMixin, SingleObjectMixin, FormView):
    """Delete a product after confirmation (R-inventory-016)."""

    model = Product
    form_class = ConfirmForm
    template_name = "inventory/confirm_delete.html"
    permission_required = ("legacy.delete_product",)

    def dispatch(self, request, *args, **kwargs):
        self.object = None
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if self.object is None:
            self.object = super().get_object(queryset)
        return self.object

    def get_context_data(self, **kwargs):
        self.get_object()
        kwargs.setdefault("cancel_url", self.success_cancel_url())
        return super().get_context_data(**kwargs)

    def success_cancel_url(self) -> str:
        return reverse(
            "inventory:form_frmProductDetail",
            kwargs={"pk": self.get_object().pk},
        )

    def form_valid(self, form):
        product = self.get_object()
        try:
            services.delete_product(
                product,
                confirmed=form.cleaned_data["confirmed"],
                user=self.request.user,
            )
        except ValidationError as error:
            _refusal(form, error)
            return self.form_invalid(form)
        messages.success(self.request, f"Deleted {product.product_name}.")
        return redirect("inventory:form_frmProductList")


class ProductReorderView(InventoryAccessMixin, SingleObjectMixin, FormView):
    """Reorder a product (R-inventory-017 to R-inventory-021): asks for the vendor
    among several and for a quantity when no suggested or minimum quantity applies."""

    model = Product
    form_class = ReorderForm
    template_name = "inventory/reorder.html"
    permission_required = ("legacy.add_purchaseorderdetail",)

    def dispatch(self, request, *args, **kwargs):
        self.object = None
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if self.object is None:
            self.object = super().get_object(queryset)
        return self.object

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        product = self.get_object()
        kwargs.update(
            vendors=services.linked_vendors(product),
            needs=services.reorder_needs(product),
        )
        return kwargs

    def get_context_data(self, **kwargs):
        product = self.get_object()
        outstanding = services.outstanding_purchase_order(product)
        kwargs.update(
            levels=services.product_stock_levels(product),
            actions=services.product_actions(product),
            vendors=services.linked_vendors(product),
            outstanding=outstanding,
            outstanding_url=outstanding
            and other_area_url(
                "purchasing:form_frmPurchaseOrderDetails",
                outstanding.pk,
            ),
        )
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        product = self.get_object()
        try:
            result = services.reorder_product(
                product,
                vendor=form.cleaned_data.get("vendor"),
                quantity=form.cleaned_data.get("quantity"),
                user=self.request.user,
            )
        except ValidationError as error:
            _refusal(form, error)
            return self.form_invalid(form)
        number = result.purchase_order.pk
        if result.opened_existing:
            messages.info(
                self.request,
                f"The product is already on order: purchase order {number}.",
            )
        else:
            messages.success(
                self.request,
                f"Added {result.quantity} to purchase order {number}.",
            )
        target = other_area_url("purchasing:form_frmPurchaseOrderDetails", number)
        return HttpResponseRedirect(
            target
            or reverse("inventory:form_frmProductDetail", kwargs={"pk": product.pk}),
        )


# ---------------------------------------------------------------- product panels


class ProductPanelView(InventoryAccessMixin, SingleObjectMixin, View):
    """One panel of the product page; the page loads it with HTMX (the `panel`
    partial), and without HTMX it is a page of its own."""

    model = Product
    template_name = ""
    table_class = None

    def get_table(self):
        return None

    def get_template_names(self):
        if self.request.htmx:
            return [f"{self.template_name}#panel"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table = self.get_table()
        if table is not None:
            RequestConfig(self.request, paginate={"per_page": 25}).configure(table)
        context.update(
            table=table,
            panel_url=self.request.path,
            actions=services.product_actions(self.object),
        )
        return context

    def render(self, **kwargs):
        return TemplateResponse(
            self.request,
            self.get_template_names(),
            self.get_context_data(**kwargs),
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render()


class ProductOrdersView(ProductPanelView):
    """sfrmProductDetail_Orders: the product's order history (R-inventory-025)."""

    template_name = "inventory/product_orders.html"
    permission_required = ("legacy.view_orderdetail",)

    def get_table(self):
        return ProductOrderTable(queries.product_orders(self.object))


class ProductPurchaseOrdersView(ProductPanelView):
    """sfrmProductDetail_PurchaseOrders: the product's purchase-order history
    (R-inventory-026)."""

    template_name = "inventory/product_purchase_orders.html"
    permission_required = ("legacy.view_purchaseorderdetail",)

    def get_table(self):
        return ProductPurchaseOrderTable(queries.product_purchase_orders(self.object))


class StockTakeView(ProductPanelView):
    """sfrmProductDetail_StockTake: the stock takes, read-only, and a form that adds
    one (R-inventory-009 to R-inventory-011). A count that differs from the expected
    quantity is shown with both figures and saved only when confirmed; cancelling
    discards it."""

    template_name = "inventory/product_stock_takes.html"
    permission_required = ("legacy.view_stocktake",)
    post_permission = "legacy.add_stocktake"

    def get_table(self):
        return StockTakeTable(queries.stock_takes(self.object))

    def get_context_data(self, **kwargs):
        kwargs.setdefault("form", StockTakeForm())
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = StockTakeForm(request.POST)
        if not form.is_valid():
            return self.render(form=form)
        try:
            result = services.record_stock_take(
                self.object,
                form.cleaned_data["quantity_on_hand"],
                confirmed=form.confirmed,
                user=request.user,
            )
        except services.StockTakeMismatchError as mismatch:
            confirm = StockTakeForm(
                initial={
                    "quantity_on_hand": mismatch.counted,
                    "confirmed_quantity": mismatch.counted,
                },
            )
            return self.render(form=confirm, mismatch=mismatch)
        except ValidationError as error:
            _refusal(form, error)
            return self.render(form=form)
        messages.success(
            request,
            f"Stock take recorded: counted {result.stock_take.quantity_on_hand}, "
            f"expected {result.expected}.",
        )
        return redirect("inventory:form_sfrmProductDetail_StockTake", pk=self.object.pk)


class VendorsView(ProductPanelView):
    """sfrmProductDetail_Vendors: the product's vendors and a form that links one
    (R-inventory-029)."""

    template_name = "inventory/product_vendors.html"
    permission_required = ("legacy.view_productvendor",)
    post_permission = "legacy.add_productvendor"

    def get_context_data(self, **kwargs):
        kwargs.setdefault("form", VendorLinkForm())
        links = list(queries.product_vendors(self.object))
        for link in links:
            link.company_url = other_area_url(
                "orders:form_frmCompanyDetail",
                link.vendor_id,
            )
        kwargs["links"] = links
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = VendorLinkForm(request.POST)
        if not form.is_valid():
            return self.render(form=form)
        try:
            services.add_product_vendor(
                self.object,
                form.cleaned_data["vendor"],
                user=request.user,
            )
        except ValidationError as error:
            _refusal(form, error)
            return self.render(form=form)
        messages.success(request, "Vendor linked.")
        return redirect("inventory:form_sfrmProductDetail_Vendors", pk=self.object.pk)


class VendorRemoveView(InventoryAccessMixin, View):
    """Remove one vendor link after confirmation."""

    permission_required = ("legacy.delete_productvendor",)

    def link(self) -> ProductVendor:
        return get_object_or_404(
            ProductVendor.objects.select_related("product", "vendor"),
            pk=self.kwargs["link"],
            product_id=self.kwargs["pk"],
        )

    def get(self, request, *args, **kwargs):
        link = self.link()
        return TemplateResponse(
            request,
            "inventory/confirm_delete.html",
            {
                "object": link,
                "form": ConfirmForm(),
                "cancel_url": reverse(
                    "inventory:form_frmProductDetail",
                    kwargs={"pk": link.product_id},
                ),
            },
        )

    def post(self, request, *args, **kwargs):
        link = self.link()
        if ConfirmForm(request.POST).is_valid():
            services.remove_product_vendor(link, user=request.user)
            messages.success(request, "Vendor link removed.")
        return redirect("inventory:form_frmProductDetail", pk=link.product_id)


# ---------------------------------------------------------------- categories


class CategoryListView(InventoryAccessMixin, SingleTableView):
    """sfrmProductCategories: the product categories."""

    model = ProductCategory
    table_class = CategoryTable
    template_name = "inventory/category_list.html"
    permission_required = ("legacy.view_productcategory",)
    table_pagination = {"per_page": 50}

    def get_queryset(self):
        return queries.categories_by_name()


class CategoryFormMixin:
    """Save through services.save_category (R-inventory-014)."""

    model = ProductCategory
    form_class = CategoryForm
    template_name = "inventory/form.html"

    def form_valid(self, form):
        try:
            self.object = services.save_category(
                form.instance,
                form.cleaned_data,
                user=self.request.user,
            )
        except ValidationError as error:
            _refusal(form, error)
            return self.form_invalid(form)
        messages.success(self.request, f"Saved {self.object}.")
        return redirect("inventory:form_sfrmProductCategories")


class CategoryCreateView(InventoryAccessMixin, CategoryFormMixin, CreateView):
    permission_required = ("legacy.add_productcategory",)


class CategoryUpdateView(InventoryAccessMixin, CategoryFormMixin, UpdateView):
    permission_required = ("legacy.change_productcategory",)


class CategoryDeleteView(InventoryAccessMixin, SingleObjectMixin, FormView):
    """Delete a category; refused while products belong to it (R-inventory-015)."""

    model = ProductCategory
    form_class = ConfirmForm
    template_name = "inventory/confirm_delete.html"
    permission_required = ("legacy.delete_productcategory",)

    def dispatch(self, request, *args, **kwargs):
        self.object = None
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if self.object is None:
            self.object = super().get_object(queryset)
        return self.object

    def get_context_data(self, **kwargs):
        self.get_object()
        kwargs.setdefault("cancel_url", reverse("inventory:form_sfrmProductCategories"))
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        category = self.get_object()
        try:
            services.delete_category(category, user=self.request.user)
        except ValidationError as error:
            _refusal(form, error)
            return self.form_invalid(form)
        messages.success(self.request, f"Deleted {category}.")
        return redirect("inventory:form_sfrmProductCategories")
