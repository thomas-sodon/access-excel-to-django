"""Hand-made test data of the Sales and Catalog Reports tests (legacy/factories.py)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from northwind.legacy.choices import CompanyTypeCode
from northwind.legacy.factories import CompanyFactory
from northwind.legacy.factories import CompanyTypeFactory
from northwind.legacy.factories import EmployeeFactory
from northwind.legacy.factories import OrderDetailFactory
from northwind.legacy.factories import OrderFactory
from northwind.legacy.factories import ProductCategoryFactory
from northwind.legacy.factories import ProductFactory
from northwind.legacy.factories import ShipperFactory
from northwind.legacy.factories import StateFactory
from northwind.legacy.factories import StringFactory

if TYPE_CHECKING:
    from northwind.legacy.models import Company
    from northwind.legacy.models import Order

CATALOG_TEXTS = {
    43: "Gastronomic header",
    44: "Gastronomic text",
    45: "Quality header",
    46: "Quality text",
    47: "How to order text",
}


def at(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute)  # noqa: DTZ001 (USE_TZ is False)


def sale(employee, when: dt.datetime, *lines, **order_fields) -> Order:
    """An order of `employee` at `when` with lines (product, quantity, unit price,
    discount); the discount may be None (a blank discount)."""
    order = OrderFactory(employee=employee, order_date=when, **order_fields)
    for product, quantity, unit_price, discount in lines:
        OrderDetailFactory(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=Decimal(unit_price),
            discount=discount,
        )
    return order


def house_company() -> Company:
    """The selling company (company type: own company)."""
    return CompanyFactory(
        company_name="House Co",
        company_type=CompanyTypeFactory(company_type_id=CompanyTypeCode.OWN_COMPANY),
        address="1 Main Street",
        city="Sampletown",
        state=StateFactory(state_abbrev="WA"),
        zip="98000",
        business_phone="(555) 555-0100",
    )


def catalog_texts() -> None:
    for string_id, text in CATALOG_TEXTS.items():
        StringFactory(string_id=string_id, string_data=text)


def report_data() -> dict:
    """A small database for the screens: two orders (the latest on 15 Jan 2024 at
    10:30, so the default period runs from 15 Oct 2023 to 15 Jan 2024 at midnight
    and holds the earlier one), a house company, a shipper, the catalog texts and
    one category with a sold and an unsold product."""
    seller = EmployeeFactory(first_name="Ada", last_name="Example")
    category = ProductCategoryFactory(product_category_name="Beverages")
    sold = ProductFactory(product_name="Tea", product_category=category)
    ProductFactory(product_name="Water", product_category=category)
    sale(seller, at(2024, 1, 10, 9), (sold, 2, "4.00", 0.0))
    sale(seller, at(2024, 1, 15, 10, 30), (sold, 1, "4.00", 0.0))
    house_company()
    ShipperFactory(company_name="Fast Freight")
    catalog_texts()
    return {"seller": seller, "category": category, "sold": sold}
