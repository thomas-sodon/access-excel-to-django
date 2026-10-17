"""Services of the Purchasing and receiving area: one function per services[] entry
of analysis/interfaces.md for this area, plus the record saves of the purchase order
and its lines that the workflow purchase_order_to_stock names.

Views call a service for every write. A service checks its rules first; a refused
action raises ValidationError with a plain message that names the rule id and
changes nothing. Shared calculations come from app/northwind/domain/ (stock figures,
the purchase order line merge, the signed-in employee, the vendor tax rate). Every
write runs inside transaction.atomic() and domain.people.acting_for(user), so the
audit stamps carry the signed-in user's name, or System for a job without a user
(R-purchasing-027).

There are no data macros with side effects on this area's tables: the S4.models
notes list only Before Change audit stamps, which legacy/audit.py applies.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from decimal import Decimal
from typing import TYPE_CHECKING
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction

from northwind.core import vbacompat
from northwind.core.local.roles import APPROVE_PURCHASE_ORDERS
from northwind.domain import inventory
from northwind.domain import purchasing as domain_purchasing
from northwind.domain.people import acting_for
from northwind.domain.people import signed_in_employee
from northwind.domain.system_settings import vendor_tax_rate
from northwind.legacy.choices import PaymentMethod
from northwind.legacy.choices import PurchaseOrderStatusCode as Status
from northwind.legacy.models import Company
from northwind.legacy.models import Product
from northwind.legacy.models import PurchaseOrder
from northwind.legacy.models import PurchaseOrderDetail

from . import queries

if TYPE_CHECKING:
    import datetime as dt

#: The rule ids the refusals name.
R_002 = "R-purchasing-002"
R_004 = "R-purchasing-004"
R_005 = "R-purchasing-005"
R_007 = "R-purchasing-007"
R_009 = "R-purchasing-009"
R_011 = "R-purchasing-011"
R_012 = "R-purchasing-012"
R_013 = "R-purchasing-013"
R_014 = "R-purchasing-014"
R_015 = "R-purchasing-015"
R_019 = "R-purchasing-019"
R_020 = "R-purchasing-020"
R_021 = "R-purchasing-021"
R_023 = "R-purchasing-023"

#: The fixed sequence of purchase order statuses (R-purchasing-003).
WORKFLOW = (
    Status.NEW,
    Status.SUBMITTED,
    Status.APPROVED,
    Status.RECEIVED,
    Status.CLOSED,
)

#: Fields the purchase order edit screen may change, by status (R-purchasing-011).
#: The vendor only before the first save (key None); nothing once Closed.
EDITABLE_FIELDS: dict[int | None, tuple[str, ...]] = {
    None: ("vendor", "notes"),
    Status.NEW: ("notes",),
    Status.SUBMITTED: ("notes",),
    Status.APPROVED: ("received_date", "notes"),
    Status.RECEIVED: ("shipping_fee", "payment_method", "notes"),
    Status.CLOSED: (),
}

PAYMENT_METHOD_MESSAGE = "the payment method must be credit card, check or cash."


def refuse(rule: str, message: str) -> ValidationError:
    """A refusal that names its rule id."""
    return ValidationError(f"{rule}: {message}", code=rule)


def now() -> dt.datetime:
    """The current date and time to the second (the original's Now)."""
    return vbacompat.now()


def _status_label(status_id: int | None) -> str:
    return Status(status_id).label if status_id in Status.values else "unsaved"


def _require_status(po: PurchaseOrder, status: int, rule: str, action: str) -> None:
    if po.status_id != status:
        msg = (
            f"only a {Status(status).label} purchase order can be {action}; this one "
            f"is {_status_label(po.status_id)}."
        )
        raise refuse(rule, msg)


def _key(value: Any) -> int | None:
    """The primary key of a model instance or a key value; None for a blank."""
    if value in (None, ""):
        return None
    return int(getattr(value, "pk", value))


def _reload(po: PurchaseOrder | int) -> PurchaseOrder:
    return PurchaseOrder.objects.get(pk=_key(po))


def steps_done(po: PurchaseOrder | None) -> list[tuple[str, bool]]:
    """The four workflow steps (Submitted, Approved, Received, Closed) and whether
    each is done, as the purchase order screen shows them (R-purchasing-003)."""
    status_id = None if po is None or po.pk is None else po.status_id
    reached = WORKFLOW.index(status_id) if status_id in WORKFLOW else -1
    return [(step.label, reached >= WORKFLOW.index(step)) for step in WORKFLOW[1:]]


def editable_fields(po: PurchaseOrder | None) -> tuple[str, ...]:
    """The fields that can still be edited on the purchase order (R-purchasing-011,
    R-purchasing-015)."""
    if po is None or po.pk is None:
        return EDITABLE_FIELDS[None]
    return EDITABLE_FIELDS.get(po.status_id, ())


def lines_editable(po: PurchaseOrder | None) -> bool:
    """Lines can be added, changed or deleted only while the purchase order is New
    or not yet saved (R-purchasing-012)."""
    return po is None or po.pk is None or po.status_id == Status.NEW


# ------------------------------------------------------------ the purchase order


def _create_purchase_order(data: dict[str, Any], user: Any) -> PurchaseOrder:
    vendor_id = _key(data.get("vendor"))
    if vendor_id is None:
        raise refuse(R_002, "choose the vendor first.")
    if not Company.objects.filter(pk=vendor_id).exists():
        raise refuse(R_002, "the vendor is not an existing company.")
    unknown = set(data) - {*EDITABLE_FIELDS[None], "status", "status_id"}
    if unknown:
        msg = f"a new purchase order cannot set {', '.join(sorted(unknown))}."
        raise refuse(R_011, msg)
    with transaction.atomic(), acting_for(user):
        # start_purchase_order ignores any status: always New (R-purchasing-001).
        return domain_purchasing.start_purchase_order(
            vendor_id,
            notes=data.get("notes") or None,
        )


def save_purchase_order(
    po: PurchaseOrder,
    data: dict[str, Any],
    user: Any = None,
) -> PurchaseOrder:
    """Create or update a purchase order from form data.

    - R-purchasing-001: a new purchase order always starts in status New.
    - R-purchasing-002: the vendor (an existing company) is required; the status is
      always set (New, then only by the workflow actions).
    - R-purchasing-011: only the fields that are still editable in the current status
      may change; a Closed purchase order is read-only.
    - R-purchasing-015: the vendor is chosen before the first save and fixed after it.
    """
    if po.pk is None:
        return _create_purchase_order(dict(data), user)

    stored = _reload(po)
    if stored.status_id == Status.CLOSED:
        raise refuse(R_011, "a Closed purchase order is read-only.")
    data = {name: (None if value == "" else value) for name, value in data.items()}
    if "vendor" in data:
        vendor_id = _key(data.pop("vendor"))
        if vendor_id is not None and vendor_id != stored.vendor_id:
            raise refuse(
                R_015,
                "the vendor of a saved purchase order cannot be changed.",
            )
    changed = {
        name: value for name, value in data.items() if getattr(stored, name) != value
    }
    locked = sorted(set(changed) - set(editable_fields(stored)))
    if locked:
        msg = (
            f"{', '.join(locked)} cannot be edited while the purchase order is "
            f"{_status_label(stored.status_id)}."
        )
        raise refuse(R_011, msg)
    method = changed.get("payment_method")
    if method is not None and method not in PaymentMethod.values:
        raise refuse(R_009, PAYMENT_METHOD_MESSAGE)
    if not changed:
        return stored
    with transaction.atomic(), acting_for(user):
        for name, value in changed.items():
            setattr(stored, name, value)
        stored.full_clean()
        stored.save()
    return stored


def submit_purchase_order(po: PurchaseOrder | int, user: Any = None) -> PurchaseOrder:
    """Submit a New purchase order (R-purchasing-003, R-purchasing-004): the
    signed-in user's employee becomes the submitter, now the submitted date and
    time, and the status Submitted."""
    po = _reload(po)
    _require_status(po, Status.NEW, R_004, "submitted")
    with transaction.atomic(), acting_for(user):
        po.submitted_by = signed_in_employee(user)
        po.submitted_date = now()
        po.status_id = Status.SUBMITTED
        po.save()
    return po


def can_approve(user: Any) -> bool:
    """Whether the user holds the approve-purchase-order privilege
    (R-purchasing-005); core/local/roles.py grants it to the approver role."""
    return bool(user is not None and user.has_perm(APPROVE_PURCHASE_ORDERS))


def _allocate_products(po: PurchaseOrder) -> None:
    """Re-run stock allocation for every product on the purchase order
    (R-purchasing-006); the allocation itself is the domain's (R-inventory-007)."""
    product_ids = (
        PurchaseOrderDetail.objects.filter(purchase_order_id=po.pk)
        .order_by("purchase_order_detail_id")
        .values_list("product_id", flat=True)
    )
    for product_id in dict.fromkeys(product_ids):
        inventory.allocate_inventory(product_id)


def approve_purchase_order(po: PurchaseOrder | int, user: Any = None) -> PurchaseOrder:
    """Approve a Submitted purchase order (R-purchasing-003, R-purchasing-005,
    R-purchasing-006): only a user with the approve-purchase-order privilege, who
    may also be its submitter. Records the approver and now, sets Approved and
    re-runs the stock allocation of its products."""
    po = _reload(po)
    _require_status(po, Status.SUBMITTED, R_005, "approved")
    if not can_approve(user):
        raise refuse(
            R_005,
            "you do not have the privilege to approve purchase orders.",
        )
    with transaction.atomic(), acting_for(user):
        po.approved_by = signed_in_employee(user)
        po.approved_date = now()
        po.status_id = Status.APPROVED
        po.save()
        _allocate_products(po)
    return po


def receive_purchase_order(
    po: PurchaseOrder | int,
    *,
    confirmed: bool,
    user: Any = None,
) -> PurchaseOrder:
    """Receive an Approved purchase order after the user confirms posting it to
    inventory (R-purchasing-003, R-purchasing-006, R-purchasing-007,
    R-purchasing-008). The whole order is received at once: the purchase order and
    every line get now as the received date and time, the status becomes Received,
    and the stock allocation of its products is re-run."""
    po = _reload(po)
    _require_status(po, Status.APPROVED, R_007, "received")
    if not confirmed:
        raise refuse(
            R_007,
            "confirm posting the purchase order to inventory; nothing was received.",
        )
    with transaction.atomic(), acting_for(user):
        received = now()
        po.received_date = received
        po.status_id = Status.RECEIVED
        po.save()
        for line in PurchaseOrderDetail.objects.filter(purchase_order_id=po.pk):
            line.received_date = received
            line.save(update_fields=["received_date"])
        _allocate_products(po)
    return po


@dataclass(frozen=True)
class Amounts:
    """The amounts of a purchase order (R-purchasing-010): subtotal, tax and total
    as Currency values, None where the original shows a blank (no lines)."""

    subtotal: Decimal | None
    tax: Decimal | None
    total: Decimal | None
    tax_rate: float = 0.0
    shipping_fee: Decimal | None = None


def purchase_order_amounts(
    po: PurchaseOrder | int,
    shipping_fee: Decimal | None = None,
) -> Amounts:
    """Subtotal = the extended cost (sum of quantity times unit cost,
    R-purchasing-024); tax = the system-wide vendor tax rate times the subtotal
    (shipping is not taxed); total = subtotal + tax + shipping fee, a missing
    shipping fee counted as zero (R-purchasing-010). A purchase order without lines
    has no subtotal, tax or total, as on the original screen. `shipping_fee`
    overrides the stored fee (the close action computes with the fee it stores).
    Tax and total are computed as doubles, as the original's screen does, and
    rounded to Currency (four places, half-even) with core.vbacompat.ccur."""
    row = (
        queries.with_extended_cost(PurchaseOrder.objects.filter(pk=_key(po)))
        .values(queries.EXTENDED_COST, "shipping_fee")
        .get()
    )
    subtotal = row[queries.EXTENDED_COST]
    fee = row["shipping_fee"] if shipping_fee is None else shipping_fee
    rate = vendor_tax_rate()
    if subtotal is None:
        return Amounts(None, None, None, rate, fee)
    tax_value = rate * float(subtotal)
    total_value = float(subtotal) + tax_value + float(fee or 0)
    return Amounts(
        vbacompat.ccur(subtotal),
        vbacompat.ccur(tax_value),
        vbacompat.ccur(total_value),
        rate,
        fee,
    )


def close_purchase_order(
    po: PurchaseOrder | int,
    shipping_fee: Decimal | None = None,
    payment_method: str | None = None,
    user: Any = None,
) -> PurchaseOrder:
    """Close a Received purchase order (R-purchasing-003, R-purchasing-009,
    R-purchasing-010). The shipping fee and the payment method (credit card, check
    or cash) must be filled in, given here or already stored. Stores now as the
    payment date, the computed tax as the tax amount and the computed total as the
    payment amount, and sets Closed."""
    po = _reload(po)
    _require_status(po, Status.RECEIVED, R_009, "closed")
    fee = po.shipping_fee if shipping_fee is None else shipping_fee
    method = payment_method or po.payment_method
    missing = [
        label
        for label, value in (("shipping fee", fee), ("payment method", method))
        if value in (None, "")
    ]
    if missing:
        msg = f"fill in the {' and the '.join(missing)} before closing."
        raise refuse(R_009, msg)
    if method not in PaymentMethod.values:
        raise refuse(R_009, PAYMENT_METHOD_MESSAGE)
    amounts = purchase_order_amounts(po, shipping_fee=fee)
    with transaction.atomic(), acting_for(user):
        po.shipping_fee = fee
        po.payment_method = method
        po.payment_date = now()
        po.tax_amount = amounts.tax
        po.payment_amount = amounts.total
        po.status_id = Status.CLOSED
        po.save()
    return po


def delete_purchase_order(po: PurchaseOrder | int, user: Any = None) -> None:
    """Delete a New or Submitted purchase order with all its lines
    (R-purchasing-014); refused in any later status."""
    po = _reload(po)
    if po.status_id not in (Status.NEW, Status.SUBMITTED):
        msg = (
            "only a New or Submitted purchase order can be deleted; this one is "
            f"{_status_label(po.status_id)}."
        )
        raise refuse(R_014, msg)
    with transaction.atomic(), acting_for(user):
        po.delete()


# ------------------------------------------------------------------ lines


@dataclass(frozen=True)
class LineResult:
    """A saved line and the warnings the user should see (never a refusal)."""

    line: PurchaseOrderDetail
    warnings: list[str] = field(default_factory=list)


def line_defaults(product: Product | int) -> tuple[int, Decimal]:
    """The quantity and unit cost a line gets when its product is chosen: the
    product's computed reorder quantity and its standard unit cost
    (R-purchasing-018). The user may change both before saving."""
    product_id = _key(product)
    cost = Product.objects.values_list("standard_unit_cost", flat=True).get(
        pk=product_id,
    )
    return inventory.product_reorder_quantity(product_id), cost


def _check_lines_editable(po: PurchaseOrder | None) -> PurchaseOrder:
    if po is None or po.pk is None:
        raise refuse(
            R_013,
            "complete and save the purchase order before entering line items.",
        )
    po = _reload(po)
    if not lines_editable(po):
        msg = (
            "line items can be added, changed or deleted only while the purchase "
            f"order is New; this one is {_status_label(po.status_id)}."
        )
        raise refuse(R_012, msg)
    return po


def _check_line(
    product: Product | int | None,
    quantity: Any,
    unit_cost: Any,
) -> tuple[Product, list[str]]:
    """R-purchasing-019: product, quantity and unit cost are required and the
    product must exist; a quantity below the minimum reorder quantity is refused;
    a quantity that leaves the product below its target level only warns."""
    missing = [
        label
        for label, value in (
            ("product", product),
            ("quantity", quantity),
            ("unit cost", unit_cost),
        )
        if value in (None, "")
    ]
    if missing:
        msg = f"fill in the {', '.join(missing)} of the line."
        raise refuse(R_019, msg)
    found = Product.objects.filter(pk=_key(product)).first()
    if found is None:
        raise refuse(R_019, "the product does not exist.")
    minimum = found.minimum_reorder_quantity or 0
    if int(quantity) < minimum:
        msg = f"the quantity must be at least the minimum reorder quantity, {minimum}."
        raise refuse(R_019, msg)
    warnings = []
    if found.target_level is not None:
        short = found.target_level - inventory.product_to_sell(found) - int(quantity)
        if short > 0:
            warnings.append(
                "R-purchasing-019: with this quantity the product stays below its "
                f"target level of {found.target_level}; {short} more would reach "
                "it. The line is saved.",
            )
    return found, warnings


def add_purchase_order_line(
    po: PurchaseOrder | None,
    product: Product | int | None,
    quantity: Any,
    unit_cost: Any,
    user: Any = None,
) -> LineResult:
    """Add a line to a New purchase order (R-purchasing-012, R-purchasing-013,
    R-purchasing-019, R-purchasing-020). A product already on the purchase order
    gets the quantity added to its line, which keeps its unit cost."""
    po = _check_lines_editable(po)
    found, warnings = _check_line(product, quantity, unit_cost)
    with transaction.atomic(), acting_for(user):
        line = domain_purchasing.add_purchase_order_line(
            po,
            found,
            int(quantity),
            Decimal(unit_cost),
        )
    return LineResult(line, warnings)


def update_purchase_order_line(
    line: PurchaseOrderDetail | int,
    product: Product | int | None,
    quantity: Any,
    unit_cost: Any,
    user: Any = None,
) -> LineResult:
    """Change a line of a New purchase order (R-purchasing-012, R-purchasing-019).
    A second line for a product already on the purchase order is refused
    (R-purchasing-020)."""
    stored = PurchaseOrderDetail.objects.get(pk=_key(line))
    _check_lines_editable(stored.purchase_order)
    found, warnings = _check_line(product, quantity, unit_cost)
    duplicate = (
        PurchaseOrderDetail.objects.filter(
            purchase_order_id=stored.purchase_order_id,
            product_id=found.pk,
        )
        .exclude(pk=stored.pk)
        .exists()
    )
    if duplicate:
        raise refuse(
            R_020,
            "this product is already on the purchase order; change that line.",
        )
    try:
        with transaction.atomic(), acting_for(user):
            stored.product = found
            stored.quantity = int(quantity)
            stored.unit_cost = Decimal(unit_cost)
            stored.save()
    except IntegrityError as error:
        raise refuse(
            R_020,
            "the purchase order holds at most one line per product.",
        ) from error
    return LineResult(stored, warnings)


def delete_purchase_order_line(
    line: PurchaseOrderDetail | int,
    user: Any = None,
) -> None:
    """Delete a line of a New purchase order (R-purchasing-012)."""
    stored = PurchaseOrderDetail.objects.get(pk=_key(line))
    _check_lines_editable(stored.purchase_order)
    with transaction.atomic(), acting_for(user):
        stored.delete()


def add_no_stock_lines(po: PurchaseOrder | None, user: Any = None) -> int:
    """Add a line for every product the vendor supplies that is not on the purchase
    order yet and has at least one customer order line waiting in No Stock; each new
    line gets the product's reorder quantity and standard unit cost
    (R-purchasing-021, R-purchasing-020). Refused on an unsaved purchase order, and,
    like every line change, once the purchase order is past New (R-purchasing-012).
    Returns the number of lines added."""
    if po is None or po.pk is None:
        raise refuse(
            R_021,
            "save the purchase order first; then all No Stock products can be added.",
        )
    po = _check_lines_editable(po)
    on_the_order = PurchaseOrderDetail.objects.filter(
        purchase_order_id=po.pk,
    ).values("product_id")
    candidates = inventory.with_product_reorder_quantity(
        queries.vendor_products(po.vendor_id).exclude(pk__in=on_the_order),
    ).filter(product_no_stock__gt=0)
    rows = list(
        candidates.values_list(
            "product_id",
            "product_reorder_quantity",
            "standard_unit_cost",
        ),
    )
    with transaction.atomic(), acting_for(user):
        for product_id, quantity, cost in rows:
            domain_purchasing.add_purchase_order_line(po, product_id, quantity, cost)
    return len(rows)


# ------------------------------------------------------- vendor choice dialog


def vendor_choices(product: Product | int) -> list[Company]:
    """The vendors offered when the product is reordered, by name
    (R-purchasing-023). A product without a vendor cannot be reordered."""
    choices = list(queries.product_vendors(product))
    if not choices:
        raise refuse(
            R_023,
            "the product has no vendor, so it cannot be reordered.",
        )
    return choices


def choose_vendor(product: Product | int, vendor: Company | int | None) -> Company:
    """The vendor confirmed in the vendor dialog (R-purchasing-023): a product with
    exactly one vendor needs no choice; otherwise the choice is required and must be
    one of the product's vendors."""
    choices = vendor_choices(product)
    vendor_id = _key(vendor)
    if vendor_id is None:
        if len(choices) == 1:
            return choices[0]
        raise refuse(R_023, "select a vendor, then OK (or Cancel).")
    for choice in choices:
        if choice.pk == vendor_id:
            return choice
    raise refuse(R_023, "the vendor does not supply this product.")
