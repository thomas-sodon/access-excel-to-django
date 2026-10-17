"""The kept Northwind tables (analysis/rules.json objects with type table and decision
keep).

Drafted with `manage.py inspectdb` on the schema-only development database that
`toolkit stage1 --schema-only` builds from the design, then curated: one managed model
per table, singular class names, `db_table` and `db_column` holding the original names,
so the same models run on a Stage 1 database next to the Access front end (`migrate
--fake-initial`).

- Relations: `on_delete` as analysis/rules.json `relations` says; each cites its rule.
- Lookups: the code lists in `legacy.choices`; each field cites its rule.
- Validation rules of the original tables are Meta.constraints (portable CHECK
  constraints that full_clean() also checks); the Before Change data macros are the
  audit stamps in `legacy.audit`.
- Columns the original stores as attachments (Employees.Attachments,
  ProductCategories.ProductCategoryImage) are not carried over: the dataset omits them
  too.
"""
# Legacy text columns hold NULL as well as text, so nullable CharFields keep null=True.
# ruff: noqa: DJ001

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from northwind.legacy import audit
from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.choices import PaymentMethod
from northwind.legacy.choices import PrivilegeCode
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.choices import SystemSettingCode
from northwind.legacy.choices import TaxStatusCode

BYTE = [MinValueValidator(0), MaxValueValidator(255)]  # Access Byte columns hold 0..255


def money(column: str, *, required: bool = True) -> models.DecimalField:
    """An Access Currency column: four decimal places."""
    return models.DecimalField(
        db_column=column,
        max_digits=19,
        decimal_places=4,
        blank=not required,
        null=not required,
    )


class FixedCodes:
    """full_clean() refuses a key outside the table's fixed code list (legacy.choices).

    Django checks `choices` on ordinary fields, but not on an AutoField key, which is
    what most of the original's code tables use."""

    def clean(self) -> None:
        super().clean()
        key = self._meta.pk
        codes = {value for value, _label in key.choices or ()}
        if codes and self.pk is not None and self.pk not in codes:
            message = f"{self.pk} is not one of the fixed codes of this table."
            raise ValidationError({key.name: message})


# ---------------------------------------------------- lookup tables


class CompanyType(FixedCodes, audit.AuditStampedModel):
    # Fixed codes (R-orders-047); lookup Companies.CompanyTypeID (R-orders-003).
    company_type_id = models.AutoField(
        db_column="CompanyTypeID",
        primary_key=True,
        choices=CompanyTypeCode.choices,
    )
    # Lookup CompanyTypes.CompanyType (R-reports-014).
    company_type = models.CharField(db_column="CompanyType", max_length=50, unique=True)
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "CompanyTypes"
        verbose_name = "company type"

    def __str__(self) -> str:
        return self.company_type


