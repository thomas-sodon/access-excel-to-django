"""django-filter filter sets of the Products and Inventory area."""

import django_filters
from django.db.models import Q

from northwind.legacy.models import Product

from . import queries


class ProductFilter(django_filters.FilterSet):
    """The product list's search and filters: name or code, category, discontinued."""

    search = django_filters.CharFilter(
        label="Search",
        method="filter_search",
    )
    product_category = django_filters.ModelChoiceFilter(
        label="Category",
        queryset=queries.categories_by_name(),
    )
    discontinued = django_filters.BooleanFilter(label="Discontinued")

    class Meta:
        model = Product
        fields = ("search", "product_category", "discontinued")

    def filter_search(self, queryset, name, value):
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(product_name__icontains=value) | Q(product_code__icontains=value),
        )
