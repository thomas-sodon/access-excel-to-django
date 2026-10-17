"""legacy.resources: one ModelResource per table, keyed by db_table, with the original
column names as headers; hand-written synthetic rows only."""

import pytest
import tablib

from northwind.legacy import models
from northwind.legacy.factories import ProductFactory
from northwind.legacy.resources import RESOURCES
from northwind.legacy.resources import legacy_models


def meta(model):
    return model._meta  # noqa: SLF001


def test_one_resource_per_table():
    assert sorted(RESOURCES) == sorted(meta(m).db_table for m in legacy_models())


@pytest.mark.parametrize("model", legacy_models(), ids=lambda m: m.__name__)
def test_headers_are_the_original_column_names(model):
    resource = RESOURCES[meta(model).db_table]()
    columns = [f.column for f in meta(model).concrete_fields]
    assert resource.get_export_headers() == columns
    assert [f.column_name for f in resource.get_import_fields()] == columns


@pytest.mark.django_db
def test_import_by_original_column_names():
    rows = tablib.Dataset(headers=["StateAbbrev", "StateName"])
    rows.append(["QQ", "Synthetic State"])
    result = RESOURCES["States"]().import_data(rows, raise_errors=True)
    assert not result.has_errors()
    assert models.State.objects.get(pk="QQ").state_name == "Synthetic State"


@pytest.mark.django_db
def test_export_then_import_round_trip():
    product = ProductFactory.create()
    resource = RESOURCES["Products"]()
    exported = resource.export()
    assert exported.headers[0] == "ProductID"
    assert "ProductCategoryID" in exported.headers
    result = RESOURCES["Products"]().import_data(
        exported,
        dry_run=True,
        raise_errors=True,
    )
    assert not result.has_errors()
    assert result.totals["update"] == 1
    assert (
        models.Product.objects.get(pk=product.pk).product_name == product.product_name
    )
