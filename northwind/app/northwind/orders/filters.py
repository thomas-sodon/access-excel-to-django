"""django-filter filter sets of the Orders, Invoicing and Shipping area."""

from __future__ import annotations

import django_filters
from django.db.models import Q

from northwind.legacy.models import Company
from northwind.legacy.models import Employee
from northwind.legacy.models import Order

from . import services


def _search_number(value: str) -> int | None:
    text = value.strip()
    return int(text) if text.isdigit() else None


class OrderFilter(django_filters.FilterSet):
    """The order list's filters (R-orders-025) and a search on customer or order
    number."""

    show = django_filters.ChoiceFilter(
        label="Show",
        choices=[(key, label) for key, label in services.ORDER_FILTERS],
        empty_label=None,
        method="filter_show",
    )
    q = django_filters.CharFilter(label="Search", method="search")

    class Meta:
        model = Order
        fields = ()

    def filter_show(self, queryset, name, value):
        user = getattr(self.request, "user", None)
        return services.filter_order_list(queryset, value, user=user)

    def search(self, queryset, name, value):
        number = _search_number(value)
        match = Q(customer__company_name__icontains=value.strip())
        if number is not None:
            match |= Q(pk=number)
        return queryset.filter(match)


class CompanyFilter(django_filters.FilterSet):
    """The company list's filter: Customers, Shippers, Vendors or all companies
    (R-orders-037), and a search on the name."""

    show = django_filters.ChoiceFilter(
        label="Show",
        choices=[(key, heading) for key, heading, _type in services.COMPANY_FILTERS],
        empty_label=None,
        method="filter_show",
    )
    q = django_filters.CharFilter(label="Search", method="search")

    class Meta:
        model = Company
        fields = ()

    def filter_show(self, queryset, name, value):
        return services.filter_company_list(queryset, value)

    def search(self, queryset, name, value):
        return queryset.filter(company_name__icontains=value.strip())


class EmployeeFilter(django_filters.FilterSet):
    """A search on the employee list."""

    q = django_filters.CharFilter(label="Search", method="search")

    class Meta:
        model = Employee
        fields = ()

    def search(self, queryset, name, value):
        text = value.strip()
        return queryset.filter(
            Q(first_name__icontains=text)
            | Q(last_name__icontains=text)
            | Q(job_title__icontains=text),
        )
