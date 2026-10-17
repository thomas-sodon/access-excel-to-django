"""Northwind's roles mirror the original's privileges (analysis/rules.json)."""

import json
from pathlib import Path

import pytest
from django.conf import settings

from northwind.core import roles
from northwind.core.local import roles as local_roles
from northwind.legacy.choices import PrivilegeCode

RULES = Path(settings.BASE_DIR).parent / "analysis" / "rules.json"


def rule_ids() -> set[str]:
    return {r["id"] for r in json.loads(RULES.read_text("utf-8"))["rules"]}


def test_every_cited_rule_exists():
    known = rule_ids()
    cited = {r for info in local_roles.ROLES.values() for r in info["rules"]}
    for info in local_roles.CUSTOM_PERMISSIONS.values():
        cited |= set(info["rules"])
    cited |= set(local_roles.FIXED_CODE_MODELS.values())
    assert cited <= known, sorted(cited - known)


def test_the_approver_mirrors_the_approve_purchase_orders_privilege():
    """R-purchasing-005: only a user holding the approve-purchase-order privilege
    may approve."""
    approver = local_roles.ROLES["approver"]
    assert approver["privilege"] == PrivilegeCode.APPROVE_PURCHASE_ORDERS
    assert "R-purchasing-005" in approver["rules"]


@pytest.mark.django_db
def test_only_the_approver_may_approve_purchase_orders():
    """R-purchasing-005."""
    assert local_roles.APPROVE_PURCHASE_ORDERS in roles.role_permissions("approver")
    assert local_roles.APPROVE_PURCHASE_ORDERS not in roles.role_permissions("staff")


@pytest.mark.django_db
def test_stock_takes_are_append_only_for_everybody():
    """R-inventory-011: a stock take can be added, never changed or deleted."""
    for role in roles.role_names():
        perms = roles.role_permissions(role)
        assert "legacy.add_stocktake" in perms
        assert "legacy.view_stocktake" in perms
        assert "legacy.change_stocktake" not in perms
        assert "legacy.delete_stocktake" not in perms


@pytest.mark.django_db
def test_fixed_code_lists_cannot_grow_or_shrink():
    """R-orders-047: the logic depends on the code rows by identity."""
    for role in roles.role_names():
        perms = roles.role_permissions(role)
        for model in local_roles.FIXED_CODE_MODELS:
            assert f"legacy.view_{model}" in perms
            assert f"legacy.add_{model}" not in perms
            assert f"legacy.delete_{model}" not in perms


@pytest.mark.django_db
def test_staff_may_work_with_orders_and_purchase_orders():
    """R-orders-050: every signed-in employee uses the order and purchasing screens."""
    perms = roles.role_permissions("staff")
    for model in ("order", "orderdetail", "purchaseorder", "purchaseorderdetail"):
        for action in ("view", "add", "change", "delete"):
            assert f"legacy.{action}_{model}" in perms
