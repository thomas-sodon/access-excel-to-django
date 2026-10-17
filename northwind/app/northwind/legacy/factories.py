"""factory_boy factories for the kept tables: synthetic values only, valid against the
choices and constraints of legacy.models.

Lookup rows use the fixed codes of legacy.choices and are fetched or created by key, so
any number of factories can share them. The defaults give a customer company, a New
order with a New line, a New purchase order from a vendor company and a Tax Exempt tax
status.
"""

from __future__ import annotations

import datetime as dt
import string
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from northwind.legacy import models
from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.choices import OrderDetailStatusCode
from northwind.legacy.choices import OrderStatusCode
from northwind.legacy.choices import PrivilegeCode
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.choices import SystemSettingCode
from northwind.legacy.choices import TaxStatusCode

LETTERS = string.ascii_uppercase
DIGITS36 = string.digits + LETTERS
WHEN = dt.datetime(2024, 1, 15, 10, 30)  # noqa: DTZ001 (the app runs with USE_TZ False)


def letters2(n: int) -> str:
    """Two capital letters for sequence number n (AA, AB, ...)."""
    return LETTERS[(n // 26) % 26] + LETTERS[n % 26]


def code3(n: int) -> str:
    """Three base-36 characters for sequence number n."""
    return DIGITS36[(n // 1296) % 36] + DIGITS36[(n // 36) % 36] + DIGITS36[n % 36]


# ---------------------------------------------------- lookup tables


class CompanyTypeFactory(DjangoModelFactory[models.CompanyType]):
    company_type_id = CompanyTypeCode.CUSTOMER
    company_type = factory.LazyAttribute(
        lambda o: CompanyTypeCode(o.company_type_id).label,
    )

    class Meta:
        model = models.CompanyType
        django_get_or_create = ("company_type_id",)


class OrderStatusFactory(DjangoModelFactory[models.OrderStatus]):
    order_status_id = OrderStatusCode.NEW
    order_status_code = factory.LazyAttribute(lambda o: f"S{int(o.order_status_id)}")
    order_status_name = factory.LazyAttribute(
        lambda o: OrderStatusCode(o.order_status_id).label,
    )
    sort_order = factory.LazyAttribute(lambda o: int(o.order_status_id))

    class Meta:
        model = models.OrderStatus
        django_get_or_create = ("order_status_id",)


class OrderDetailStatusFactory(DjangoModelFactory[models.OrderDetailStatus]):
    order_detail_status_id = OrderDetailStatusCode.NEW
    order_detail_status_name = factory.LazyAttribute(
        lambda o: OrderDetailStatusCode(o.order_detail_status_id).label,
    )
    sort_order = factory.LazyAttribute(lambda o: int(o.order_detail_status_id))

    class Meta:
        model = models.OrderDetailStatus
        django_get_or_create = ("order_detail_status_id",)


class TaxStatusFactory(DjangoModelFactory[models.TaxStatus]):
    tax_status_id = TaxStatusCode.TAX_EXEMPT
    tax_status = factory.LazyAttribute(lambda o: TaxStatusCode(o.tax_status_id).label)

    class Meta:
        model = models.TaxStatus
        django_get_or_create = ("tax_status_id",)


class PurchaseOrderStatusFactory(DjangoModelFactory[models.PurchaseOrderStatus]):
    status_id = PurchaseOrderStatusCode.NEW
    status_name = factory.LazyAttribute(
        lambda o: PurchaseOrderStatusCode(o.status_id).label,
    )
    sort_order = factory.LazyAttribute(lambda o: int(o.status_id))

    class Meta:
        model = models.PurchaseOrderStatus
        django_get_or_create = ("status_id",)


class PrivilegeFactory(DjangoModelFactory[models.Privilege]):
    privilege_id = PrivilegeCode.APPROVE_PURCHASE_ORDERS
    privilege_name = factory.LazyAttribute(
        lambda o: PrivilegeCode(o.privilege_id).label,
    )

    class Meta:
        model = models.Privilege
        django_get_or_create = ("privilege_id",)


class StateFactory(DjangoModelFactory[models.State]):
    state_abbrev = factory.Sequence(letters2)
    state_name = factory.LazyAttribute(lambda o: f"State {o.state_abbrev}")

    class Meta:
        model = models.State
        django_get_or_create = ("state_abbrev",)


class TitleFactory(DjangoModelFactory[models.Title]):
    title = factory.Sequence(lambda n: f"T{n}.")

    class Meta:
        model = models.Title
        django_get_or_create = ("title",)


class SystemSettingFactory(DjangoModelFactory[models.SystemSetting]):
    setting_id = SystemSettingCode.SALES_TAX_RATE
    setting_name = factory.LazyAttribute(lambda o: f"Setting{int(o.setting_id)}")
    setting_value = "0"

    class Meta:
        model = models.SystemSetting
        django_get_or_create = ("setting_id",)


class StringFactory(DjangoModelFactory[models.String]):
    string_data = factory.Sequence(lambda n: f"Synthetic text {n}")

    class Meta:
        model = models.String


# ---------------------------------------------------- companies and people


class CompanyFactory(DjangoModelFactory[models.Company]):
    company_name = factory.Sequence(lambda n: f"Company {n:05d}")
    company_type = factory.SubFactory(CompanyTypeFactory)
    address = factory.Sequence(lambda n: f"{n} Example Street")
    city = "Sampletown"
    state = factory.SubFactory(StateFactory)
    zip = "00000"
    standard_tax_status = factory.SubFactory(TaxStatusFactory)

    class Meta:
        model = models.Company


class VendorFactory(CompanyFactory):
    company_type = factory.SubFactory(
        CompanyTypeFactory,
        company_type_id=CompanyTypeCode.VENDOR,
    )


class ShipperFactory(CompanyFactory):
    company_type = factory.SubFactory(
        CompanyTypeFactory,
        company_type_id=CompanyTypeCode.SHIPPER,
    )


class ContactFactory(DjangoModelFactory[models.Contact]):
    company = factory.SubFactory(CompanyFactory)
    last_name = factory.Sequence(lambda n: f"Contact{n}")
    first_name = "Pat"
    job_title = "Buyer"

    class Meta:
        model = models.Contact


class EmployeeFactory(DjangoModelFactory[models.Employee]):
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}")
    job_title = "Sales Representative"
    email_address = factory.LazyAttribute(
        lambda o: f"{o.first_name}.{o.last_name}@example.com".lower(),
    )

    class Meta:
        model = models.Employee


class EmployeePrivilegeFactory(DjangoModelFactory[models.EmployeePrivilege]):
    employee = factory.SubFactory(EmployeeFactory)
    privilege = factory.SubFactory(PrivilegeFactory)

    class Meta:
        model = models.EmployeePrivilege


# ------------------------------------------------- products and inventory


class ProductCategoryFactory(DjangoModelFactory[models.ProductCategory]):
    product_category_name = factory.Sequence(lambda n: f"Category {n}")
    product_category_code = factory.Sequence(code3)

    class Meta:
        model = models.ProductCategory


class ProductFactory(DjangoModelFactory[models.Product]):
    product_code = factory.Sequence(lambda n: f"SYN-{n:05d}")
    product_name = factory.Sequence(lambda n: f"Product {n:05d}")
    standard_unit_cost = Decimal("2.5000")
    unit_price = Decimal("4.0000")
    reorder_level = 5
    target_level = 20
    minimum_reorder_quantity = 10
    discontinued = False
    product_category = factory.SubFactory(ProductCategoryFactory)

    class Meta:
        model = models.Product


class ProductVendorFactory(DjangoModelFactory[models.ProductVendor]):
    product = factory.SubFactory(ProductFactory)
    vendor = factory.SubFactory(VendorFactory)

    class Meta:
        model = models.ProductVendor


class StockTakeFactory(DjangoModelFactory[models.StockTake]):
    stock_take_date = WHEN
    product = factory.SubFactory(ProductFactory)
    quantity_on_hand = 12
    expected_quantity = 12

    class Meta:
        model = models.StockTake


# ---------------------------------------------------- orders


class OrderFactory(DjangoModelFactory[models.Order]):
    employee = factory.SubFactory(EmployeeFactory)
    customer = factory.SubFactory(CompanyFactory)
    order_date = WHEN
    tax_rate = 0.0
    tax_status = factory.SubFactory(TaxStatusFactory)
    order_status = factory.SubFactory(OrderStatusFactory)

    class Meta:
        model = models.Order


class OrderDetailFactory(DjangoModelFactory[models.OrderDetail]):
    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 3
    unit_price = Decimal("4.0000")
    discount = 0.0
    order_detail_status = factory.SubFactory(OrderDetailStatusFactory)

    class Meta:
        model = models.OrderDetail


# ---------------------------------------------------- purchasing


class PurchaseOrderFactory(DjangoModelFactory[models.PurchaseOrder]):
    vendor = factory.SubFactory(VendorFactory)
    status = factory.SubFactory(PurchaseOrderStatusFactory)

    class Meta:
        model = models.PurchaseOrder


class PurchaseOrderDetailFactory(DjangoModelFactory[models.PurchaseOrderDetail]):
    purchase_order = factory.SubFactory(PurchaseOrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 10
    unit_cost = Decimal("2.5000")

    class Meta:
        model = models.PurchaseOrderDetail


FACTORIES = {
    models.CompanyType: CompanyTypeFactory,
    models.OrderStatus: OrderStatusFactory,
    models.OrderDetailStatus: OrderDetailStatusFactory,
    models.TaxStatus: TaxStatusFactory,
    models.PurchaseOrderStatus: PurchaseOrderStatusFactory,
    models.Privilege: PrivilegeFactory,
    models.State: StateFactory,
    models.Title: TitleFactory,
    models.SystemSetting: SystemSettingFactory,
    models.String: StringFactory,
    models.Company: CompanyFactory,
    models.Contact: ContactFactory,
    models.Employee: EmployeeFactory,
    models.EmployeePrivilege: EmployeePrivilegeFactory,
    models.ProductCategory: ProductCategoryFactory,
    models.Product: ProductFactory,
    models.ProductVendor: ProductVendorFactory,
    models.StockTake: StockTakeFactory,
    models.Order: OrderFactory,
    models.OrderDetail: OrderDetailFactory,
    models.PurchaseOrder: PurchaseOrderFactory,
    models.PurchaseOrderDetail: PurchaseOrderDetailFactory,
}
