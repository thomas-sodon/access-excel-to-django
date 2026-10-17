"""Every unit the area registers runs on synthetic seed 1 (core.testing load_seed)
and returns the manifest's columns. Only the structure of goldens/manifest.json
(unit ids, area, column names) and the seed's parameter values of
goldens/params.json are read; never an expected output."""

import json
from pathlib import Path

import pytest
from django.conf import settings

from northwind.core.saved_queries import SAVED_QUERIES
from northwind.core.saved_queries import run_saved_query

# isort: split
# (the area's own modules sort after the shared ones, whatever the area id)
from northwind.purchasing import saved_queries

AREA = "purchasing"


def goldens() -> Path:
    return Path(settings.BASE_DIR).parent / "goldens"


def area_units() -> dict[str, dict]:
    manifest = json.loads((goldens() / "manifest.json").read_text(encoding="utf-8"))
    return {
        unit_id: unit
        for unit_id, unit in manifest["units"].items()
        if unit["area"] == AREA and unit["kind"] in ("saved_query", "formula_output")
    }


def seed_params(unit_id: str) -> dict[str, str]:
    params = json.loads((goldens() / "params.json").read_text(encoding="utf-8"))
    return params["units"].get(unit_id, {}).get("values", {}).get("seed-1", {})


def test_the_area_registers_exactly_its_units():
    registered = {
        unit_id
        for unit_id, fn in SAVED_QUERIES.items()
        if fn.__module__ == saved_queries.__name__
    }
    assert registered == set(area_units())


@pytest.mark.parametrize("unit_id", sorted(area_units()))
def test_unit_runs_on_seed_1(load_seed, unit_id):
    load_seed(1)
    columns = [column["name"] for column in area_units()[unit_id]["columns"]]
    assert list(saved_queries.COLUMNS[unit_id]) == columns
    rows = run_saved_query(unit_id, seed_params(unit_id))
    assert rows, f"{unit_id} returned no rows on seed 1"
    assert {len(row) for row in rows} == {len(columns)}
