"""Forms of the Products and Inventory area (crispy-forms, Bootstrap 5).

The forms only collect input; the rules are checked by the services they are saved
through (services.py), so a refusal names its rule wherever it comes from.
"""

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.models import Company
from northwind.legacy.models import Product
from northwind.legacy.models import ProductCategory

from . import queries
from .services import FORM_FIELDS


def _helper(label: str = "Save") -> FormHelper:
    helper = FormHelper()
    helper.add_input(Submit("save", label))
    return helper


class ProductForm(forms.ModelForm):
    """frmProductDetail: create and edit a product; saved through
    services.save_product (R-inventory-012, R-inventory-013)."""

    class Meta:
        model = Product
        fields = FORM_FIELDS
        widgets = {"product_description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product_category"].queryset = queries.categories_by_name()
        self.helper = _helper()


class CategoryForm(forms.ModelForm):
    """sfrmProductCategories: create and edit a category; saved through
    services.save_category (R-inventory-014)."""

    class Meta:
        model = ProductCategory
        fields = (
            "product_category_name",
            "product_category_code",
            "product_category_desc",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _helper()


class StockTakeForm(forms.Form):
    """sfrmProductDetail_StockTake: the counted quantity of a new stock take; the
    date and the expected quantity are set by the system (R-inventory-009).
    `confirmed_quantity` carries the count the user confirmed after seeing that it
    differs from the expected quantity (R-inventory-010); a changed count needs a new
    confirmation."""

    quantity_on_hand = forms.IntegerField(label="Counted quantity on hand", min_value=0)
    confirmed_quantity = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _helper("Record stock take")

    @property
    def confirmed(self) -> bool:
        data = self.cleaned_data
        return data.get("confirmed_quantity") == data.get("quantity_on_hand")


class VendorLinkForm(forms.Form):
    """sfrmProductDetail_Vendors: link a vendor to the product (R-inventory-029)."""

    vendor = forms.ModelChoiceField(
        label="Vendor",
        queryset=Company.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Company.objects.filter(
            company_type_id=CompanyTypeCode.VENDOR,
        ).order_by("company_name", "pk")
        self.helper = _helper("Add vendor")


class ReorderForm(forms.Form):
    """The reorder dialog: the vendor when several are linked (R-inventory-018) and
    the quantity when no suggested or minimum quantity applies (R-inventory-019)."""

    vendor = forms.ModelChoiceField(
        label="Vendor",
        queryset=Company.objects.none(),
        required=False,
    )
    quantity = forms.IntegerField(label="Quantity", min_value=1, required=False)

    def __init__(self, *args, vendors=(), needs=None, **kwargs):
        super().__init__(*args, **kwargs)
        needs = needs or {}
        self.fields["vendor"].queryset = Company.objects.filter(
            pk__in=[vendor.pk for vendor in vendors],
        ).order_by("company_name", "pk")
        if not needs.get("vendor"):
            del self.fields["vendor"]
        if not needs.get("quantity"):
            del self.fields["quantity"]
        self.helper = _helper("Reorder")


class ConfirmForm(forms.Form):
    """A delete confirmation (R-inventory-016)."""

    confirmed = forms.BooleanField(label="Yes, delete it", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _helper("Delete")
