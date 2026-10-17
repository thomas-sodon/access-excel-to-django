"""Fixed code lists of the original application (analysis/rules.json `lookups`).

The codes come from the design (the original's code constants and value lists), never
from data, as the signed spec's "Lookup codes to sign" table says. The labels are this
app's wording. Each class cites the rule of its lookup; R-orders-047 says the logic
depends on these codes by identity.
"""

from django.db import models


class OrderStatusCode(models.IntegerChoices):
    """Orders.OrderStatusID and the OrderStatus keys (R-orders-030, R-orders-047)."""

    CLOSED = 1, "Closed"
    INVOICED = 2, "Invoiced"
    NEW = 3, "New"
    SHIPPED = 4, "Shipped"
    PAID = 5, "Paid"


class OrderDetailStatusCode(models.IntegerChoices):
    """OrderDetails.OrderDetailStatusID, the OrderDetailStatus keys (R-orders-009)."""

    ALLOCATED = 1, "Allocated"
    INVOICED = 2, "Invoiced"
    NEW = 3, "New"
    NO_STOCK = 4, "No Stock"
    ON_ORDER = 5, "On Order"
    SHIPPED = 6, "Shipped"


class TaxStatusCode(models.IntegerChoices):
    """Orders.TaxStatusID (R-orders-020) and Companies.StandardTaxStatusID
    (R-orders-048)."""

    TAX_EXEMPT = 0, "Tax Exempt"
    TAXABLE = 1, "Taxable"


class CompanyTypeCode(models.IntegerChoices):
    """Companies.CompanyTypeID (R-orders-003); OWN_COMPANY marks the trading company
    itself, the company type that CompanyTypes.CompanyType names for the catalog
    (R-reports-014)."""

    CUSTOMER = 1, "Customer"
    SHIPPER = 2, "Shipper"
    VENDOR = 3, "Vendor"
    OWN_COMPANY = 4, "Own company"


class PurchaseOrderStatusCode(models.IntegerChoices):
    """PurchaseOrders.StatusID and the PurchaseOrderStatus keys (R-purchasing-003)."""

    APPROVED = 1, "Approved"
    CLOSED = 2, "Closed"
    NEW = 3, "New"
    SUBMITTED = 4, "Submitted"
    RECEIVED = 5, "Received"


class PrivilegeCode(models.IntegerChoices):
    """EmployeePrivileges.PrivilegeID and the Privileges keys (R-purchasing-005)."""

    APPROVE_PURCHASE_ORDERS = 1, "Approve purchase orders"


class SystemSettingCode(models.IntegerChoices):
    """SystemSettings.SettingID (R-orders-001): the settings the logic reads by key."""

    SALES_TAX_RATE = 1, "Default sales tax rate (thousandths)"
    LAST_RESET_DATE = 4, "Last date reset"
    SHOW_WELCOME = 5, "Show welcome page"
    VENDOR_TAX_RATE = 6, "Vendor tax rate"
    FIRST_RUN = 7, "First-run flag"


class PaymentMethod(models.TextChoices):
    """Orders.PaymentMethod (R-orders-017) and PurchaseOrders.PaymentMethod
    (R-purchasing-009): the fixed value list of the order and purchase order screens."""

    CREDIT_CARD = "Credit Card", "Credit card"
    CHECK = "Check", "Check"
    CASH = "Cash", "Cash"
