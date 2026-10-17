"""The recorded demo walkthrough: workflow order_to_ship, the first must-keep item
("order entry -> invoice (printable PDF) -> shipping"), from sign-in to closing the
order, at a pace a viewer can follow.

It runs alone with `-m walkthrough tests/e2e` (the S6 demo gate runs it that way) in
its own browser context. With E2E_VIDEO_DIR set, that context is recorded at 1280x800
and saved as walkthrough.webm in that directory; without it nothing is written. The
steps and their assertions are test_order_to_ship's (R-orders-050, R-orders-029,
R-orders-030).
"""

from __future__ import annotations

import pytest

from tests.e2e.test_order_to_ship import run_order_to_ship


@pytest.mark.walkthrough
def test_walkthrough(record_context, sign_in, pause):
    with record_context("walkthrough") as page:
        run_order_to_ship(page, sign_in, pause=pause)
