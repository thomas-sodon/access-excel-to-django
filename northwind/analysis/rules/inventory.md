# Products and Inventory (inventory): business rules

Engagement `northwind-demo`, spec version 1.0, area status **kept**. Generated from `analysis/rules/inventory.json`; the JSON file is the source of truth.

## Area summary

This area covers the product catalogue (products, categories, product-vendor links), stock takes, and the stock figures the rest of the app relies on: physical stock, allocated, no-stock, on-order, quantity to sell and the suggested reorder quantity. It also owns stock allocation to order lines and the reorder action that creates or extends a purchase order. It carries the must-keep item *inventory levels and restocking* (workflow `inventory_restock`) and supplies the stock-update half of *purchase order, receiving, stock update*: received purchase-order lines raise physical stock (R-inventory-001) and allocation re-runs (R-inventory-007).

- Objects in scope: 85 (keep 68, drop 17, out of scope 0)
- Tables: ProductCategories, ProductVendors, Products, StockTake
- Forms: frmProductDetail, frmProductList, sfrmProductCategories, sfrmProductDetail_Orders, sfrmProductDetail_PurchaseOrders, sfrmProductDetail_StockTake, sfrmProductDetail_Vendors
- Reports: none
- Queries: 14; procedures: 56; data macros: 4
- Rules: 30; open questions: 8

## Rules

Test kind: `rule` gets a test in `app/northwind/inventory/tests/test_rules.py`; `equivalence` is proven by the equivalence units of its query sources; `e2e` is proven by the end-to-end workflow tests.

