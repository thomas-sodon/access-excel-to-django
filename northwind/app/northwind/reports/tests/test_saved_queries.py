"""Every unit the area registers runs on seed 1 (core.testing load_seed(1)) and returns
rows with the manifest's columns (goldens/manifest.json, units of area reports)."""

import pytest

from northwind.core.saved_queries import SAVED_QUERIES
from northwind.core.saved_queries import run_saved_query

pytestmark = pytest.mark.django_db

#: The manifest's columns of the area's units, in order.
UNITS = {
    "qryTotalSalesByProduct": ("ProductID", "TotalSales"),
    "qryrptProductCatalog": (
        "ProductCategoryID",
        "ProductCategoryName",
        "ProductCategoryCode",
        "ProductName",
        "ProductID",
        "QuantityPerUnit",
        "UnitPrice",
        "TotalSales",
        "ProductCategoryDesc",
        "ProductCategoryImage",
    ),
    "qryrptSalesByEmployee": (
        "EmployeeID",
        "OrderTotal",
        "FullNameFNLN",
        "MonthYear",
        "MonthYearSort",
    ),
    "qryrptSalesByProduct_ByMonth": (
        "ProductName",
        "ProductID",
        "MonthYear",
        "MonthYearSort",
        "OrderTotal",
    ),
    "qryrptSalesByProduct_ByQuarter": (
        "ProductName",
        "ProductID",
        "QuarterYear",
        "OrderTotal",
    ),
}


def test_the_area_registers_exactly_its_units():
    mine = {
        unit
        for unit, fn in SAVED_QUERIES.items()
        if fn.__module__ == "northwind.reports.saved_queries"
    }
    assert mine == set(UNITS)


def test_every_unit_runs_on_seed_1(load_seed):
    load_seed(1)
    for unit, columns in UNITS.items():
        rows = run_saved_query(unit, {})
        assert all(len(row) == len(columns) for row in rows), unit
        if unit in {"qryTotalSalesByProduct", "qryrptProductCatalog"}:
            # seed 1 has products and order lines; its sales in the default period
            # may be empty (the orders of that period need not have lines)
            assert rows, unit
