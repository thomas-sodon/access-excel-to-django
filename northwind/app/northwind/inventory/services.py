"""Services of the Products and Inventory area (analysis/interfaces.md, area
inventory): product_stock_levels, allocate_inventory, record_stock_take,
reorder_product and delete_product, plus the record saves of the product,
category and vendor-link screens.

Views call a service for every write. A service checks its rules first; a refused
action raises ValidationError with a plain message that starts with the rule id and
changes nothing. Every write runs in one transaction and is stamped with the signed-in
user's name (domain.people.acting_for; R-inventory-028); with no user, the stamp is
System. The stock figures, allocation and the purchase-order writes of a reorder are
shared with other areas and come from app/northwind/domain/ (its README).

The S4.models notes list no data macros with side effects (After Insert, After Update,
After Delete) on this area's tables, only the Before Change audit stamps, which
legacy.audit applies on every save.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.db import transaction
from django.db.models import F

from northwind.domain import inventory as stock
from northwind.domain import purchasing
from northwind.domain.people import acting_for
from northwind.legacy import audit
from northwind.legacy.choices import PurchaseOrderStatusCode
from northwind.legacy.models import Company
from northwind.legacy.models import OrderDetail
from northwind.legacy.models import Product
from northwind.legacy.models import ProductCategory
from northwind.legacy.models import ProductVendor
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail
from northwind.legacy.models import StockTake

if TYPE_CHECKING:
    from northwind.domain.inventory import StockLevels

#: The table of the skeleton's example screens: the products.
Record = Product
#: Columns of the product list, editable fields of the product form and the fields
#: of the list's filter. The product code is built, never typed (R-inventory-013).
LIST_FIELDS: tuple[str, ...] = (
    "product_code",
    "product_name",
    "product_category",
    "standard_unit_cost",
    "unit_price",
    "discontinued",
)
FORM_FIELDS: tuple[str, ...] = (
    "product_name",
    "product_category",
    "product_description",
    "quantity_per_unit",
    "standard_unit_cost",
    "unit_price",
    "reorder_level",
    "target_level",
    "minimum_reorder_quantity",
    "discontinued",
)
FILTER_FIELDS: tuple[str, ...] = ("product_category", "discontinued")
#: The product fields that cannot be empty (R-inventory-012).
REQUIRED_FIELDS: tuple[str, ...] = (
    "product_code",
    "product_name",
    "standard_unit_cost",
    "unit_price",
    "product_category_id",
    "discontinued",
)
EXAMPLE_RULE = "R-inventory-012"

#: The fixed company prefix of product codes (R-inventory-013).
CODE_PREFIX = "NWT"

APPROVED = PurchaseOrderStatusCode.APPROVED
NEW = PurchaseOrderStatusCode.NEW
SUBMITTED = PurchaseOrderStatusCode.SUBMITTED
#: Purchase orders a reorder treats as outstanding (R-inventory-017).
OUTSTANDING_STATUSES = (APPROVED, NEW, SUBMITTED)

_LABELS = {
    "product_code": "product code",
    "product_name": "product name",
    "standard_unit_cost": "standard unit cost",
    "unit_price": "unit price",
    "product_category_id": "category",
    "discontinued": "discontinued",
}


def refuse(rule: str, message: str, cause: BaseException | None = None) -> NoReturn:
    """Refuse an action: a ValidationError whose message starts with the rule id."""
    text = f"{rule}: {message}"
    raise ValidationError(text, code=rule) from cause


def _blank(value: Any) -> bool:
    return value is None or value == ""


def _product(product: Product | int) -> Product:
    if isinstance(product, Product):
        return product
    try:
        return Product.objects.get(pk=int(product))
    except (Product.DoesNotExist, TypeError, ValueError):
        refuse("R-inventory-001", "unknown product.")


def _clean(instance: Any, rule: str) -> None:
    """full_clean() with the refusal naming `rule` (unique names and codes, the
    table's checks)."""
    try:
        instance.full_clean()
    except ValidationError as error:
        refuse(rule, " ".join(error.messages), error)


# ---------------------------------------------------------------- stock figures


ZERO_LEVELS = stock.StockLevels(
    last_stock_take_date=None,
    last_stock_take_quantity=0,
    available=0,
    allocated=0,
    no_stock=0,
    on_order=0,
    to_sell=0,
    reorder_quantity=0,
)


def product_stock_levels(product: Product | int) -> StockLevels:
    """Physical stock, allocated, no-stock, on-order quantity, quantity to sell and
    suggested reorder quantity of a product (R-inventory-001 to R-inventory-006). A
    product that is not saved yet shows zeros (R-inventory-022); an unknown product
    is refused."""
    if isinstance(product, Product) and product.pk is None:
        return ZERO_LEVELS
    return stock.stock_levels(_product(product))


def needs_reorder_attention(product: Product, levels: StockLevels) -> bool:
    """Whether the page highlights the reorder quantity: only for a product that is
    not discontinued and whose suggested reorder quantity is above zero
    (R-inventory-021)."""
    return not product.discontinued and levels.reorder_quantity > 0


@dataclass(frozen=True)
class ProductActions:
    """What the product page offers (R-inventory-021, R-inventory-022)."""

    delete: bool
    reorder: bool
    order_history: bool
    purchase_order_history: bool


def product_actions(product: Product) -> ProductActions:
    """A product not saved yet offers no delete, reorder, order history or
    purchase-order history (R-inventory-022); a discontinued product offers no
    reorder (R-inventory-021)."""
    saved = product.pk is not None
    return ProductActions(
        delete=saved,
        reorder=saved and not product.discontinued,
        order_history=saved,
        purchase_order_history=saved,
    )


def allocate_inventory(product: Product | int, *, user: Any = None) -> list:
    """Re-run the stock allocation of the product's waiting order lines and return
    the lines whose status changed (R-inventory-007)."""
    product = _product(product)
    with transaction.atomic(), acting_for(user):
        return stock.allocate_inventory(product)


# ---------------------------------------------------------------- stock takes


class StockTakeMismatchError(ValidationError):
    """The counted quantity differs from the expected one and was not confirmed
    (R-inventory-010); carries both figures for the confirmation."""

    def __init__(self, counted: int, expected: int):
        super().__init__(
            f"R-inventory-010: the counted quantity {counted} differs from the "
            f"expected quantity {expected}. Confirm the count to save it.",
            code="R-inventory-010",
        )
        self.counted = counted
        self.expected = expected


@dataclass(frozen=True)
class StockTakeResult:
    stock_take: StockTake
    expected: int
    reallocated: list


def record_stock_take(
    product: Product | int,
    counted: int | None,
    *,
    confirmed: bool = False,
    user: Any = None,
) -> StockTakeResult:
    """Record a stock take (R-inventory-009): the counted quantity, dated by the
    system at the moment it is saved, with the product's physical stock at that
    moment as the expected quantity. Neither can be negative, and the count is
    required. A count that differs from the expected quantity needs `confirmed`
    (R-inventory-010); without it nothing is saved. After the save the product's
    stock is allocated again (R-inventory-008). Stock takes are only ever added
    (R-inventory-011)."""
    product = _product(product)
    if _blank(counted):
        refuse("R-inventory-009", "enter the counted quantity on hand.")
    counted = int(counted)
    if counted < 0:
        refuse("R-inventory-009", "the counted quantity cannot be negative.")
    with transaction.atomic(), acting_for(user):
        # The original's stock calculation gives a product without any stock take
        # its opening one first (R-inventory-002).
        stock.ensure_opening_stock_take(product)
        expected = stock.product_available(product)
        if expected < 0:
            refuse(
                "R-inventory-009",
                f"the expected quantity (physical stock {expected}) cannot be "
                "negative, so the stock take cannot be saved.",
            )
        if counted != expected and not confirmed:
            raise StockTakeMismatchError(counted, expected)
        stock_take = StockTake(
            product=product,
            stock_take_date=audit.stamp_time(),
            quantity_on_hand=counted,
            expected_quantity=expected,
        )
        _clean(stock_take, "R-inventory-009")
        stock_take.save()
        reallocated = stock.allocate_inventory(product)
    return StockTakeResult(stock_take, expected, reallocated)


# ---------------------------------------------------------------- products


def product_code(product: Product, category: ProductCategory) -> str:
    """NWT, the category code, a hyphen and the product number (R-inventory-013)."""
    return f"{CODE_PREFIX}{category.product_category_code}-{product.pk}"


def _check_product(product: Product) -> None:
    """R-inventory-012: no required field empty and a standard unit cost above
    zero."""
    missing = [
        _LABELS[name] for name in REQUIRED_FIELDS if _blank(getattr(product, name))
    ]
    if missing:
        refuse("R-inventory-012", f"fill in {', '.join(missing)}.")
    if product.standard_unit_cost <= 0:
        refuse(
            "R-inventory-012",
            "the standard unit cost must be greater than zero.",
        )


def save_product(
    product: Product,
    data: dict[str, Any],
    *,
    user: Any = None,
) -> Product:
    """Create or update a product from cleaned form data.

    The code is built from the category (R-inventory-013) when the product is created
    and whenever its category changes; a new product gets its opening stock take of
    zero, dated at its creation (R-inventory-002). Refused when a required field is
    empty, the standard unit cost is zero or less, or the code or name is taken
    (R-inventory-012)."""
    creating = product.pk is None
    stored_category = (
        None
        if creating
        else Product.objects.filter(pk=product.pk)
        .values_list("product_category_id", flat=True)
        .first()
    )
    for name, value in data.items():
        if name != "product_code":
            setattr(product, name, value)
    if creating:
        # A provisional unique code until the product has its number.
        product.product_code = f"{CODE_PREFIX}-new-{uuid.uuid4().hex[:8]}"
    _check_product(product)
    with transaction.atomic(), acting_for(user):
        _clean(product, "R-inventory-012")
        product.save()
        if creating or product.product_category_id != stored_category:
            product.product_code = product_code(product, product.product_category)
            _clean(product, "R-inventory-012")
            product.save()
        if creating:
            stock.ensure_opening_stock_take(product)
    return product


def delete_product(
    product: Product | int,
    *,
    confirmed: bool = False,
    user: Any = None,
) -> None:
    """Delete a product with its stock takes and vendor links in one step
    (R-inventory-016). Refused, with nothing deleted, while the product is on an order
    line or a purchase-order line, or when the delete is not confirmed."""
    product = _product(product)
    if OrderDetail.objects.filter(product=product).exists():
        refuse(
            "R-inventory-016",
            "the product is on an order line, so it cannot be deleted.",
        )
    if PurchaseOrderDetail.objects.filter(product=product).exists():
        refuse(
            "R-inventory-016",
            "the product is on a purchase-order line, so it cannot be deleted.",
        )
    if not confirmed:
        refuse("R-inventory-016", "confirm the delete; nothing was deleted.")
    with transaction.atomic(), acting_for(user):
        StockTake.objects.filter(product=product).delete()
        ProductVendor.objects.filter(product=product).delete()
        product.delete()


# ---------------------------------------------------------------- reorder


@dataclass(frozen=True)
class ReorderResult:
    """The purchase order a reorder resulted in; `opened_existing` when an
    outstanding purchase order was opened instead (R-inventory-017)."""

    purchase_order: PurchaseOrder
    opened_existing: bool
    line: PurchaseOrderDetail | None = None
    quantity: int | None = None


def outstanding_purchase_order(product: Product | int) -> PurchaseOrder | None:
    """The purchase order a reorder opens instead of ordering again: only when the
    product has an on-order quantity, the first Approved, New or Submitted purchase
    order containing it, by status sort order and then submitted date
    (R-inventory-017)."""
    product = _product(product)
    if stock.product_on_order(product) <= 0:
        return None
    return (
        PurchaseOrder.objects.filter(
            lines__product=product,
            status_id__in=OUTSTANDING_STATUSES,
        )
        .order_by(
            "status__sort_order",
            F("submitted_date").asc(nulls_first=True),
            "purchase_order_id",
        )
        .first()
    )


def linked_vendors(product: Product | int) -> list[Company]:
    """The vendors linked to a product, by name (R-inventory-018)."""
    links = ProductVendor.objects.filter(product=product).select_related("vendor")
    return [
        link.vendor
        for link in links.order_by("vendor__company_name", "product_vendor_id")
    ]


def choose_vendor(product: Product, vendor: Company | int | None) -> Company:
    """R-inventory-018: at least one linked vendor; the only one, or the one the user
    picked among several."""
    vendors = linked_vendors(product)
    if not vendors:
        refuse(
            "R-inventory-018",
            "a vendor is required: link a vendor to the product before reordering it.",
        )
    if len(vendors) == 1:
        return vendors[0]
    if _blank(vendor):
        refuse("R-inventory-018", "choose the vendor to reorder from.")
    vendor_id = vendor.pk if isinstance(vendor, Company) else int(vendor)
    for candidate in vendors:
        if candidate.pk == vendor_id:
            return candidate
    refuse("R-inventory-018", "choose one of the product's vendors.")


def reorder_quantity(product: Product, quantity: int | None = None) -> int:
    """R-inventory-019: the suggested reorder quantity; when that is zero the minimum
    reorder quantity; when that is also zero or blank, the quantity the user gives,
    which must be above zero."""
    suggested = stock.product_reorder_quantity(product)
    if suggested:
        return suggested
    if product.minimum_reorder_quantity:
        return product.minimum_reorder_quantity
    if _blank(quantity) or int(quantity) <= 0:
        refuse("R-inventory-019", "enter the quantity to reorder.")
    return int(quantity)


def reorder_needs(product: Product) -> dict[str, bool]:
    """What the reorder screen has to ask: a vendor choice (several vendors,
    R-inventory-018) and a quantity (no suggested or minimum quantity,
    R-inventory-019)."""
    return {
        "vendor": len(linked_vendors(product)) > 1,
        "quantity": not stock.product_reorder_quantity(product)
        and not product.minimum_reorder_quantity,
    }


def reorder_product(
    product: Product | int,
    *,
    vendor: Company | int | None = None,
    quantity: int | None = None,
    user: Any = None,
) -> ReorderResult:
    """Reorder a product (R-inventory-017 to R-inventory-021).

    A discontinued product cannot be reordered. When the product is on order and an
    Approved, New or Submitted purchase order holds it, that purchase order is
    returned unchanged. Otherwise the product goes onto the chosen vendor's oldest New
    purchase order (its line quantity raised when it is already there) or onto a new
    New purchase order, at the product's standard unit cost."""
    product = _product(product)
    if product.discontinued:
        refuse("R-inventory-021", "a discontinued product cannot be reordered.")
    existing = outstanding_purchase_order(product)
    if existing is not None:
        return ReorderResult(purchase_order=existing, opened_existing=True)
    chosen = choose_vendor(product, vendor)
    amount = reorder_quantity(product, quantity)
    try:
        with transaction.atomic(), acting_for(user):
            line = purchasing.reorder_into_purchase_order(product, chosen, amount)
    except DatabaseError as error:
        refuse(
            "R-inventory-020",
            "the reorder failed; no purchase order was changed.",
            error,
        )
    return ReorderResult(
        purchase_order=line.purchase_order,
        opened_existing=False,
        line=line,
        quantity=amount,
    )


# ---------------------------------------------------------------- categories


def save_category(
    category: ProductCategory,
    data: dict[str, Any],
    *,
    user: Any = None,
) -> ProductCategory:
    """Create or update a product category. Name and code are required and unique,
    and the code cannot change once a product belongs to the category, because
    product codes are built from it (R-inventory-014)."""
    for name, value in data.items():
        setattr(category, name, value)
    for name, label in (
        ("product_category_name", "category name"),
        ("product_category_code", "category code"),
    ):
        if _blank(getattr(category, name)):
            refuse("R-inventory-014", f"fill in the {label}.")
    if category.pk is not None:
        stored_code = (
            ProductCategory.objects.filter(pk=category.pk)
            .values_list("product_category_code", flat=True)
            .first()
        )
        in_use = Product.objects.filter(product_category=category).exists()
        if in_use and stored_code != category.product_category_code:
            refuse(
                "R-inventory-014",
                "the category code cannot change while products belong to the "
                "category, because their codes are built from it.",
            )
    with transaction.atomic(), acting_for(user):
        _clean(category, "R-inventory-014")
        category.save()
    return category


def delete_category(category: ProductCategory, *, user: Any = None) -> None:
    """Delete a product category; refused while any product belongs to it
    (R-inventory-015)."""
    if Product.objects.filter(product_category=category).exists():
        refuse(
            "R-inventory-015",
            "products belong to this category, so it cannot be deleted.",
        )
    with transaction.atomic(), acting_for(user):
        category.delete()


# ---------------------------------------------------------------- vendor links


def add_product_vendor(
    product: Product | int,
    vendor: Company | int | None,
    *,
    user: Any = None,
) -> ProductVendor:
    """Link a vendor to a product: both required, the vendor an existing company, and
    each vendor linked to a product only once (R-inventory-029)."""
    product = _product(product)
    if _blank(vendor):
        refuse("R-inventory-029", "choose a vendor.")
    vendor_id = vendor.pk if isinstance(vendor, Company) else int(vendor)
    if not Company.objects.filter(pk=vendor_id).exists():
        refuse("R-inventory-029", "the vendor must be an existing company.")
    if ProductVendor.objects.filter(product=product, vendor_id=vendor_id).exists():
        refuse("R-inventory-029", "this vendor is already linked to the product.")
    link = ProductVendor(product=product, vendor_id=vendor_id)
    with transaction.atomic(), acting_for(user):
        _clean(link, "R-inventory-029")
        link.save()
    return link


def remove_product_vendor(link: ProductVendor, *, user: Any = None) -> None:
    """Remove one vendor link of a product."""
    with transaction.atomic(), acting_for(user):
        link.delete()


def save_record(record: Product, data: dict[str, Any]) -> Product:
    """The skeleton's save entry point: the product save (R-inventory-012)."""
    return save_product(record, data)
