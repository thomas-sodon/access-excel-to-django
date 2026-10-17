"""django-filter filter sets of the Purchasing and receiving area."""

import django_filters
from django.db.models import Q

from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderStatus

from . import queries


class PurchaseOrderListFilter(django_filters.FilterSet):
    """Search and filters of the purchase order list: a search on the number or the
    vendor name, the status and the vendor. The list starts unfiltered."""

    search = django_filters.CharFilter(
        method="filter_search",
        label="Search (PO number or vendor)",
    )
    status = django_filters.ModelChoiceFilter(
        queryset=PurchaseOrderStatus.objects.order_by("sort_order"),
        label="Status",
    )
    vendor = django_filters.ModelChoiceFilter(
        queryset=queries.vendors(),
        label="Vendor",
    )

    class Meta:
        model = PurchaseOrder
        fields = ("search", "status", "vendor")

    def filter_search(self, queryset, name, value):
        value = (value or "").strip()
        if not value:
            return queryset
        condition = Q(vendor__company_name__icontains=value)
        if value.isdigit():
            condition |= Q(purchase_order_id=int(value))
        return queryset.filter(condition)
