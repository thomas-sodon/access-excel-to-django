# Domain functions shared by several areas

The feature areas (orders, inventory, purchasing, reports) call these functions
instead of writing their own copy. Each figure comes as a queryset helper, which adds
an annotation that works in `filter()`, `order_by()` and `values()` on PostgreSQL
and SQL Server, and as a plain function for one object. `tests/test_forms_agree.py`
shows that the two forms agree. `tests/test_rules.py` holds one test per rule, with
the rule id first in the docstring.

Rules: the statements are in `analysis/rules.md`. Writes are stamped with the name
that `people.acting_for(request.user)` sets. Callers wrap them in
`transaction.atomic()`.

## Stock figures and allocation (`inventory.py`)

A product argument is a `Product` or its key. A queryset argument is a `Product`
queryset.

| Name | Signature | Rule ids | Areas | Replaces |
|---|---|---|---|---|
| `with_product_allocated` | `(queryset) -> queryset` with `product_allocated` | R-inventory-003 | inventory, purchasing | modInventory.ProductAllocated |
| `product_allocated` | `(product) -> int` | R-inventory-003 | inventory, purchasing | modInventory.ProductAllocated |
| `with_product_no_stock` | `(queryset) -> queryset` with `product_no_stock` | R-inventory-003 | inventory, purchasing | modInventory.ProductNoStock |
| `product_no_stock` | `(product) -> int` | R-inventory-003 | inventory, purchasing | modInventory.ProductNoStock |
| `with_product_on_order` | `(queryset) -> queryset` with `product_on_order` | R-inventory-004 | inventory, purchasing | modInventory.ProductOnOrder, qryPOProducts_ByStatus |
| `product_on_order` | `(product) -> int` | R-inventory-004 | inventory, purchasing | modInventory.ProductOnOrder |
| `with_last_stock_take` | `(queryset) -> queryset` with `last_stock_take_date`, `last_stock_take_quantity`, `stock_as_of` | R-inventory-002 | inventory, purchasing, orders | modInventory.ProductLastStockTakeDate, modInventory.ProductLastStockTakeQuantity |
| `last_stock_take` | `(product) -> (datetime or None, int)` | R-inventory-002 | inventory, purchasing, orders | modInventory.ProductLastStockTakeDate, modInventory.ProductLastStockTakeQuantity |
| `stock_as_of` | `(product) -> datetime` | R-inventory-002 | inventory, purchasing, orders | modInventory.ProductLastStockTakeDate |
| `ensure_opening_stock_take` | `(product) -> StockTake or None` | R-inventory-002 | inventory, purchasing, orders | modInventory.ProductLastStockTakeDate (its insert) |
| `with_product_available` | `(queryset) -> queryset` with `product_available` (and `product_bought`, `product_sold`) | R-inventory-001 | orders, inventory, purchasing | modInventory.ProductAvailable, modInventory.ProductBought, modInventory.ProductSold |
| `product_available` | `(product) -> int` | R-inventory-001 | orders, inventory, purchasing | modInventory.ProductAvailable |
| `product_bought` | `(product, as_of) -> int` | R-inventory-001 | inventory, purchasing | modInventory.ProductBought |
| `product_sold` | `(product, as_of) -> int` | R-inventory-001 | inventory, orders | modInventory.ProductSold |
| `with_product_to_sell` | `(queryset) -> queryset` with `product_to_sell` | R-inventory-005 | inventory, purchasing | modInventory.ProductToSell |
| `product_to_sell` | `(product) -> int` | R-inventory-005 | inventory, purchasing | modInventory.ProductToSell |
| `with_product_reorder_quantity` | `(queryset) -> queryset` with `product_reorder_quantity` | R-inventory-006 | inventory, purchasing | modInventory.ProductReorderQuantity |
| `product_reorder_quantity` | `(product) -> int` | R-inventory-006 | inventory, purchasing | modInventory.ProductReorderQuantity |
| `with_stock_levels` | `(queryset) -> queryset` with every annotation above | R-inventory-001, R-inventory-003, R-inventory-004, R-inventory-005, R-inventory-006 | inventory, purchasing | qryProductList (its computed columns) |
| `stock_levels` | `(product) -> StockLevels` | R-inventory-001, R-inventory-003, R-inventory-004, R-inventory-005, R-inventory-006 | inventory, purchasing | Form_frmProductDetail.CalculateLevels |
| `allocate_inventory` | `(product) -> list[OrderDetail]` (the lines whose status changed) | R-inventory-007 | orders, inventory, purchasing | modInventory.AllocateInventory |

Notes:

- Physical stock is counted from the latest stock take. When two stock takes share
  the latest date and time, the larger count wins, as the reference rewrite takes
  `Max`. A product without a stock take counts from its added date, or from now when
  that is blank. The plain figures never write. `ensure_opening_stock_take` writes the
  opening zero stock take, and `allocate_inventory` calls it first, as the original's
  stock calculation did. Creating the opening stock take when the product is created
  (Q-inventory-002) belongs to the inventory area.
- `allocate_inventory` saves only the lines whose status changes. The original also
  rewrote the unchanged lines, which only refreshed their modified stamps.

## Purchase orders (`purchasing.py`)

