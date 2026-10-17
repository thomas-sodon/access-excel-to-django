"""App-wide pytest set-up (written by toolkit new-app).

- Test databases are named by config/testdb.py, the helper that
  config/settings/test.py uses too.
- northwind.core.testing (load_seed, user_with_role) is loaded once
  northwind/core/testing.py exists, so tests anywhere under app/ (tests/e2e/
  included) reach its fixtures.
"""

from pathlib import Path

import pytest

from config.testdb import apply_test_db_names
from config.testdb import prefix_and_suffix

if (Path(__file__).resolve().parent / "northwind" / "core" / "testing.py").is_file():
    pytest_plugins = ["northwind.core.testing"]


@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    from django.conf import settings  # noqa: PLC0415

    apply_test_db_names(settings.DATABASES, *prefix_and_suffix())
