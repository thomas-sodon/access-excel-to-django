"""Fixtures of the Sales and Catalog Reports tests."""

import pytest

from northwind.reports.tests.data import report_data


@pytest.fixture
def staff_client(client, user_with_role):
    """A client signed in as a user with the staff role (every Northwind role may
    run the reports, R-orders-050)."""
    client.force_login(user_with_role("staff"))
    return client


@pytest.fixture
def screen_data(db):
    return report_data()