| Name | Signature | Rule ids | Areas | Replaces |
|---|---|---|---|---|
| `start_purchase_order` | `(vendor, **fields) -> PurchaseOrder` (status New) | R-purchasing-001 | purchasing, inventory | Form_frmPurchaseOrderDetails.Form_BeforeInsert, modPurchaseOrders.ReorderProduct (its insert) |
| `add_purchase_order_line` | `(purchase_order, product, quantity, unit_cost) -> PurchaseOrderDetail` | R-purchasing-020 | purchasing, inventory | modPurchaseOrders.AddPurchaseOrderDetail |
| `oldest_new_purchase_order` | `(vendor) -> PurchaseOrder or None` | R-inventory-020 | inventory, purchasing | Form_frmProductDetail.cmdReorderProduct_Click (its lookup of the oldest New purchase order) |
| `reorder_into_purchase_order` | `(product, vendor, quantity) -> PurchaseOrderDetail` | R-inventory-020, R-purchasing-001, R-purchasing-020 | inventory, purchasing | modPurchaseOrders.ReorderProduct |

The callers keep their own checks, which belong to one area each: lines only while
the purchase order is New, the minimum reorder quantity, and the vendor choice and
quantity prompts of a reorder.

## Order amounts (`sales.py`)

| Name | Signature | Rule ids | Areas | Replaces |
|---|---|---|---|---|
| `line_amount_expression` | `(prefix="") -> expression` (double) | R-orders-022, R-reports-005 | orders, reports | the line amount expression of qryOrderTotal, qryTotalSalesByProduct, qryrptSalesByProduct_ByMonth and qryrptSalesByProduct_ByQuarter |
| `with_line_amount` | `(OrderDetail queryset) -> queryset` with `line_amount` | R-orders-022 | orders, reports | the same |
| `line_amount` | `(line) -> float or None` | R-orders-022 | orders, reports | the same |
| `order_total_expression` | `(order_ref="pk") -> Subquery` (double, null without lines) | R-orders-023, R-reports-004 | orders, reports | qryOrderTotal |
| `with_order_total` | `(Order queryset) -> queryset` with `order_total` | R-orders-023, R-reports-004 | orders, reports | qryOrderTotal |
| `order_total` | `(order) -> float or None` | R-orders-023 | orders, reports | qryOrderTotal |

The amounts are doubles, as the original computes them. Round them for output with
`core.vbacompat.ccur` (four places, half-even). A line with a blank discount has no
amount and adds nothing to a sum.

SQL Server refuses an aggregate over a subquery. Never `Sum()` the `order_total`
annotation inside a `values(...).annotate(...)` grouping. Group the order lines
instead: `OrderDetail.objects.values("order__employee").annotate(total=Sum(line_amount_expression()))`.
A plain `aggregate(Sum("order_total"))` works on both databases.

## The signed-in employee and employee names (`people.py`)

| Name | Signature | Rule ids | Areas | Replaces |
|---|---|---|---|---|
| `signed_in_employee` | `(user) -> Employee or None` | R-orders-001, R-purchasing-004 | orders, purchasing | modGlobal.Get_UserID |
| `stamp_name` | `(user) -> str` | R-orders-031 | orders, inventory, purchasing | modTableDataMacros.GetAuditFieldsUserName |
| `acting_for` | `(user) -> context manager` (`legacy.audit.acting_as` with the stamp name) | R-orders-031 | orders, inventory, purchasing | modTableDataMacros.GetAuditFieldsUserName |
| `full_name_expression` | `(prefix="") -> expression` | R-orders-043 | orders, reports, purchasing | the FullNameFNLN expression of qryEmployees and qryrptSalesByEmployee |
| `with_full_name` | `(queryset, prefix="", name="full_name_fnln") -> queryset` | R-orders-043 | orders, reports, purchasing | the same |
| `full_name` | `(employee) -> str or None` | R-orders-043 | orders, reports, purchasing | the same |

A web user is linked to the employee whose e-mail address equals the user's e-mail
address, ignoring case. When several match, the lowest employee number wins. A user
without an employee record has no employee (no salesperson, no submitter). Their
stamps carry their own name, or their e-mail address when the name is blank. Wrap
every service write in `with acting_for(request.user):`.

The full name is first name, a space, last name. A blank part counts as empty text, so
the space is always there. The stamp name of `legacy.audit.employee_full_name` is a
separate function and leaves blank parts out.

## System settings (`system_settings.py`)

| Name | Signature | Rule ids | Areas | Replaces |
|---|---|---|---|---|
| `system_setting` | `(code) -> str or None` | R-orders-001, R-purchasing-010 | orders, purchasing | modStartup.GetSystemSetting |
| `sales_tax_rate` | `() -> float` | R-orders-001 | orders | modStartup.GetSystemSetting (sales tax rate) |
| `vendor_tax_rate` | `() -> float` | R-purchasing-010 | purchasing | modStartup.GetSystemSetting (vendor tax rate) |

Both rates are stored as whole thousandths and read divided by 1000. A missing,
blank or non-numeric setting reads as 0.

## Not here

- Data macros with side effects: none. The S4.models notes list 20 data macros, and
  all of them are Before Change audit stamps (legacy/audit.py). There are no After
  Insert, After Update or After Delete macros.
- Working days (Excel WORKDAY): no rule of this application uses them.
- Invoice tax and totals belong only to the orders area, and purchase order amounts
  only to the purchasing area. Each area builds them on `order_total` or its own line
  sums.
