"""Forms of the Orders, Invoicing and Shipping area (crispy-forms, Bootstrap 5).

The forms only collect values. Every rule, required fields included, is checked by
the service the view calls, so a refusal names its rule id (services.py); that is why
the model forms skip Django's model validation and mark no field required.
"""

from __future__ import annotations

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.forms import modelform_factory

from northwind.legacy.choices import PaymentMethod
from northwind.legacy.models import Company
from northwind.legacy.models import Contact
from northwind.legacy.models import Employee
from northwind.legacy.models import Order
from northwind.legacy.models import Privilege
from northwind.legacy.models import ProductCategory
from northwind.legacy.models import TaxStatus
from northwind.legacy.models import Title

from . import queries
from . import services

DATETIME_FORMATS = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%dT%H:%M")


def datetime_field(label: str) -> forms.DateTimeField:
    return forms.DateTimeField(
        label=label,
        required=False,
        widget=DateTimeInput(),
        input_formats=DATETIME_FORMATS,
    )


def helper(label: str = "Save", *, form_tag: bool = True) -> FormHelper:
    form_helper = FormHelper()
    form_helper.form_tag = form_tag
    if form_tag:
        form_helper.add_input(Submit("save", label))
    return form_helper


class ServiceModelForm(forms.ModelForm):
    """A model form that leaves every check to the area's services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.helper = helper()

    def _post_clean(self):
        """Skip the model's own validation: the service checks the rules and names
        them (services.check_required, check_unique)."""


# ---------------------------------------------------------------- orders


class OrderForm(ServiceModelForm):
    """The order header. Its fields are the ones the order's status leaves editable
    (R-orders-014, services.editable_order_fields)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, label in (
            ("shipped_date", "Shipped date"),
            ("paid_date", "Paid date"),
        ):
            if name in self.fields:
                self.fields[name] = datetime_field(label)
        choices = {
            "customer": queries.customers(),
            "employee": queries.employee_choices(),
            "shipper": queries.shippers(),
            "tax_status": TaxStatus.objects.order_by("tax_status_id"),
        }
        for name, queryset in choices.items():
            if name in self.fields:
                self.fields[name].queryset = queryset
        if "employee" in self.fields:
            self.fields["employee"].label = "Salesperson"


def order_form_class(order: Order) -> type[OrderForm]:
    """The order form with exactly the fields editable in the order's status."""
    return modelform_factory(
        Order,
        form=OrderForm,
        fields=services.editable_order_fields(order),
    )


class OrderLineForm(forms.Form):
    """One order line: the product list can be narrowed to a category
    (R-orders-008)."""

    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.order_by("product_category_name"),
        required=False,
        empty_label="All products",
    )
    product = forms.ModelChoiceField(queryset=None, required=False)
    quantity = forms.IntegerField(required=False)
    discount = forms.FloatField(required=False, initial=0)

    def __init__(self, *args, category=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = services.product_choices(category)
        self.helper = helper(form_tag=False)


class ShipForm(forms.Form):
    """Shipping an Invoiced order (R-orders-016)."""

    shipped_date = datetime_field("Shipped date")
    shipper = forms.ModelChoiceField(queryset=Company.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shipper"].queryset = queries.shippers()
        self.helper = helper(form_tag=False)


class PaymentForm(forms.Form):
    """Receiving payment for a Shipped order (R-orders-017)."""

    payment_method = forms.ChoiceField(
        choices=[("", "---------"), *PaymentMethod.choices],
        required=False,
    )
    paid_date = datetime_field("Paid date")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = helper(form_tag=False)


# ---------------------------------------------------------------- companies

PHONE_HELP = (
    "Ten digits (3-3-4), optionally followed by an extension of up to 8 characters."
)


def phone_field(label: str) -> forms.CharField:
    return forms.CharField(
        label=label,
        max_length=30,
        required=False,
        help_text=PHONE_HELP,
    )


class CompanyForm(ServiceModelForm):
    """The company screen (R-orders-034, R-orders-036, R-orders-045, R-orders-048)."""

    business_phone = phone_field("Business phone")

    class Meta:
        model = Company
        fields = (
            "company_name",
            "company_type",
            "business_phone",
            "address",
            "city",
            "state",
            "zip",
            "website",
            "notes",
            "standard_tax_status",
        )


class ContactForm(ServiceModelForm):
    """A contact of a company (sfrmCompanyDetail_Contacts)."""

    primary_phone = phone_field("Primary phone")
    secondary_phone = phone_field("Secondary phone")

    class Meta:
        model = Contact
        fields = (
            "first_name",
            "last_name",
            "job_title",
            "email_address",
            "primary_phone",
            "secondary_phone",
            "notes",
        )


# ---------------------------------------------------------------- employees


class EmployeeForm(ServiceModelForm):
    """The employee screen: the supervisor list leaves out the employee being edited
    (R-orders-041); titles come from the titles list (R-orders-044)."""

    primary_phone = phone_field("Primary phone")
    secondary_phone = phone_field("Secondary phone")

    class Meta:
        model = Employee
        fields = (
            "title",
            "first_name",
            "last_name",
            "job_title",
            "email_address",
            "primary_phone",
            "secondary_phone",
            "supervisor",
            "windows_user_name",
            "notes",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].queryset = Title.objects.order_by("title")
        self.fields["supervisor"].queryset = services.supervisor_choices(self.instance)


class TitleForm(forms.Form):
    """The small title-entry screen (frmEmployeeTitles, R-orders-044)."""

    title = forms.CharField(max_length=20, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = helper("Add title")


class PrivilegeGrantForm(forms.Form):
    """Granting a privilege to an employee (sfrmEmployee_Privileges)."""

    privilege = forms.ModelChoiceField(
        queryset=Privilege.objects.order_by("privilege_name"),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = helper("Grant")
