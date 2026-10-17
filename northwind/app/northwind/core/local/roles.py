"""Roles of Northwind (engagement code; core/roles.py syncs them into Django Groups).

The original has one privilege model: the Privileges table lists the rights,
EmployeePrivileges grants them to employees, and the only right the logic checks is
"approve purchase orders" (R-purchasing-005, modSecurity.HasPrivilege). Every other
screen is open to any signed-in employee (R-orders-050). So there are two roles:

- staff: what every signed-in employee may do. Every permission on the kept tables,
  except what the rules forbid to everybody: adding or deleting rows of the fixed code
  lists the logic depends on by identity (R-orders-047, R-purchasing-003,
  R-purchasing-005, R-orders-001), changing or deleting a stock take (stock takes
  are append-only, R-inventory-011), and approving purchase orders.
- approver: staff plus the approve-purchase-order right (R-purchasing-005); it mirrors
  the privilege with PrivilegeID 1 (legacy.choices.PrivilegeCode).

Approving is a permission no model declares, so it is a CUSTOM_PERMISSIONS row on the
purchase order model: legacy.approve_purchaseorder.
"""

from northwind.legacy.choices import PrivilegeCode

# Code tables whose rows the logic uses by key: no adds or deletes for anybody.
FIXED_CODE_MODELS = {
    "companytype": "R-orders-047",
    "orderstatus": "R-orders-047",
    "orderdetailstatus": "R-orders-047",
    "taxstatus": "R-orders-047",
    "purchaseorderstatus": "R-purchasing-003",
    "privilege": "R-purchasing-005",
    "systemsetting": "R-orders-001",
}

APPROVE_PURCHASE_ORDERS = "legacy.approve_purchaseorder"

CUSTOM_PERMISSIONS = {
    APPROVE_PURCHASE_ORDERS: {
        "model": "legacy.purchaseorder",
        "name": "Can approve purchase orders",
        "rules": ["R-purchasing-005"],
    },
}

NOBODY = [
    *(
        f"legacy.{action}_{model}"
        for model in FIXED_CODE_MODELS
        for action in ("add", "delete")
    ),
    "legacy.change_stocktake",
    "legacy.delete_stocktake",
]

ROLES = {
    "staff": {
        "label": "Staff",
        "permissions": ["legacy.*"],
        "exclude": [*NOBODY, APPROVE_PURCHASE_ORDERS],
        "rules": [
            "R-orders-050",
            "R-orders-047",
            "R-purchasing-003",
            "R-orders-001",
            "R-inventory-011",
        ],
    },
    "approver": {
        "label": "Purchase order approver",
        "permissions": ["legacy.*"],
        "exclude": NOBODY,
        "rules": ["R-purchasing-005", "R-orders-050", "R-inventory-011"],
        "privilege": int(PrivilegeCode.APPROVE_PURCHASE_ORDERS),
    },
}
