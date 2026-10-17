"""django-tables2 tables of the Orders, Invoicing and Shipping area."""

from __future__ import annotations

import django_tables2 as tables

from .templatetags.orders_tags import money
from .templatetags.orders_tags import phone

ATTRS = {"class": "table table-sm table-striped"}


class MoneyColumn(tables.Column):
    def render(self, value):
        return money(value)


class DateColumn(tables.DateTimeColumn):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("format", "n/j/Y")
        super().__init__(*args, **kwargs)


class OrderTable(tables.Table):
    """The order list (R-orders-024): the number opens the order screen
    (R-orders-029)."""

    order_id = tables.Column(
        verbose_name="Order #",
        linkify=("orders:form_frmOrderDetails", {"pk": tables.A("pk")}),
    )
    order_date = DateColumn(verbose_name="Order date")
    company_name = tables.Column(verbose_name="Customer")
    full_name_fnln = tables.Column(verbose_name="Salesperson")
    order_total = MoneyColumn(verbose_name="Total", attrs={"td": {"class": "text-end"}})
    order_status_name = tables.Column(verbose_name="Status")
    order_detail_status_name = tables.Column(verbose_name="Line status")

    class Meta:
        attrs = ATTRS
        order_by = ("-order_id",)


class CompanyTable(tables.Table):
    """The read-only company list (R-orders-037, R-orders-039)."""

    company_id = tables.Column(
        verbose_name="ID",
        linkify=("orders:form_frmCompanyDetail", {"pk": tables.A("pk")}),
    )
    company_name = tables.Column(verbose_name="Company")
    company_type_name = tables.Column(verbose_name="Type")
    business_phone = tables.Column(verbose_name="Phone")
    business_address = tables.Column(verbose_name="Address")
    tax_status_name = tables.Column(verbose_name="Standard tax status")

    class Meta:
        attrs = ATTRS
        order_by = ("company_name",)

    def render_business_phone(self, value):
        return phone(value)


class EmployeeTable(tables.Table):
    """The employee list, last name first (R-orders-043)."""

    employee_id = tables.Column(
        verbose_name="ID",
        linkify=("orders:employee_detail", {"pk": tables.A("pk")}),
    )
    full_name_lnfn = tables.Column(verbose_name="Name")
    job_title = tables.Column(verbose_name="Job title")
    email_address = tables.Column(verbose_name="E-mail")
    primary_phone = tables.Column(verbose_name="Phone")

    class Meta:
        attrs = ATTRS
        order_by = ("full_name_lnfn",)

    def render_primary_phone(self, value):
        return phone(value)