| ID | Statement | Trigger | Sources | Tables | Confidence | Test | Questions |
|---|---|---|---|---|---|---|---|
| R-inventory-001 | A product's physical stock (available quantity) is the quantity counted at its most recent stock take, plus every purchase-order line quantity for the product received at or after that stock take's date and time, minus every order line quantity for the product whose order was invoiced at or after that moment. Orders with no invoice date are not counted as sold, and purchase-order lines with no received date are not counted as bought. | `procedure:modInventory.ProductAvailable` | procedure: modInventory.ProductAvailable<br>procedure: modInventory.ProductSold<br>procedure: modInventory.ProductBought<br>procedure: modInventory.ProductLastStockTakeQuantity | StockTake, PurchaseOrderDetails, OrderDetails, Orders | high | rule | Q-inventory-008 |
| R-inventory-002 | The stock take that counts for a product is the one with the latest date and time. When a product has no stock take at all, an opening stock take with quantity zero is created for it, dated at the moment the product was added (or now when that is unknown), so every product always has a starting point for its stock figures. | `procedure:modInventory.ProductLastStockTakeDate` | procedure: modInventory.ProductLastStockTakeDate<br>procedure: modInventory.ProductLastStockTakeQuantity | StockTake, Products | high | rule | Q-inventory-002 |
| R-inventory-003 | A product's allocated quantity is the total quantity of its order lines in the Allocated line status, and its no-stock quantity is the total quantity of its order lines in the No Stock line status; a product with no such lines has zero. | `procedure:modInventory.OrderQuantity_ByStatus` | procedure: modInventory.OrderQuantity_ByStatus<br>procedure: modInventory.ProductAllocated<br>procedure: modInventory.ProductNoStock | OrderDetails | high | rule | - |
| R-inventory-004 | A product's on-order quantity is the total quantity of the product on purchase-order lines whose purchase order is in the Approved status. Purchase orders that are New, Submitted, Received or Closed do not count. | `procedure:modInventory.ProductOnOrder` | procedure: modInventory.ProductOnOrder<br>query: qryPOProducts_ByStatus | PurchaseOrders, PurchaseOrderDetails | high | rule | Q-inventory-001 |
| R-inventory-005 | A product's quantity to sell is its physical stock (R-inventory-001) minus its allocated quantity (R-inventory-003). It can be negative. | `procedure:modInventory.ProductToSell` | procedure: modInventory.ProductToSell | StockTake, PurchaseOrderDetails, OrderDetails, Orders | high | rule | - |
| R-inventory-006 | The suggested reorder quantity compares supply (quantity to sell plus on-order quantity) with demand (no-stock quantity plus the product's target level, a blank target counting as zero). When supply covers demand the suggestion is the product's minimum reorder quantity (1 when blank). Otherwise it is the shortfall (demand minus supply), raised to the minimum reorder quantity when the shortfall is smaller. | `procedure:modInventory.ProductReorderQuantity` | procedure: modInventory.ProductReorderQuantity | Products, OrderDetails, PurchaseOrders, PurchaseOrderDetails, StockTake, Orders | high | rule | Q-inventory-001 |
| R-inventory-007 | Allocating stock to orders for a product goes through its order lines in the Allocated, No Stock or On Order line status, oldest order date first (lower order number first on a tie). A line becomes Allocated only if its whole quantity fits in the physical stock still unallocated; otherwise it becomes On Order if its whole quantity fits in the remaining physical stock plus the on-order quantity; otherwise it becomes No Stock. Lines are never part-allocated, and a later smaller line can be allocated when an earlier larger one could not. | `procedure:modInventory.AllocateInventory` | procedure: modInventory.AllocateInventory | OrderDetails, Orders | high | rule | - |
| R-inventory-008 | Saving a stock take re-runs the stock allocation (R-inventory-007) for that product, so order line statuses follow the new count straight away. | `form:sfrmProductDetail_StockTake.AfterUpdate` | procedure: Form_sfrmProductDetail_StockTake.Form_AfterUpdate | StockTake, OrderDetails | high | rule | - |
| R-inventory-009 | A stock take records the counted quantity on hand for a product. Its date and time are set by the system to the moment it is saved (the user cannot enter or back-date them), and the expected quantity stored with it is the product's physical stock (R-inventory-001) calculated at that moment. The counted and expected quantities can never be negative, and date, product and counted quantity are required. | `form:sfrmProductDetail_StockTake.QuantityOnHand.AfterUpdate` | procedure: Form_sfrmProductDetail_StockTake.QuantityOnHand_AfterUpdate<br>procedure: Form_sfrmProductDetail_StockTake.Form_BeforeUpdate<br>form: sfrmProductDetail_StockTake<br>table: StockTake | StockTake | high | rule | Q-inventory-003 |
| R-inventory-010 | When the counted quantity entered for a stock take differs from the expected quantity, the user is shown both figures and must confirm the count; if they decline, the entry is discarded and nothing is saved. | `form:sfrmProductDetail_StockTake.QuantityOnHand.BeforeUpdate` | procedure: Form_sfrmProductDetail_StockTake.QuantityOnHand_BeforeUpdate | StockTake | high | e2e | - |
| R-inventory-011 | Stock takes are append-only: users may add a new stock take for a product, but an existing stock take can be neither edited nor deleted. | `form:sfrmProductDetail_StockTake.Current` | procedure: Form_sfrmProductDetail_StockTake.Form_Current | StockTake | high | rule | - |
| R-inventory-012 | A product cannot be saved while any required field is empty (code, name, standard unit cost, unit price, category, discontinued flag) or while its standard unit cost is zero or less. Product code and product name are each unique. | `form:frmProductDetail.BeforeUpdate` | procedure: Form_frmProductDetail.Form_BeforeUpdate<br>table: Products | Products | high | rule | - |
| R-inventory-013 | A product's code is built from a fixed company prefix (NWT), the code of the product's category, a hyphen and the product's number. It is set whenever a category is chosen for a product that already has a number, so changing a product's category changes its code. | `form:frmProductDetail.cboProductCategoryID.AfterUpdate` | procedure: Form_frmProductDetail.SetProductCode<br>procedure: Form_frmProductDetail.cboProductCategoryID_AfterUpdate | Products, ProductCategories | high | rule | Q-inventory-007 |
| R-inventory-014 | A product category's code cannot be changed once any product belongs to that category, because product codes are built from it. Category name and category code are each required and unique. | `form:sfrmProductCategories.txtProductCategoryCode.BeforeUpdate` | procedure: Form_sfrmProductCategories.txtProductCategoryCode_BeforeUpdate<br>form: sfrmProductCategories<br>table: ProductCategories | ProductCategories, Products | high | rule | - |
| R-inventory-015 | A product category cannot be deleted while any product belongs to it; the user is told why. An unsaved new category is simply discarded. | `form:sfrmProductCategories.cmdDelete.Click` | procedure: Form_sfrmProductCategories.cmdDelete_Click | ProductCategories, Products | high | rule | - |
| R-inventory-016 | A product cannot be deleted while it appears on any order line or any purchase-order line; the user is told which kind of record blocks it. Otherwise deleting a product also deletes its stock takes and its vendor links. | `form:frmProductDetail.cmdDeleteProduct.Click` | procedure: Form_frmProductDetail.cmdDeleteProduct_Click | Products, OrderDetails, PurchaseOrderDetails, StockTake, ProductVendors | high | rule | - |
| R-inventory-017 | Reordering a product first saves any pending changes to it. If the product has an on-order quantity and there is a purchase order in the Approved, New or Submitted status that contains the product, reordering opens that purchase order instead of creating or changing anything. | `form:frmProductDetail.cmdReorderProduct.Click` | procedure: Form_frmProductDetail.cmdReorderProduct_Click<br>query: qryProductPurchaseOrder | PurchaseOrders, PurchaseOrderDetails | high | rule | Q-inventory-001 |
| R-inventory-018 | A product can be reordered only when at least one vendor is linked to it; otherwise the user is told a vendor is required and sent to the product's vendors. With exactly one linked vendor that vendor is used; with several the user picks one, and cancelling the choice cancels the reorder. | `form:frmProductDetail.cmdReorderProduct.Click` | procedure: Form_frmProductDetail.cmdReorderProduct_Click | ProductVendors | high | rule | - |
| R-inventory-019 | The reorder quantity is the suggested reorder quantity (R-inventory-006). If that is zero, the product's minimum reorder quantity is used; if that is also zero or blank, the user is asked for a quantity, and a zero or cancelled answer cancels the reorder. | `form:frmProductDetail.cmdReorderProduct.Click` | procedure: Form_frmProductDetail.cmdReorderProduct_Click | Products | high | rule | - |
| R-inventory-020 | A reorder adds the product to the chosen vendor's oldest purchase order still in the New status: if the product is already on that order its line quantity is increased, otherwise a line is added. When the vendor has no New purchase order, a new purchase order in the New status is created for the vendor with that single line. The line's unit cost is the product's standard unit cost. If no purchase order results, the user is told the reorder failed. | `form:frmProductDetail.cmdReorderProduct.Click` | procedure: Form_frmProductDetail.cmdReorderProduct_Click | PurchaseOrders, PurchaseOrderDetails, Products | high | rule | - |
| R-inventory-021 | A discontinued product cannot be reordered (the reorder action is not offered) and its discontinued status is shown prominently. The reorder quantity is highlighted as needing attention only for a product that is not discontinued and whose suggested reorder quantity is above zero. | `form:frmProductDetail.chkDiscontinued.AfterUpdate` | procedure: Form_frmProductDetail.ControlStates<br>procedure: Form_frmProductDetail.chkDiscontinued_AfterUpdate | Products | high | rule | - |
| R-inventory-022 | The product page shows, for a saved product, its quantity to sell, no-stock, allocated and on-order quantities and its suggested reorder quantity, recalculated whenever the product or its target level changes. A product that is not yet saved shows zeros and offers no delete, reorder, order history or purchase-order history. | `form:frmProductDetail.Current` | procedure: Form_frmProductDetail.CalculateLevels<br>procedure: Form_frmProductDetail.ControlStates<br>procedure: Form_frmProductDetail.txtTargetLevel_AfterUpdate<br>form: frmProductDetail | Products | high | rule | - |
| R-inventory-023 | The product list shows every product with its category name, code, name, description, costs and prices, reorder settings and discontinued flag, together with its calculated no-stock, allocated, to-sell and on-order quantities. | `query:qryProductList` | query: qryProductList<br>form: frmProductList | Products, ProductCategories | high | equivalence | - |
| R-inventory-024 | The product list can be exported to a spreadsheet listing, per product sorted by name, its number, code and name, allocated quantity, quantity to sell, on-order quantity, reorder level, target level, minimum reorder quantity and discontinued flag. | `form:frmProductList.cmdExport.Click` | query: qryProductList_Export<br>procedure: Form_frmProductList.cmdExport_Click | Products | high | equivalence | Q-inventory-004 |
| R-inventory-025 | A product's order history lists each order line for the product with the order number and date, quantity, unit price, extended price (quantity times unit price), the order's status name and the line's status name. | `query:qryProductOrders` | query: qryProductOrders<br>form: sfrmProductDetail_Orders | OrderDetails, Orders, OrderStatus, OrderDetailStatus, Products | high | equivalence | - |
| R-inventory-026 | A product's purchase-order history lists each purchase-order line for the product with the purchase order number, status, quantity, unit cost, extended cost (quantity times unit cost), vendor name, submitted date and received date, ordered by the status's sort order and then the submitted date. | `query:qryProductPurchaseOrder` | query: qryProductPurchaseOrder<br>form: sfrmProductDetail_PurchaseOrders | PurchaseOrderDetails, PurchaseOrders, PurchaseOrderStatus, Companies, Products | high | equivalence | - |
| R-inventory-027 | When picking a product on an order line, the category filter offers an 'all categories' entry first and then every category by name; the product choices, sorted by name with their unit price and category, are all products when 'all' is chosen and only that category's products otherwise. | `query:qrycboProducts` | query: qrycboProductCategories<br>query: qrycboProducts<br>query: qrycboProducts_All | Products, ProductCategories | high | equivalence | Q-inventory-005 |
| R-inventory-028 | Products, product categories, product-vendor links and stock takes carry audit stamps: when a record is created, the added-by and modified-by fields get the current user's name and the added-on and modified-on fields the current date and time; on every later change only the modified-by and modified-on fields are refreshed, and the added-by and added-on values can never be changed or cleared. | `datamacro:Products.BeforeChange` | data_macro: Products.BeforeChange<br>data_macro: ProductCategories.BeforeChange<br>data_macro: ProductVendors.BeforeChange<br>data_macro: StockTake.BeforeChange<br>procedure: Form_sfrmProductDetail_Vendors.Form_BeforeUpdate | Products, ProductCategories, ProductVendors, StockTake | high | rule | Q-inventory-006 |
| R-inventory-029 | A product can be linked to a given vendor only once; product and vendor are both required on the link, and the vendor must be an existing company. | `form:sfrmProductDetail_Vendors.BeforeUpdate` | form: sfrmProductDetail_Vendors<br>table: ProductVendors | ProductVendors, Companies | high | rule | - |
| R-inventory-030 | End to end, a user can open the product list, open a product whose stock is short of its target, see its levels and suggested reorder quantity, reorder it from a linked vendor, and find the resulting New purchase order on the product's purchase-order history; once that order is approved the quantity shows as on order, and once it is received the product's physical stock rises and waiting order lines are allocated. | `form:frmProductDetail.cmdReorderProduct.Click` | form: frmProductList<br>form: frmProductDetail<br>procedure: Form_frmProductDetail.cmdReorderProduct_Click | Products, ProductVendors, PurchaseOrders, PurchaseOrderDetails, OrderDetails | medium | e2e | - |

## Keep / drop

| Type | Name | Decision | Target component | Reason |
|---|---|---|---|---|
| table | ProductCategories | keep | legacy.models | - |
| table | ProductVendors | keep | legacy.models | - |
| table | Products | keep | legacy.models | - |
| table | StockTake | keep | legacy.models | - |
| data_macro | ProductCategories.BeforeChange | keep | inventory.models | - |
| data_macro | ProductVendors.BeforeChange | keep | inventory.models | - |
| data_macro | Products.BeforeChange | keep | inventory.models | - |
| data_macro | StockTake.BeforeChange | keep | inventory.models | - |
| form | frmProductDetail | keep | inventory.views | - |
| form | frmProductList | keep | inventory.views | - |
| form | sfrmProductCategories | keep | inventory.views | - |
| form | sfrmProductDetail_Orders | keep | inventory.views | - |
| form | sfrmProductDetail_PurchaseOrders | keep | inventory.views | - |
| form | sfrmProductDetail_StockTake | keep | inventory.views | - |
| form | sfrmProductDetail_Vendors | keep | inventory.views | - |
| query | qryMaxStockTakeDate | drop | - | unused: no form, report, query or code refers to it; the latest stock take is found in code (R-inventory-002) |
| query | qryPOProducts_ByStatus | keep | inventory.saved_queries | - |
| query | qryProductCategories | keep | inventory.saved_queries | plain record source for category maintenance (all columns of one table); its unit proves it, no rule |
| query | qryProductDetail | keep | inventory.saved_queries | plain record source for the product page (all columns of one table); its unit proves it, no rule |
| query | qryProductList | keep | inventory.saved_queries | - |
| query | qryProductList_Export | keep | inventory.saved_queries | - |
| query | qryProductOrders | keep | inventory.saved_queries | - |
| query | qryProductPurchaseOrder | keep | inventory.saved_queries | - |
| query | qryProductVendors | keep | inventory.saved_queries | plain record source for a product's vendor links (all columns of one table); its unit proves it, no rule |
| query | qryStockTake | keep | inventory.saved_queries | plain record source for a product's stock takes (columns of one table); its unit proves it, no rule |
| query | qrycboProductCategories | keep | inventory.saved_queries | - |
| query | qrycboProductCategory | keep | inventory.saved_queries | plain category choice list sorted by name for the product page; its unit proves it, no rule |
| query | qrycboProducts | keep | inventory.saved_queries | - |
| query | qrycboProducts_All | keep | inventory.saved_queries | - |
| procedure | Form_frmProductDetail.CalculateLevels | keep | inventory.views | - |
| procedure | Form_frmProductDetail.ControlStates | keep | inventory.views | - |
| procedure | Form_frmProductDetail.Form_Activate | drop | - | Access screen refresh when the window regains focus; a web page recalculates the figures on every load |
| procedure | Form_frmProductDetail.Form_AfterDelConfirm | drop | - | refreshes the product picker and any open product list after a delete; web pages are rebuilt on load |
| procedure | Form_frmProductDetail.Form_AfterInsert | drop | - | refreshes on-screen state and open lists after an insert; the web page redirects and reloads |
| procedure | Form_frmProductDetail.Form_AfterUpdate | drop | - | refreshes on-screen state and open lists after a save; the web page redirects and reloads |
| procedure | Form_frmProductDetail.Form_BeforeUpdate | keep | inventory.forms | - |
| procedure | Form_frmProductDetail.Form_Close | drop | - | Access lazy-loading cleanup and refresh of other open windows; not needed on the web |
| procedure | Form_frmProductDetail.Form_Current | drop | - | only re-applies the screen states of ControlStates on record navigation; that behaviour is kept through R-inventory-021 and R-inventory-022 |
| procedure | Form_frmProductDetail.Form_Delete | drop | - | removes the product from the Access recently-used navigation list; no such list in the web app |
| procedure | Form_frmProductDetail.Form_Load | drop | - | Access lazy loading of tab subforms; not needed on the web |
| procedure | Form_frmProductDetail.SetProductCode | keep | inventory.models | - |
| procedure | Form_frmProductDetail.cboFindProduct_AfterUpdate | keep | inventory.views | navigation only: jumps to the chosen product; holds no business rule |
| procedure | Form_frmProductDetail.cboProductCategoryID_AfterUpdate | keep | inventory.models | - |
| procedure | Form_frmProductDetail.chkDiscontinued_AfterUpdate | keep | inventory.views | - |
| procedure | Form_frmProductDetail.cmdAddProduct_Click | keep | inventory.views | navigation only: opens a blank product; holds no business rule |
| procedure | Form_frmProductDetail.cmdDeleteProduct_Click | keep | inventory.services | - |
| procedure | Form_frmProductDetail.cmdReorderProduct_Click | keep | inventory.services | - |
| procedure | Form_frmProductDetail.imgHelp_Click | drop | - | empty help handler; does nothing |
| procedure | Form_frmProductDetail.tabProducts_Change | drop | - | Access lazy loading of tab subforms; not needed on the web |
| procedure | Form_frmProductDetail.txtTargetLevel_AfterUpdate | keep | inventory.views | - |
| procedure | Form_frmProductList.ProductID_Click | keep | inventory.views | navigation only: opens the clicked product; holds no business rule |
| procedure | Form_frmProductList.cmdAddProduct_Click | keep | inventory.views | navigation only: opens a blank product; holds no business rule |
| procedure | Form_frmProductList.cmdExport_Click | keep | inventory.views | - |
| procedure | Form_sfrmProductCategories.Form_AfterInsert | drop | - | refreshes the category list box after an insert; web pages are rebuilt on load |
| procedure | Form_sfrmProductCategories.Form_Current | drop | - | keeps the list box selection in step with the record shown; Access UI only |
| procedure | Form_sfrmProductCategories.Form_Delete | drop | - | refreshes the category list box after a delete; web pages are rebuilt on load |
| procedure | Form_sfrmProductCategories.cmdAdd_Click | keep | inventory.views | navigation only: opens a blank category; holds no business rule |
| procedure | Form_sfrmProductCategories.cmdDelete_Click | keep | inventory.services | - |
| procedure | Form_sfrmProductCategories.lstCategory_AfterUpdate | keep | inventory.views | navigation only: shows the category picked in the list; holds no business rule |
| procedure | Form_sfrmProductCategories.txtProductCategoryCode_BeforeUpdate | keep | inventory.forms | - |
| procedure | Form_sfrmProductDetail_Orders.txtOrderID_Click | keep | inventory.views | navigation only: opens the clicked order; holds no business rule |
| procedure | Form_sfrmProductDetail_PurchaseOrders.txtPOID_Click | keep | inventory.views | navigation only: opens the clicked purchase order; holds no business rule |
| procedure | Form_sfrmProductDetail_StockTake.Form_AfterInsert | drop | - | refreshes the parent window's figures after an insert; the web page reloads |
| procedure | Form_sfrmProductDetail_StockTake.Form_AfterUpdate | keep | inventory.services | - |
| procedure | Form_sfrmProductDetail_StockTake.Form_BeforeUpdate | keep | inventory.forms | - |
| procedure | Form_sfrmProductDetail_StockTake.Form_Current | keep | inventory.views | - |
| procedure | Form_sfrmProductDetail_StockTake.QuantityOnHand_AfterUpdate | keep | inventory.services | - |
| procedure | Form_sfrmProductDetail_StockTake.QuantityOnHand_BeforeUpdate | keep | inventory.forms | - |
| procedure | Form_sfrmProductDetail_StockTake.RequeryQuantities | drop | - | refreshes the parent window and any open product list; the web page reloads |
| procedure | Form_sfrmProductDetail_Vendors.Form_BeforeUpdate | keep | inventory.models | - |
| procedure | Form_sfrmProductDetail_Vendors.txtVendorID_Click | keep | inventory.views | navigation only: opens the vendor's company page; holds no business rule |
| procedure | modForms.RequeryProductList | drop | - | refreshes the product list window if it is open; web pages are rebuilt on load |
| procedure | modInventory.AllocateInventory | keep | inventory.services | - |
| procedure | modInventory.OrderQuantity_ByStatus | keep | inventory.services | - |
| procedure | modInventory.ProductAllocated | keep | inventory.services | - |
| procedure | modInventory.ProductAvailable | keep | inventory.services | - |
| procedure | modInventory.ProductBought | keep | inventory.services | - |
| procedure | modInventory.ProductLastStockTakeDate | keep | inventory.services | - |
| procedure | modInventory.ProductLastStockTakeQuantity | keep | inventory.services | - |
| procedure | modInventory.ProductNoStock | keep | inventory.services | - |
| procedure | modInventory.ProductOnOrder | keep | inventory.services | - |
| procedure | modInventory.ProductReorderQuantity | keep | inventory.services | - |
| procedure | modInventory.ProductSold | keep | inventory.services | - |
| procedure | modInventory.ProductToSell | keep | inventory.services | - |
| procedure | modRibbonCallback.cmdProducts_OnAction | keep | inventory.views | menu entry that opens the product list; holds no business rule |

## Lookups

| Table | Column | Copy codes | Codes to sign | Rule |
|---|---|---|---|---|
| OrderDetails | OrderDetailStatusID | yes | none listed: the codes come from the design (code literals and the status enumerations) | R-inventory-007 |
| PurchaseOrders | StatusID | yes | none listed: the codes come from the design (code literals and the status enumerations) | R-inventory-004 |
| ProductCategories | ProductCategoryCode | no | generated by synth | R-inventory-013 |

## Relations

| Table | Foreign key | On delete | Rule |
|---|---|---|---|
| Products | ProductCategoryID | PROTECT | R-inventory-015 |
| StockTake | ProductID | CASCADE | R-inventory-016 |
| ProductVendors | ProductID | CASCADE | R-inventory-016 |
| OrderDetails | ProductID | PROTECT | R-inventory-016 |
| PurchaseOrderDetails | ProductID | PROTECT | R-inventory-016 |
| ProductVendors | VendorID | PROTECT | R-inventory-029 |

## Workflows

### Inventory levels and restocking (`inventory_restock`)

- Forms: frmProductList, frmProductDetail, sfrmProductDetail_Vendors, sfrmProductDetail_PurchaseOrders
- Reports: none
- Rules: R-inventory-030, R-inventory-006, R-inventory-017, R-inventory-018, R-inventory-019, R-inventory-020, R-inventory-021, R-inventory-022
- Steps:
  1. open the product list and read each product's stock figures
  2. open a product whose quantity to sell is below its target level
  3. check its suggested reorder quantity
  4. reorder it from a linked vendor
  5. see the new or extended New purchase order on the product's purchase-order history
  6. after the purchase order is approved and received, see the physical stock rise and waiting order lines allocated

### Stock take and re-allocation (`stock_take`)

- Forms: frmProductDetail, sfrmProductDetail_StockTake
- Reports: none
- Rules: R-inventory-010, R-inventory-009, R-inventory-011, R-inventory-008, R-inventory-001
- Steps:
  1. open a product's stock takes
  2. enter a counted quantity that differs from the expected quantity
  3. confirm the count when asked
  4. see the stock take saved with the system date and expected quantity
  5. see the product's figures and order line allocations updated

## Services

| Name | Inputs | Outputs | Errors |
|---|---|---|---|
| product_stock_levels | product id | physical stock; allocated quantity; no-stock quantity; on-order quantity; quantity to sell; suggested reorder quantity | unknown product |
| allocate_inventory | product id | order lines whose status changed | unknown product |
| record_stock_take | product id; counted quantity; mismatch confirmed | stock take id; expected quantity | negative quantity; count differs from expected and was not confirmed |
| reorder_product | product id; vendor id (when the product has several vendors); quantity (when no reorder or minimum quantity applies) | purchase order id; whether an outstanding purchase order was opened instead | product is discontinued; no vendor linked to the product; vendor choice required; quantity required; reorder failed |
| delete_product | product id | deleted | product is on an order line; product is on a purchase-order line |

## Open questions

| ID | Question | Status |
|---|---|---|
| Q-inventory-001 | Only Approved purchase orders count as on order in the stock figures and the suggested reorder quantity, while the reorder action also treats New and Submitted orders as outstanding. Should New and Submitted orders keep being left out of the on-order figure? | open |
| Q-inventory-002 | When a product has no stock take, the old app silently creates an opening zero-quantity stock take the first time stock is calculated. May the new app create that opening stock take when the product is created instead (same figures)? | open |
| Q-inventory-003 | Stock takes are always dated at the moment they are saved, so a count made earlier cannot be back-dated. Keep that restriction? | open |
| Q-inventory-004 | Is the spreadsheet export of the product list still needed, and is an .xlsx download from the web page acceptable? | open |
| Q-inventory-005 | Discontinued products are still offered when picking a product on an order line. Should they stay selectable for new orders? | open |
| Q-inventory-006 | Audit stamps use the signed-in employee's full name, and the old app falls back to the Windows user name when nobody is signed in. In the web app everyone is signed in; which name should stamps from imports or system jobs carry? | open |
| Q-inventory-007 | Product codes are rebuilt from the fixed NWT prefix, the category code and the product number whenever the category changes. Keep the prefix and the rebuild on category change, or should codes stay fixed once issued? | open |
| Q-inventory-008 | Sold quantity counts every line of an invoiced order from the invoice date on, whatever the line's own status. Is that the intended point at which stock leaves the warehouse (rather than shipping)? | open |