class OrderStatus(FixedCodes, audit.AuditStampedModel):
    # Fixed codes (R-orders-047); lookup Orders.OrderStatusID (R-orders-030).
    order_status_id = models.AutoField(
        db_column="OrderStatusID",
        primary_key=True,
        choices=OrderStatusCode.choices,
    )
    order_status_code = models.CharField(
        db_column="OrderStatusCode",
        max_length=5,
        unique=True,
    )
    order_status_name = models.CharField(
        db_column="OrderStatusName",
        max_length=50,
        unique=True,
    )
    sort_order = models.SmallIntegerField(
        db_column="SortOrder",
        unique=True,
        validators=BYTE,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "OrderStatus"
        verbose_name = "order status"
        verbose_name_plural = "order statuses"

    def __str__(self) -> str:
        return self.order_status_name


class OrderDetailStatus(FixedCodes, audit.AuditStampedModel):
    # Fixed codes (R-orders-047); lookup OrderDetails.OrderDetailStatusID
    # (R-orders-009).
    order_detail_status_id = models.AutoField(
        db_column="OrderDetailStatusID",
        primary_key=True,
        choices=OrderDetailStatusCode.choices,
    )
    order_detail_status_name = models.CharField(
        db_column="OrderDetailStatusName",
        max_length=50,
        unique=True,
    )
    sort_order = models.SmallIntegerField(
        db_column="SortOrder",
        unique=True,
        validators=BYTE,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "OrderDetailStatus"
        verbose_name = "order line status"
        verbose_name_plural = "order line statuses"

    def __str__(self) -> str:
        return self.order_detail_status_name


class TaxStatus(FixedCodes, audit.AuditStampedModel):
    # An Access Byte key numbered by hand. Fixed codes (R-orders-047); lookups
    # Orders.TaxStatusID (R-orders-020) and Companies.StandardTaxStatusID
    # (R-orders-048).
    tax_status_id = models.SmallIntegerField(
        db_column="TaxStatusID",
        primary_key=True,
        choices=TaxStatusCode.choices,
        validators=BYTE,
    )
    tax_status = models.CharField(db_column="TaxStatus", max_length=50, unique=True)
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "TaxStatus"
        verbose_name = "tax status"
        verbose_name_plural = "tax statuses"

    def __str__(self) -> str:
        return self.tax_status


class PurchaseOrderStatus(FixedCodes, audit.AuditStampedModel):
    # Fixed sequence New, Submitted, Approved, Received, Closed; lookup
    # PurchaseOrders.StatusID (R-purchasing-003).
    status_id = models.AutoField(
        db_column="StatusID",
        primary_key=True,
        choices=PurchaseOrderStatusCode.choices,
    )
    status_name = models.CharField(db_column="StatusName", max_length=50, unique=True)
    sort_order = models.SmallIntegerField(
        db_column="SortOrder",
        unique=True,
        validators=BYTE,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "PurchaseOrderStatus"
        verbose_name = "purchase order status"
        verbose_name_plural = "purchase order statuses"

    def __str__(self) -> str:
        return self.status_name


class Privilege(FixedCodes, audit.AuditStampedModel):
    # Lookup EmployeePrivileges.PrivilegeID (R-purchasing-005).
    privilege_id = models.AutoField(
        db_column="PrivilegeID",
        primary_key=True,
        choices=PrivilegeCode.choices,
    )
    privilege_name = models.CharField(
        db_column="PrivilegeName",
        max_length=50,
        unique=True,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Privileges"
        verbose_name = "privilege"

    def __str__(self) -> str:
        return self.privilege_name


class State(models.Model):
    state_abbrev = models.CharField(
        db_column="StateAbbrev",
        primary_key=True,
        max_length=2,
    )
    state_name = models.CharField(db_column="StateName", max_length=50, unique=True)
    history = HistoricalRecords()

    class Meta:
        db_table = "States"
        verbose_name = "state"

    def __str__(self) -> str:
        return self.state_name


class Title(audit.AuditStampedModel):
    # Courtesy titles; the list can grow from the employee screen (R-orders-044).
    title = models.CharField(db_column="Title", primary_key=True, max_length=20)
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Titles"
        verbose_name = "title"

    def __str__(self) -> str:
        return self.title


class SystemSetting(FixedCodes, models.Model):
    # Settings read by key (R-orders-001).
    setting_id = models.AutoField(
        db_column="SettingID",
        primary_key=True,
        choices=SystemSettingCode.choices,
    )
    setting_name = models.CharField(db_column="SettingName", max_length=50, unique=True)
    setting_value = models.CharField(
        db_column="SettingValue",
        max_length=255,
        blank=True,
        null=True,
    )
    notes = models.CharField(db_column="Notes", max_length=255, blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        db_table = "SystemSettings"
        verbose_name = "system setting"

    def __str__(self) -> str:
        return self.setting_name


class String(audit.AuditStampedModel):
    """The application's maintained texts (messages, catalog pages)."""

    string_id = models.AutoField(db_column="StringID", primary_key=True)
    string_data = models.TextField(db_column="StringData")
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Strings"
        verbose_name = "string"

    def __str__(self) -> str:
        return f"String {self.string_id}"


# ---------------------------------------------------- companies and people


class Company(audit.AuditStampedModel):
    company_id = models.AutoField(db_column="CompanyID", primary_key=True)
    company_name = models.CharField(db_column="CompanyName", max_length=50)
    # PROTECT (R-orders-034); codes in CompanyTypeCode (R-orders-003).
    company_type = models.ForeignKey(
        CompanyType,
        models.PROTECT,
        db_column="CompanyTypeID",
        related_name="companies",
    )
    business_phone = models.CharField(
        db_column="BusinessPhone",
        max_length=20,
        blank=True,
        null=True,
    )
    address = models.CharField(db_column="Address", max_length=255)
    city = models.CharField(db_column="City", max_length=255)
    # PROTECT (R-orders-047).
    state = models.ForeignKey(
        State,
        models.PROTECT,
        db_column="StateAbbrev",
        related_name="companies",
    )
    zip = models.CharField(db_column="Zip", max_length=10)
    website = models.TextField(db_column="Website", blank=True, null=True)
    notes = models.TextField(db_column="Notes", blank=True, null=True)
    # PROTECT (R-orders-047); a new company is Tax Exempt (R-orders-048).
    standard_tax_status = models.ForeignKey(
        TaxStatus,
        models.PROTECT,
        db_column="StandardTaxStatusID",
        related_name="companies",
        default=TaxStatusCode.TAX_EXEMPT,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Companies"
        verbose_name = "company"
        verbose_name_plural = "companies"
        constraints = [
            models.UniqueConstraint(
                fields=["company_name", "company_type"],
                name="Companies_CustomerName",
            ),
        ]

    def __str__(self) -> str:
        return self.company_name


class Contact(audit.AuditStampedModel):
    contact_id = models.AutoField(db_column="ContactID", primary_key=True)
    # CASCADE: a company is deleted with its contacts (R-orders-033).
    company = models.ForeignKey(
        Company,
        models.CASCADE,
        db_column="CompanyID",
        related_name="contacts",
    )
    last_name = models.CharField(db_column="LastName", max_length=30)
    first_name = models.CharField(db_column="FirstName", max_length=20)
    email_address = models.CharField(
        db_column="EmailAddress",
        max_length=255,
        blank=True,
        null=True,
    )
    job_title = models.CharField(db_column="JobTitle", max_length=50)
    primary_phone = models.CharField(
        db_column="PrimaryPhone",
        max_length=20,
        blank=True,
        null=True,
    )
    secondary_phone = models.CharField(
        db_column="SecondaryPhone",
        max_length=20,
        blank=True,
        null=True,
    )
    notes = models.TextField(db_column="Notes", blank=True, null=True)
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Contacts"
        verbose_name = "contact"
        # The original's second unique index (company, last, first) covers the same
        # columns.
        constraints = [
            models.UniqueConstraint(
                fields=["company", "first_name", "last_name"],
                name="Contacts_uidxCompanyFNLN",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Employee(audit.AuditStampedModel):
    employee_id = models.AutoField(db_column="EmployeeID", primary_key=True)
    first_name = models.CharField(db_column="FirstName", max_length=20)
    last_name = models.CharField(db_column="LastName", max_length=30)
    email_address = models.CharField(
        db_column="EmailAddress",
        max_length=255,
        blank=True,
        null=True,
    )
    job_title = models.CharField(db_column="JobTitle", max_length=50)
    primary_phone = models.CharField(
        db_column="PrimaryPhone",
        max_length=20,
        blank=True,
        null=True,
    )
    secondary_phone = models.CharField(
        db_column="SecondaryPhone",
        max_length=20,
        blank=True,
        null=True,
    )
    # PROTECT; a title from the titles list (R-orders-044).
    title = models.ForeignKey(
        Title,
        models.PROTECT,
        db_column="Title",
        related_name="employees",
        blank=True,
        null=True,
    )
    notes = models.TextField(db_column="Notes", blank=True, null=True)
    # PROTECT (R-orders-040).
    supervisor = models.ForeignKey(
        "self",
        models.PROTECT,
        db_column="SupervisorID",
        related_name="supervised",
        blank=True,
        null=True,
    )
    windows_user_name = models.CharField(
        db_column="WindowsUserName",
        max_length=50,
        blank=True,
        null=True,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Employees"
        verbose_name = "employee"
        # The original's second unique index (last, first) covers the same columns.
        constraints = [
            models.UniqueConstraint(
                fields=["first_name", "last_name"],
                name="Employees_uidxFNLN",
            ),
            # Unique when set, several blanks allowed (a filtered index on SQL Server).
            models.UniqueConstraint(
                fields=["windows_user_name"],
                condition=models.Q(windows_user_name__isnull=False),
                name="Employees_WindowsUserName",
            ),
        ]

    def __str__(self) -> str:
        return audit.employee_full_name(self.first_name, self.last_name)

    @property
    def full_name(self) -> str:
        """First name then last name, as the audit stamps record it (R-orders-031)."""
        return audit.employee_full_name(self.first_name, self.last_name)


class EmployeePrivilege(audit.AuditStampedModel):
    employee_privilege_id = models.AutoField(
        db_column="EmployeePrivilegeID",
        primary_key=True,
    )
    # PROTECT (R-orders-040).
    employee = models.ForeignKey(
        Employee,
        models.PROTECT,
        db_column="EmployeeID",
        related_name="privilege_grants",
    )
    # PROTECT (R-orders-042); codes in PrivilegeCode (R-purchasing-005).
    privilege = models.ForeignKey(
        Privilege,
        models.PROTECT,
        db_column="PrivilegeID",
        related_name="grants",
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "EmployeePrivileges"
        verbose_name = "employee privilege"
        # The original's unique index on (EmployeePrivilegeID, PrivilegeID) contains the
        # primary key, so it adds nothing and is not repeated.

    def __str__(self) -> str:
        return f"{self.employee} - {self.privilege}"


# ------------------------------------------------- products and inventory


class ProductCategory(audit.AuditStampedModel):
    product_category_id = models.AutoField(
        db_column="ProductCategoryID",
        primary_key=True,
    )
    product_category_name = models.CharField(
        db_column="ProductCategoryName",
        max_length=255,
        unique=True,
    )
    # Generated by the new app, no codes copied (lookup, R-inventory-013).
    product_category_code = models.CharField(
        db_column="ProductCategoryCode",
        max_length=3,
        unique=True,
    )
    product_category_desc = models.CharField(
        db_column="ProductCategoryDesc",
        max_length=255,
        blank=True,
        null=True,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "ProductCategories"
        verbose_name = "product category"
        verbose_name_plural = "product categories"

    def __str__(self) -> str:
        return self.product_category_name


class Product(audit.AuditStampedModel):
    product_id = models.AutoField(db_column="ProductID", primary_key=True)
    product_code = models.CharField(db_column="ProductCode", max_length=20, unique=True)
    product_name = models.CharField(db_column="ProductName", max_length=50, unique=True)
    product_description = models.TextField(
        db_column="ProductDescription",
        blank=True,
        null=True,
    )
    standard_unit_cost = money("StandardUnitCost")
    unit_price = money("UnitPrice")
    reorder_level = models.SmallIntegerField(
        db_column="ReorderLevel",
        blank=True,
        null=True,
        default=0,
    )
    target_level = models.SmallIntegerField(
        db_column="TargetLevel",
        blank=True,
        null=True,
    )
    quantity_per_unit = models.CharField(
        db_column="QuantityPerUnit",
        max_length=50,
        blank=True,
        null=True,
    )
    discontinued = models.BooleanField(db_column="Discontinued", default=False)
    minimum_reorder_quantity = models.SmallIntegerField(
        db_column="MinimumReorderQuantity",
        blank=True,
        null=True,
    )
    # PROTECT (R-inventory-015).
    product_category = models.ForeignKey(
        ProductCategory,
        models.PROTECT,
        db_column="ProductCategoryID",
        related_name="products",
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Products"
        verbose_name = "product"

    def __str__(self) -> str:
        return self.product_name


class ProductVendor(audit.AuditStampedModel):
    product_vendor_id = models.AutoField(db_column="ProductVendorID", primary_key=True)
    # CASCADE: a product is deleted with its vendor links (R-inventory-016).
    product = models.ForeignKey(
        Product,
        models.CASCADE,
        db_column="ProductID",
        related_name="vendor_links",
    )
    # PROTECT (R-inventory-029).
    vendor = models.ForeignKey(
        Company,
        models.PROTECT,
        db_column="VendorID",
        related_name="vendor_products",
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "ProductVendors"
        verbose_name = "product vendor"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "vendor"],
                name="ProductVendors_UniqueIdx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product} - {self.vendor}"


class StockTake(audit.AuditStampedModel):
    stock_take_id = models.AutoField(db_column="StockTakeID", primary_key=True)
    # Set to the moment the stock take is saved (R-inventory-009).
    stock_take_date = models.DateTimeField(
        db_column="StockTakeDate",
        default=audit.stamp_time,
    )
    # CASCADE: a product is deleted with its stock takes (R-inventory-016).
    product = models.ForeignKey(
        Product,
        models.CASCADE,
        db_column="ProductID",
        related_name="stock_takes",
    )
    quantity_on_hand = models.SmallIntegerField(db_column="QuantityOnHand")
    expected_quantity = models.IntegerField(
        db_column="ExpectedQuantity",
        blank=True,
        null=True,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "StockTake"
        verbose_name = "stock take"
        constraints = [
            # The counted quantity is physical stock and cannot be negative
            # (R-inventory-009).
            models.CheckConstraint(
                condition=models.Q(quantity_on_hand__gte=0),
                name="StockTake_QuantityOnHand_not_negative",
                violation_error_message=(
                    "The quantity on hand is physical stock and cannot be negative."
                ),
            ),
            # The expected quantity cannot be negative either (R-inventory-009).
            models.CheckConstraint(
                condition=models.Q(expected_quantity__isnull=True)
                | models.Q(expected_quantity__gte=0),
                name="StockTake_ExpectedQuantity_not_negative",
                violation_error_message=(
                    "The expected quantity is physical stock and cannot be negative."
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"Stock take {self.stock_take_id}"


# ---------------------------------------------------- orders


class Order(audit.AuditStampedModel):
    order_id = models.AutoField(db_column="OrderID", primary_key=True)
    # The salesperson; PROTECT (R-orders-040).
    employee = models.ForeignKey(
        Employee,
        models.PROTECT,
        db_column="EmployeeID",
        related_name="orders",
    )
    # PROTECT: a company with orders cannot be deleted (R-orders-033).
    customer = models.ForeignKey(
        Company,
        models.PROTECT,
        db_column="CustomerID",
        related_name="orders_as_customer",
    )
    # Pre-filled with the current date and time (R-orders-001).
    order_date = models.DateTimeField(db_column="OrderDate", default=timezone.now)
    invoice_date = models.DateTimeField(db_column="InvoiceDate", blank=True, null=True)
    shipped_date = models.DateTimeField(db_column="ShippedDate", blank=True, null=True)
    # PROTECT (R-orders-033).
    shipper = models.ForeignKey(
        Company,
        models.PROTECT,
        db_column="ShipperID",
        related_name="orders_as_shipper",
        blank=True,
        null=True,
    )
    shipping_fee = money("ShippingFee", required=False)
    tax_rate = models.FloatField(db_column="TaxRate")
    # PROTECT (R-orders-047); codes in TaxStatusCode (R-orders-020).
    tax_status = models.ForeignKey(
        TaxStatus,
        models.PROTECT,
        db_column="TaxStatusID",
        related_name="orders",
    )
    # The order screen's fixed payment methods (lookup, R-orders-017).
    payment_method = models.CharField(
        db_column="PaymentMethod",
        max_length=50,
        blank=True,
        null=True,
        choices=PaymentMethod.choices,
    )
    paid_date = models.DateTimeField(db_column="PaidDate", blank=True, null=True)
    notes = models.TextField(db_column="Notes", blank=True, null=True)
    # PROTECT (R-orders-047); codes in OrderStatusCode (R-orders-030).
    order_status = models.ForeignKey(
        OrderStatus,
        models.PROTECT,
        db_column="OrderStatusID",
        related_name="orders",
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "Orders"
        verbose_name = "order"

    def __str__(self) -> str:
        return f"Order {self.order_id}"


class OrderDetail(audit.AuditStampedModel):
    order_detail_id = models.AutoField(db_column="OrderDetailID", primary_key=True)
    # CASCADE: an order is deleted with its lines (R-orders-011).
    order = models.ForeignKey(
        Order,
        models.CASCADE,
        db_column="OrderID",
        related_name="lines",
    )
    # PROTECT: a product on an order line cannot be deleted (R-inventory-016).
    product = models.ForeignKey(
        Product,
        models.PROTECT,
        db_column="ProductID",
        related_name="order_lines",
    )
    quantity = models.SmallIntegerField(db_column="Quantity")
    unit_price = money("UnitPrice")
    discount = models.FloatField(db_column="Discount", blank=True, null=True, default=0)
    # PROTECT (R-orders-047); codes in OrderDetailStatusCode (R-orders-009).
    order_detail_status = models.ForeignKey(
        OrderDetailStatus,
        models.PROTECT,
        db_column="OrderDetailStatusID",
        related_name="order_lines",
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "OrderDetails"
        verbose_name = "order line"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="OrderDetails_uidxOrderID_ProductID",
            ),
            # An order line's quantity must be greater than zero (R-orders-006).
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="OrderDetails_Quantity_positive",
                violation_error_message=(
                    "An order line's quantity must be greater than zero."
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"Order {self.order_id} line {self.order_detail_id}"


# ---------------------------------------------------- purchasing


class PurchaseOrder(audit.AuditStampedModel):
    purchase_order_id = models.AutoField(db_column="PurchaseOrderID", primary_key=True)
    # PROTECT (R-purchasing-002).
    vendor = models.ForeignKey(
        Company,
        models.PROTECT,
        db_column="VendorID",
        related_name="purchase_orders",
    )
    # PROTECT (R-purchasing-004).
    submitted_by = models.ForeignKey(
        Employee,
        models.PROTECT,
        db_column="SubmittedByID",
        related_name="purchase_orders_submitted",
        blank=True,
        null=True,
    )
    submitted_date = models.DateTimeField(
        db_column="SubmittedDate",
        blank=True,
        null=True,
    )
    # PROTECT (R-purchasing-005).
    approved_by = models.ForeignKey(
        Employee,
        models.PROTECT,
        db_column="ApprovedByID",
        related_name="purchase_orders_approved",
        blank=True,
        null=True,
    )
    approved_date = models.DateTimeField(
        db_column="ApprovedDate",
        blank=True,
        null=True,
    )
    # PROTECT; codes in PurchaseOrderStatusCode (R-purchasing-003).
    status = models.ForeignKey(
        PurchaseOrderStatus,
        models.PROTECT,
        db_column="StatusID",
        related_name="purchase_orders",
    )
    received_date = models.DateTimeField(
        db_column="ReceivedDate",
        blank=True,
        null=True,
    )
    shipping_fee = money("ShippingFee", required=False)
    tax_amount = money("TaxAmount", required=False)
    payment_date = models.DateTimeField(db_column="PaymentDate", blank=True, null=True)
    payment_amount = money("PaymentAmount", required=False)
    # The purchase order screen's fixed payment methods (lookup, R-purchasing-009).
    payment_method = models.CharField(
        db_column="PaymentMethod",
        max_length=50,
        blank=True,
        null=True,
        choices=PaymentMethod.choices,
    )
    notes = models.TextField(db_column="Notes", blank=True, null=True)
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "PurchaseOrders"
        verbose_name = "purchase order"

    def __str__(self) -> str:
        return f"Purchase order {self.purchase_order_id}"


class PurchaseOrderDetail(audit.AuditStampedModel):
    purchase_order_detail_id = models.AutoField(
        db_column="PurchaseOrderDetailID",
        primary_key=True,
    )
    # CASCADE: a purchase order is deleted with its lines (R-purchasing-014).
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        models.CASCADE,
        db_column="PurchaseOrderID",
        related_name="lines",
    )
    # PROTECT: a product on a purchase order line cannot be deleted (R-inventory-016).
    product = models.ForeignKey(
        Product,
        models.PROTECT,
        db_column="ProductID",
        related_name="purchase_order_lines",
    )
    quantity = models.SmallIntegerField(db_column="Quantity")
    unit_cost = money("UnitCost")
    received_date = models.DateTimeField(
        db_column="ReceivedDate",
        blank=True,
        null=True,
    )
    added_by = audit.added_by()
    added_on = audit.added_on()
    modified_by = audit.modified_by()
    modified_on = audit.modified_on()
    history = HistoricalRecords()

    class Meta:
        db_table = "PurchaseOrderDetails"
        verbose_name = "purchase order line"
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "product"],
                name="PurchaseOrderDetails_uidxPOID_ProductID",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Purchase order {self.purchase_order_id} line "
            f"{self.purchase_order_detail_id}"
        )
