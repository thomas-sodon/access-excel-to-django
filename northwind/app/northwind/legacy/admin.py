"""Admin for the kept tables: history (django-simple-history) and import/export
(django-import-export, through legacy.resources) on every model."""

from __future__ import annotations

from django.contrib import admin
from import_export.admin import ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from northwind.legacy import models
from northwind.legacy.resources import RESOURCES

AUDIT = ("added_by", "added_on", "modified_by", "modified_on")


class LegacyAdmin(ImportExportMixin, SimpleHistoryAdmin):
    """History and xlsx/csv import-export; the audit stamps are shown read-only."""

    def get_resource_classes(self, request):
        return [RESOURCES[self.model._meta.db_table]]  # noqa: SLF001

    def get_readonly_fields(self, request, obj=None):
        names = {f.name for f in self.model._meta.concrete_fields}  # noqa: SLF001
        stamps = [name for name in AUDIT if name in names]
        return [*super().get_readonly_fields(request, obj), *stamps]


@admin.register(models.CompanyType)
class CompanyTypeAdmin(LegacyAdmin):
    list_display = ["company_type_id", "company_type"]
    search_fields = ["company_type"]


@admin.register(models.OrderStatus)
class OrderStatusAdmin(LegacyAdmin):
    list_display = [
        "order_status_id",
        "order_status_code",
        "order_status_name",
        "sort_order",
    ]
    search_fields = ["order_status_code", "order_status_name"]


@admin.register(models.OrderDetailStatus)
class OrderDetailStatusAdmin(LegacyAdmin):
    list_display = ["order_detail_status_id", "order_detail_status_name", "sort_order"]
    search_fields = ["order_detail_status_name"]


@admin.register(models.TaxStatus)
class TaxStatusAdmin(LegacyAdmin):
    list_display = ["tax_status_id", "tax_status"]
    search_fields = ["tax_status"]


@admin.register(models.PurchaseOrderStatus)
class PurchaseOrderStatusAdmin(LegacyAdmin):
    list_display = ["status_id", "status_name", "sort_order"]
    search_fields = ["status_name"]


@admin.register(models.Privilege)
class PrivilegeAdmin(LegacyAdmin):
    list_display = ["privilege_id", "privilege_name"]
    search_fields = ["privilege_name"]


@admin.register(models.State)
class StateAdmin(LegacyAdmin):
    list_display = ["state_abbrev", "state_name"]
    search_fields = ["state_abbrev", "state_name"]


@admin.register(models.Title)
class TitleAdmin(LegacyAdmin):
    list_display = ["title"]
    search_fields = ["title"]


@admin.register(models.SystemSetting)
class SystemSettingAdmin(LegacyAdmin):
    list_display = ["setting_id", "setting_name", "setting_value"]
    search_fields = ["setting_name", "notes"]


@admin.register(models.String)
class StringAdmin(LegacyAdmin):
    list_display = ["string_id", "string_data"]
    search_fields = ["string_data"]


@admin.register(models.Company)
class CompanyAdmin(LegacyAdmin):
    list_display = [
        "company_id",
        "company_name",
        "company_type",
        "city",
        "state",
        "business_phone",
    ]
    list_filter = ["company_type"]
    search_fields = ["company_name", "city", "zip"]


@admin.register(models.Contact)
class ContactAdmin(LegacyAdmin):
    list_display = [
        "contact_id",
        "last_name",
        "first_name",
        "company",
        "job_title",
        "email_address",
    ]
    search_fields = ["last_name", "first_name", "email_address", "job_title"]


@admin.register(models.Employee)
class EmployeeAdmin(LegacyAdmin):
    list_display = [
        "employee_id",
        "first_name",
        "last_name",
        "job_title",
        "email_address",
        "supervisor",
    ]
    search_fields = ["first_name", "last_name", "email_address", "job_title"]


@admin.register(models.EmployeePrivilege)
class EmployeePrivilegeAdmin(LegacyAdmin):
    list_display = ["employee_privilege_id", "employee", "privilege"]
    search_fields = ["employee__first_name", "employee__last_name"]


@admin.register(models.ProductCategory)
class ProductCategoryAdmin(LegacyAdmin):
    list_display = [
        "product_category_id",
        "product_category_name",
        "product_category_code",
    ]
    search_fields = ["product_category_name", "product_category_code"]


@admin.register(models.Product)
class ProductAdmin(LegacyAdmin):
    list_display = [
        "product_id",
        "product_code",
        "product_name",
        "product_category",
        "unit_price",
        "discontinued",
    ]
    list_filter = ["discontinued", "product_category"]
    search_fields = ["product_code", "product_name"]


@admin.register(models.ProductVendor)
class ProductVendorAdmin(LegacyAdmin):
    list_display = ["product_vendor_id", "product", "vendor"]
    search_fields = ["product__product_name", "vendor__company_name"]


@admin.register(models.StockTake)
class StockTakeAdmin(LegacyAdmin):
    list_display = [
        "stock_take_id",
        "stock_take_date",
        "product",
        "quantity_on_hand",
        "expected_quantity",
    ]
    search_fields = ["product__product_name", "product__product_code"]


@admin.register(models.Order)
class OrderAdmin(LegacyAdmin):
    list_display = [
        "order_id",
        "order_date",
        "customer",
        "employee",
        "order_status",
        "invoice_date",
        "shipped_date",
    ]
    list_filter = ["order_status"]
    search_fields = ["customer__company_name", "notes"]


@admin.register(models.OrderDetail)
class OrderDetailAdmin(LegacyAdmin):
    list_display = [
        "order_detail_id",
        "order",
        "product",
        "quantity",
        "unit_price",
        "discount",
        "order_detail_status",
    ]
    list_filter = ["order_detail_status"]
    search_fields = ["product__product_name", "product__product_code"]


@admin.register(models.PurchaseOrder)
class PurchaseOrderAdmin(LegacyAdmin):
    list_display = [
        "purchase_order_id",
        "vendor",
        "status",
        "submitted_date",
        "approved_date",
        "received_date",
    ]
    list_filter = ["status"]
    search_fields = ["vendor__company_name", "notes"]


@admin.register(models.PurchaseOrderDetail)
class PurchaseOrderDetailAdmin(LegacyAdmin):
    list_display = [
        "purchase_order_detail_id",
        "purchase_order",
        "product",
        "quantity",
        "unit_cost",
        "received_date",
    ]
    search_fields = ["product__product_name", "product__product_code"]
