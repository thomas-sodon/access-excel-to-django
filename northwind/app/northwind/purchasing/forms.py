"""Forms of the Purchasing and receiving area (crispy-forms, Bootstrap 5).

The forms only collect values; the services check the rules and save.
"""

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.urls import reverse

from northwind.legacy.choices import PaymentMethod
from northwind.legacy.models import Company
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail

from . import queries
from . import services

DATETIME_INPUT = forms.DateTimeInput(
    attrs={"type": "datetime-local", "step": "1"},
    format="%Y-%m-%dT%H:%M:%S",
)


def _helper(label: str = "Save", *, form_tag: bool = True) -> FormHelper:
    helper = FormHelper()
    helper.form_tag = form_tag
    if form_tag:
        helper.add_input(Submit("save", label))
    return helper


class PurchaseOrderForm(forms.ModelForm):
    """The purchase order header (frmPurchaseOrderDetails). Only the fields that are
    still editable in the current status are on the form (R-purchasing-011): the
    vendor and notes on a new purchase order (R-purchasing-015), then the notes,
    the received date while Approved and the shipping fee and payment method while
    Received."""

    class Meta:
        model = PurchaseOrder
        fields = ("vendor", "notes", "received_date", "shipping_fee", "payment_method")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "received_date": DATETIME_INPUT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        keep = services.editable_fields(self.instance)
        for name in list(self.fields):
            if name not in keep:
                del self.fields[name]
        if "vendor" in self.fields:
            # R-purchasing-017: the vendor companies, by name.
            self.fields["vendor"].queryset = queries.vendors()
            self.fields["vendor"].empty_label = "Choose a vendor"
        if "payment_method" in self.fields:
            self.fields["payment_method"] = forms.ChoiceField(
                choices=[("", "---------"), *PaymentMethod.choices],
                required=False,
                initial=self.instance.payment_method,
            )
        if "received_date" in self.fields:
            self.fields["received_date"].input_formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
            ]
        self.helper = _helper()

    def _post_clean(self):
        # The services validate and save; do not copy values onto the instance.
        pass


class CloseForm(forms.Form):
    """The close action (R-purchasing-009): shipping fee and payment method."""

    shipping_fee = forms.DecimalField(
        max_digits=19,
        decimal_places=4,
        required=False,
        label="Shipping fee",
    )
    payment_method = forms.ChoiceField(
        choices=[("", "---------"), *PaymentMethod.choices],
        required=False,
        label="Payment method",
    )

    def __init__(self, *args, purchase_order=None, **kwargs):
        if purchase_order is not None:
            kwargs.setdefault(
                "initial",
                {
                    "shipping_fee": purchase_order.shipping_fee,
                    "payment_method": purchase_order.payment_method,
                },
            )
        super().__init__(*args, **kwargs)
        self.helper = _helper("Close purchase order")
        if purchase_order is not None:
            self.helper.form_action = reverse(
                "purchasing:close",
                kwargs={"pk": purchase_order.pk},
            )


class ReceiveForm(forms.Form):
    """The receive action (R-purchasing-007): posting to inventory is confirmed."""

    confirm = forms.BooleanField(
        required=False,
        label="Post this purchase order to inventory (the whole order is received)",
    )

    def __init__(self, *args, purchase_order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _helper("Receive purchase order")
        if purchase_order is not None:
            self.helper.form_action = reverse(
                "purchasing:receive",
                kwargs={"pk": purchase_order.pk},
            )


class LineForm(forms.ModelForm):
    """A purchase order line (sfrmPurchaseOrderLineItems). The product choices are
    the products the purchase order's vendor supplies, by name (R-purchasing-016);
    choosing one fills in the quantity and unit cost (R-purchasing-018)."""

    class Meta:
        model = PurchaseOrderDetail
        fields = ("product", "quantity", "unit_cost")

    def __init__(self, *args, purchase_order=None, **kwargs):
        super().__init__(*args, **kwargs)
        po = purchase_order or getattr(self.instance, "purchase_order", None)
        vendor_id = getattr(po, "vendor_id", None)
        self.fields["product"].queryset = queries.vendor_products(vendor_id)
        if po is not None and po.pk is not None and self.instance.pk is None:
            # HTMX: choosing a product reloads the new-line form with its defaults.
            self.fields["product"].widget.attrs.update(
                {
                    "hx-get": reverse("purchasing:line_defaults", kwargs={"pk": po.pk}),
                    "hx-target": "#line-form",
                    "hx-swap": "outerHTML",
                    "hx-trigger": "change",
                },
            )
        for name in self.fields:
            self.fields[name].required = False
        self.helper = _helper(form_tag=False)

    def _post_clean(self):
        # The services validate and save; do not copy values onto the instance.
        pass


class VendorChoiceForm(forms.Form):
    """The vendor dialog (frmSelectVendorDialog, R-purchasing-023)."""

    vendor = forms.ModelChoiceField(
        queryset=Company.objects.none(),
        required=False,
        widget=forms.RadioSelect,
        label="Vendor",
    )

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if product is not None:
            self.fields["vendor"].queryset = queries.product_vendors(product)
        self.helper = _helper(form_tag=False)
