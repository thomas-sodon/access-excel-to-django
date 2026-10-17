"""The area registers exactly its units of goldens/manifest.json, and every unit runs
on synthetic seed 1 and returns the manifest's columns.

Structure only: the manifest gives unit ids and columns, params.json the seed's
parameter values. Expected outputs are the harness's job (equivalence/), never read
here.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings

from northwind.core.saved_queries import DOCUMENTS
from northwind.core.saved_queries import SAVED_QUERIES
from northwind.core.saved_queries import run_saved_query

AREA = "orders"
SEED = "seed-1"


def _goldens(name: str) -> dict:
    path = Path(settings.BASE_DIR).parent / "goldens" / name
    return json.loads(path.read_text(encoding="utf-8"))


MANIFEST = _goldens("manifest.json")["units"]
PARAMS = _goldens("params.json")["units"]
UNITS = sorted(unit for unit, info in MANIFEST.items() if info["area"] == AREA)


def test_the_area_registers_exactly_its_units():
    registered = {
        unit
        for unit, fn in {**SAVED_QUERIES, **DOCUMENTS}.items()
        if fn.__module__ == f"northwind.{AREA}.saved_queries"
    }
    assert registered == set(UNITS)


def test_every_unit_runs_on_seed_one(load_seed):
    """Seed 1 is loaded once; each unit returns rows of the manifest's width."""
    load_seed(1)
    problems = []
    for unit in UNITS:
        params = PARAMS.get(unit, {}).get("values", {}).get(SEED, {})
        rows = run_saved_query(unit, params)
        width = len(MANIFEST[unit]["columns"])
        if not rows or any(len(row) != width for row in rows):
            problems.append(unit)
    assert problems == []
