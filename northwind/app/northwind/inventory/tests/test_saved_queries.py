"""Every unit the area registers runs on seed 1 (core.testing load_seed) and returns
rows with the manifest's number of columns. The values themselves are checked by the
equivalence harness against the goldens, never here.
"""

import pytest

from northwind.core.saved_queries import SAVED_QUERIES
from northwind.core.saved_queries import run_saved_query
from northwind.legacy.models import Product

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.inventory import saved_queries

pytestmark = pytest.mark.django_db

#: Unit id -> number of output columns (goldens/manifest.json, area inventory).
COLUMNS = {
    "qryPOProducts_ByStatus": 3,
    "qryProductCategories": 9,
    "qryProductDetail": 16,
    "qryProductList": 21,
    "qryProductList_Export": 10,
    "qryProductOrders": 8,
    "qryProductPurchaseOrder": 11,
    "qryProductVendors": 7,
    "qryStockTake": 5,
    "qrycboProductCategories": 3,
    "qrycboProductCategory": 2,
    "qrycboProducts": 4,
    "qrycboProducts_All": 4,
}


def test_the_area_registers_exactly_its_units():
    registered = {
        unit
        for unit, fn in SAVED_QUERIES.items()
        if fn.__module__ == saved_queries.__name__
    }
    assert registered == set(COLUMNS)


@pytest.mark.parametrize("unit", sorted(COLUMNS))
def test_unit_runs_on_seed_1(load_seed, unit):
    load_seed(1)
    params = {}
    if unit == "qrycboProducts":
        category = Product.objects.order_by("pk").values_list(
            "product_category_id",
            flat=True,
        )[0]
        params = {saved_queries.CATEGORY_PARAM: str(category)}
    rows = run_saved_query(unit, params)
    assert rows
    assert {len(row) for row in rows} == {COLUMNS[unit]}


def test_category_filter_starts_with_all(load_seed):
    """R-inventory-027: the 'all categories' entry first, then the categories by
    name."""
    load_seed(1)
    rows = run_saved_query("qrycboProductCategories", {})
    assert rows[0] == (1, 0, "<All>")
    assert {clause for clause, _pk, _name in rows[1:]} == {2}
    assert run_saved_query("qrycboProducts", {}) == []
