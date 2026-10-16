# Purchasing and receiving: rules for sign-off

Area `purchasing` of engagement northwind-demo, spec version 1.0 (draft, not signed). This file is the reader's copy of `analysis/rules/purchasing.json`; the JSON file is the source of truth.

## Area summary

Purchasing covers buying stock from vendors: entering a purchase order for one vendor with its line items, taking it through submit, approve, receive and close, and the stock update that receiving causes. It also covers the reorder path that starts on a product page and the vendor's purchase order tab on the company page.

- Status: kept. It carries the must-keep workflow *purchase order → receiving → stock update* (workflow `purchase_order_to_stock`) and the purchase side of *inventory levels and restocking* (workflow `reorder_product`).
- Objects in scope: 63; kept 50, dropped 13, out of scope 0.
- Rules: 27 (19 proven by rule tests, 5 by equivalence units, 3 by end-to-end tests).
- Open questions: 9.
- Reports: none of the source reports belongs to this area.
- Sign-in and roles (the approve-purchase-order privilege) come from the foundation built in S4.

Purchase order statuses, in order: New, Submitted, Approved, Received, Closed.

## Rules

| ID | Rule | Trigger | Sources | Tables | Confidence | Proven by | Questions |
|---|---|---|---|---|---|---|---|
| R-purchasing-001 | A new purchase order always starts in status New, whether it is entered by hand or created by a product reorder. | `form:frmPurchaseOrderDetails.BeforeInsert` | procedure Form_frmPurchaseOrderDetails.Form_BeforeInsert; procedure modPurchaseOrders.ReorderProduct | PurchaseOrders | high | rule | - |
| R-purchasing-002 | A purchase order is saved only when its required fields are filled in (at least the vendor and the status); otherwise the save is refused and the missing fields are highlighted. The vendor must be an existing company, the status an existing purchase order status, and the submitter and approver existing employees. | `form:frmPurchaseOrderDetails.BeforeUpdate` | procedure Form_frmPurchaseOrderDetails.Form_BeforeUpdate; table PurchaseOrders | PurchaseOrders, Companies, Employees, PurchaseOrderStatus | high | rule | - |
| R-purchasing-003 | A purchase order moves through the fixed sequence New, Submitted, Approved, Received, Closed. Each step has its own action, each action works only from the status directly before it, and no step can be skipped or undone. The form shows which steps are already done. | `form:frmPurchaseOrderDetails.Current` | procedure Form_frmPurchaseOrderDetails.SetWorkflowLabelColors; procedure Form_frmPurchaseOrderDetails.cmdSubmitPO_Click; procedure Form_frmPurchaseOrderDetails.cmdApprovePO_Click; procedure Form_frmPurchaseOrderDetails.cmdReceivePO_Click; procedure Form_frmPurchaseOrderDetails.cmdClosePO_Click; table PurchaseOrderStatus; data_macro PurchaseOrderStatus.BeforeChange | PurchaseOrders, PurchaseOrderStatus | high | e2e | - |
| R-purchasing-004 | Submitting is allowed only for a purchase order in status New. It records the signed-in user as submitter and the current date and time as the submitted date, and sets the status to Submitted. From any other status the action is refused with a message and nothing changes. | `form:frmPurchaseOrderDetails.cmdSubmitPO.Click` | procedure Form_frmPurchaseOrderDetails.cmdSubmitPO_Click | PurchaseOrders | high | rule | Q-purchasing-006 |
| R-purchasing-005 | Approving is allowed only for a Submitted purchase order and only for a user who holds the approve-purchase-order privilege. It records that user as approver and the current date and time as the approved date, and sets the status to Approved. Without the privilege, or from another status, the action is refused with a message and nothing changes. | `form:frmPurchaseOrderDetails.cmdApprovePO.Click` | procedure Form_frmPurchaseOrderDetails.cmdApprovePO_Click | PurchaseOrders, EmployeePrivileges | high | rule | Q-purchasing-004, Q-purchasing-006 |
| R-purchasing-006 | Right after a purchase order is approved, and again right after it is received, stock allocation is re-run for every product on it, so customer order lines waiting for those products are re-evaluated oldest first (the allocation rule itself belongs to the inventory area). | `procedure:Form_frmPurchaseOrderDetails.AllocatePurchaseOrder` | procedure Form_frmPurchaseOrderDetails.AllocatePurchaseOrder; procedure Form_frmPurchaseOrderDetails.cmdApprovePO_Click; procedure Form_frmPurchaseOrderDetails.cmdReceivePO_Click; procedure modInventory.AllocateInventory | PurchaseOrderDetails, OrderDetails | high | rule | - |
| R-purchasing-007 | Receiving is allowed only for an Approved purchase order and only after the user confirms posting it to inventory; declining changes nothing. Receiving records the current date and time as the received date of the purchase order and of every one of its lines (the whole order is received at once) and sets the status to Received. | `form:frmPurchaseOrderDetails.cmdReceivePO.Click` | procedure Form_frmPurchaseOrderDetails.cmdReceivePO_Click | PurchaseOrders, PurchaseOrderDetails | high | rule | Q-purchasing-005, Q-purchasing-006 |
| R-purchasing-008 | Stock update: once a line is received, its quantity counts as stock bought from its received date and time, so it raises the product's available quantity after the last stock take. While its purchase order is Approved and not yet received, the line quantity counts as on order instead. | `form:frmPurchaseOrderDetails.cmdReceivePO.Click` | procedure Form_frmPurchaseOrderDetails.cmdReceivePO_Click; procedure modInventory.ProductBought; procedure modInventory.ProductOnOrder | PurchaseOrderDetails, PurchaseOrders | high | e2e | - |
| R-purchasing-009 | Closing is allowed only for a Received purchase order and only when both the shipping fee and the payment method are filled in; otherwise the missing fields are highlighted and the close is refused. Closing stores the current date and time as the payment date, the computed tax as the tax amount and the computed total as the payment amount, and sets the status to Closed. The payment method is chosen from a fixed list in the form. | `form:frmPurchaseOrderDetails.cmdClosePO.Click` | procedure Form_frmPurchaseOrderDetails.cmdClosePO_Click; procedure Form_frmPurchaseOrderDetails.PoCloseFieldsFilledOut | PurchaseOrders | high | rule | Q-purchasing-007 |
| R-purchasing-010 | Purchase order amounts: each line amount is quantity times unit cost; the subtotal is the sum of the line amounts; the tax is the vendor tax rate from the system settings times the subtotal (the shipping fee is not taxed); the total is subtotal plus tax plus shipping fee, with a missing shipping fee counted as zero. | `form:frmPurchaseOrderDetails.Current` | form frmPurchaseOrderDetails; form sfrmPurchaseOrderLineItems | PurchaseOrders, PurchaseOrderDetails, SystemSettings | high | rule | Q-purchasing-003 |
| R-purchasing-011 | Field locking by status: once a purchase order is saved, its number, vendor, status, submitter, approver, the submitted and approved dates, the computed tax and total and the payment date can no longer be edited directly. The received date is editable only while the order is Approved, the shipping fee and payment method only while it is Received, and the notes until it is Closed. A Closed purchase order is read-only. On a new, unsaved purchase order the vendor can be chosen. | `form:frmPurchaseOrderDetails.Current` | procedure Form_frmPurchaseOrderDetails.LockControls; procedure Form_frmPurchaseOrderDetails.Form_Current | PurchaseOrders | medium | rule | Q-purchasing-001, Q-purchasing-007 |
| R-purchasing-012 | Line items can be added, changed or deleted only while the purchase order is New (or not yet saved); from Submitted on the lines are frozen. | `form:frmPurchaseOrderDetails.Current` | procedure Form_frmPurchaseOrderDetails.Form_Current | PurchaseOrderDetails, PurchaseOrders | high | rule | - |
| R-purchasing-013 | Line items cannot be entered before the purchase order itself has been saved; the user is told to complete and save the purchase order first. | `form:sfrmPurchaseOrderLineItems.Error` | procedure Form_sfrmPurchaseOrderLineItems.Form_Error; form sfrmPurchaseOrderLineItems | PurchaseOrderDetails | high | rule | - |
| R-purchasing-014 | A purchase order can be deleted only while it is New or Submitted; deleting it also deletes all of its lines. In any later status the delete is refused with a message. | `form:frmPurchaseOrderDetails.cmdDeletePO.Click` | procedure Form_frmPurchaseOrderDetails.cmdDeletePO_Click; table PurchaseOrderDetails | PurchaseOrders, PurchaseOrderDetails | high | rule | - |
| R-purchasing-015 | Changing the vendor of a purchase order that already has a vendor asks for confirmation. On yes, all lines of the purchase order are deleted and the new vendor is kept; on no, the old vendor stays. Choosing the first vendor of a new purchase order does not ask. After a vendor change the product choices for the lines are refreshed. | `form:frmPurchaseOrderDetails.VendorID.BeforeUpdate` | procedure Form_frmPurchaseOrderDetails.VendorID_BeforeUpdate; procedure Form_frmPurchaseOrderDetails.VendorID_AfterUpdate | PurchaseOrders, PurchaseOrderDetails | medium | rule | Q-purchasing-001 |
| R-purchasing-016 | The product choices for a purchase order line are only the products that the purchase order's vendor supplies (per the product-vendor list), sorted by product name, each carrying its standard unit cost. | `query:qrycboProducts_PO` | query qrycboProducts_PO; procedure Form_frmPurchaseOrderDetails.VendorID_AfterUpdate | Products, ProductVendors | high | equivalence | - |
| R-purchasing-017 | The vendor choices for a purchase order are the companies whose company type is vendor, sorted by company name. | `query:qrycboVendors` | query qrycboVendors | Companies | high | equivalence | - |
| R-purchasing-018 | Choosing a product on a purchase order line fills in the quantity with the product's computed reorder quantity and the unit cost with the product's standard unit cost; the user may change both before saving. | `form:sfrmPurchaseOrderLineItems.ProductID.AfterUpdate` | procedure Form_sfrmPurchaseOrderLineItems.ProductID_AfterUpdate; procedure modInventory.ProductReorderQuantity | PurchaseOrderDetails, Products | high | rule | - |
| R-purchasing-019 | A purchase order line needs a product, a quantity and a unit cost, and the product must exist. A quantity below the product's minimum reorder quantity is refused with a message. If the product's quantity available to sell plus the ordered quantity stays below the product's target level, the user gets a warning but the line is still saved. | `form:sfrmPurchaseOrderLineItems.BeforeUpdate` | procedure Form_sfrmPurchaseOrderLineItems.Form_BeforeUpdate; procedure Form_sfrmPurchaseOrderLineItems.ValidateLineItem; procedure modInventory.ProductToSell | PurchaseOrderDetails, Products | high | rule | Q-purchasing-008 |
| R-purchasing-020 | A purchase order holds at most one line per product. Adding a product that is already on the purchase order adds the new quantity to the existing line and keeps its unit cost; the database also refuses a second line for the same product. | `procedure:modPurchaseOrders.AddPurchaseOrderDetail` | procedure modPurchaseOrders.AddPurchaseOrderDetail; table PurchaseOrderDetails | PurchaseOrderDetails | high | rule | - |
| R-purchasing-021 | On a saved purchase order, one action adds a line for every product that the vendor supplies, that is not yet on the purchase order and that has at least one customer order line waiting in No Stock status; each new line gets the product's computed reorder quantity and its standard unit cost. On an unsaved purchase order the action is refused with a message. | `form:frmPurchaseOrderDetails.cmdAddNostock.Click` | procedure Form_frmPurchaseOrderDetails.cmdAddNostock_Click; procedure modInventory.ProductNoStock; procedure modInventory.ProductReorderQuantity | PurchaseOrderDetails, Products, ProductVendors, OrderDetails | high | rule | - |
| R-purchasing-022 | Reordering a product for a vendor appends a line (product, quantity, standard unit cost) to that vendor's oldest purchase order still in status New; when the vendor has none, it creates a new purchase order for the vendor in status New with that one line. If the line cannot be added the user is told that the purchase order exists without it. | `procedure:modPurchaseOrders.ReorderProduct` | procedure modPurchaseOrders.ReorderProduct; procedure modPurchaseOrders.AddPurchaseOrderDetail; procedure Form_frmProductDetail.cmdReorderProduct_Click | PurchaseOrders, PurchaseOrderDetails | high | rule | - |
| R-purchasing-023 | When a product with several vendors is reordered, the user picks the vendor from a dialog that lists only the vendors supplying that product, sorted by name. Confirming without a vendor selected is refused with a prompt, a double-click on a vendor confirms it, and cancel ends the reorder without creating anything. A product with exactly one vendor skips the dialog, and a product without a vendor cannot be reordered. | `form:frmSelectVendorDialog.cmdOK.Click` | form frmSelectVendorDialog; procedure Form_frmSelectVendorDialog.Form_Load; procedure Form_frmSelectVendorDialog.cmdOK_Click; procedure Form_frmSelectVendorDialog.lstVendor_DblClick; procedure Form_frmSelectVendorDialog.cmdCancel_Click; procedure Form_frmProductDetail.cmdReorderProduct_Click | ProductVendors, Companies | high | e2e | - |
| R-purchasing-024 | The extended cost of a purchase order is the sum over its lines of quantity times unit cost; a purchase order without lines still appears, with no cost. | `query:qryPurchaseOrderCost` | query qryPurchaseOrderCost | PurchaseOrders, PurchaseOrderDetails | high | equivalence | - |
| R-purchasing-025 | The purchase order list shows every purchase order with its status, vendor name, submitter and approver names, submitted, approved and payment dates, and a total cost equal to extended cost plus shipping fee plus tax amount (missing parts count as zero), ordered by purchase order number with the newest first. The list footer shows the number of purchase orders and the sum of their total cost. | `query:qryPurchaseOrderList` | query qryPurchaseOrderList; form frmPurchaseOrderList | PurchaseOrders, PurchaseOrderStatus, Companies, Employees | medium | equivalence | - |
| R-purchasing-026 | On a vendor's company page, the purchase order tab lists that vendor's purchase orders with status, submitter, approver, the submitted, approved and received dates, the payment fields and the extended cost, plus a count; only purchase orders that have a submitter appear. Double-clicking a row opens that purchase order. | `query:qryVendorPurchaseOrderList` | query qryVendorPurchaseOrderList; form sfrmCompanyDetail_VendorPurchaseOrders; procedure Form_sfrmCompanyDetail_VendorPurchaseOrders.Detail_DblClick; procedure Form_sfrmCompanyDetail_VendorPurchaseOrders.OpenForm_frmPurchaseOrderDetails | PurchaseOrders, PurchaseOrderStatus, Employees | medium | equivalence | Q-purchasing-002 |
| R-purchasing-027 | Audit fields on purchase orders, purchase order lines and purchase order statuses: on insert, added-by, added-on, modified-by and modified-on are set to the current user's name and the current date and time; on every update, modified-by and modified-on are refreshed while added-by and added-on keep their original values even if an edit tries to change or clear them. The purchase order form shows who created and last changed the record. | `datamacro:PurchaseOrders.BeforeChange` | data_macro PurchaseOrders.BeforeChange; data_macro PurchaseOrderDetails.BeforeChange; data_macro PurchaseOrderStatus.BeforeChange | PurchaseOrders, PurchaseOrderDetails, PurchaseOrderStatus | high | rule | Q-purchasing-009 |

## Keep and drop

### Keep (50)

| Type | Name | Target component | Note |
|---|---|---|---|
| table | PurchaseOrders | legacy.models |  |
| table | PurchaseOrderDetails | legacy.models |  |
| table | PurchaseOrderStatus | legacy.models |  |
| data_macro | PurchaseOrders.BeforeChange | purchasing.services |  |
| data_macro | PurchaseOrderDetails.BeforeChange | purchasing.services |  |
| data_macro | PurchaseOrderStatus.BeforeChange | purchasing.services |  |
| form | frmPurchaseOrderDetails | purchasing.views |  |
| form | frmPurchaseOrderList | purchasing.views |  |
| form | frmSelectVendorDialog | purchasing.views |  |
| form | sfrmCompanyDetail_VendorPurchaseOrders | purchasing.views |  |
| form | sfrmPurchaseOrderLineItems | purchasing.views |  |
| query | qryPurchaseOrder | purchasing.saved_queries | record source of the purchase order form (the order with its status, submitter and approver names); a plain lookup join, its equivalence unit proves it, no rule |
| query | qryPurchaseOrderCost | purchasing.saved_queries |  |
| query | qryPurchaseOrderLineItems | purchasing.saved_queries | record source of the line items subform (the order's lines in entry order); its equivalence unit proves it, no rule |
| query | qryPurchaseOrderList | purchasing.saved_queries |  |
| query | qryVendorPurchaseOrderList | purchasing.saved_queries |  |
| query | qrycboProducts_PO | purchasing.saved_queries |  |
| query | qrycboVendors | purchasing.saved_queries |  |
| procedure | Form_frmPurchaseOrderDetails.AllocatePurchaseOrder | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.Form_BeforeInsert | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.Form_BeforeUpdate | purchasing.forms |  |
| procedure | Form_frmPurchaseOrderDetails.Form_Current | purchasing.views |  |
| procedure | Form_frmPurchaseOrderDetails.Form_Load | purchasing.views | opens the requested purchase order or a blank new one; navigation only; the web app's links and URLs replace it, so it holds no business rule |
| procedure | Form_frmPurchaseOrderDetails.LockControls | purchasing.forms |  |
| procedure | Form_frmPurchaseOrderDetails.PoCloseFieldsFilledOut | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.SetWorkflowLabelColors | purchasing.views |  |
| procedure | Form_frmPurchaseOrderDetails.VendorID_AfterUpdate | purchasing.forms |  |
| procedure | Form_frmPurchaseOrderDetails.VendorID_BeforeUpdate | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.cmdAddNostock_Click | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.cmdAddPO_Click | purchasing.views | moves to a blank new purchase order; navigation only; the web app's links and URLs replace it, so it holds no business rule |
| procedure | Form_frmPurchaseOrderDetails.cmdApprovePO_Click | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.cmdClosePO_Click | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.cmdDeletePO_Click | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.cmdReceivePO_Click | purchasing.services |  |
| procedure | Form_frmPurchaseOrderDetails.cmdSubmitPO_Click | purchasing.services |  |
| procedure | Form_frmPurchaseOrderList.PurchaseOrderID_Click | purchasing.views | opens the clicked purchase order; navigation only; the web app's links and URLs replace it, so it holds no business rule |
| procedure | Form_frmPurchaseOrderList.cmdAddPO_Click | purchasing.views | opens a blank new purchase order; navigation only; the web app's links and URLs replace it, so it holds no business rule |
| procedure | Form_frmSelectVendorDialog.Form_Load | purchasing.views |  |
| procedure | Form_frmSelectVendorDialog.cmdCancel_Click | purchasing.views |  |
| procedure | Form_frmSelectVendorDialog.cmdOK_Click | purchasing.forms |  |
| procedure | Form_frmSelectVendorDialog.lstVendor_DblClick | purchasing.views |  |
| procedure | Form_sfrmCompanyDetail_VendorPurchaseOrders.Detail_DblClick | purchasing.views |  |
| procedure | Form_sfrmCompanyDetail_VendorPurchaseOrders.OpenForm_frmPurchaseOrderDetails | purchasing.views |  |
| procedure | Form_sfrmPurchaseOrderLineItems.Form_BeforeUpdate | purchasing.forms |  |
| procedure | Form_sfrmPurchaseOrderLineItems.Form_Error | purchasing.views |  |
| procedure | Form_sfrmPurchaseOrderLineItems.ProductID_AfterUpdate | purchasing.forms |  |
| procedure | Form_sfrmPurchaseOrderLineItems.PurchaseOrderDetailID_Click | purchasing.views | opens the product of the clicked line; navigation only; the web app's links and URLs replace it, so it holds no business rule |
| procedure | Form_sfrmPurchaseOrderLineItems.ValidateLineItem | purchasing.forms |  |
| procedure | modPurchaseOrders.AddPurchaseOrderDetail | purchasing.services |  |
| procedure | modPurchaseOrders.ReorderProduct | purchasing.services |  |

### Drop (13)

| Type | Name | Reason |
|---|---|---|
| query | qryVendors | not used by any form, report, query or code; qrycboVendors already lists the vendors |
| procedure | Form_frmPurchaseOrderDetails.Form_AfterInsert | adds the new purchase order to the Access ribbon's recently-used list; a desktop UI convenience with no web equivalent |
| procedure | Form_frmPurchaseOrderDetails.Form_AfterUpdate | clears field highlights and refreshes the open list window; a web page reloads from the database |
| procedure | Form_frmPurchaseOrderDetails.Form_Close | window bookkeeping for several open purchase order windows; not needed in a browser |
| procedure | Form_frmPurchaseOrderDetails.Form_Delete | removes the deleted purchase order from the Access ribbon's recently-used list; a desktop UI convenience |
| procedure | Form_frmPurchaseOrderDetails.Form_Open | empty handler (only its error handling); no behaviour |
| procedure | Form_frmPurchaseOrderList.Form_Open | clears a filter left over from an earlier Access session; the web list starts unfiltered |
| procedure | Form_sfrmPurchaseOrderLineItems.Form_Current | clears field highlights when moving between lines; UI only |
| procedure | modPurchaseOrders.CloseAllPurchaseOrderDetailsForms | releases the list of open purchase order windows at shutdown; not needed in a browser |
| procedure | modPurchaseOrders.ClosePurchaseOrderDetailsForm | removes a closed purchase order window from the list of open windows; not needed in a browser |
| procedure | modPurchaseOrders.OpenPurchaseOrderDetailsForm | opens a purchase order in an extra Access window (several at once); the purchase order detail URL replaces it |
| procedure | modRibbonCallback.cmdAddPurchaseOrder_OnAction | Access ribbon button that opens a new purchase order; the app's navigation bar and the list's new button replace it |
| procedure | modRibbonCallback.cmdPurchaseOrders_OnAction | Access ribbon button that opens the purchase order list; the app's navigation bar replaces it |

### Out of scope (0)

None.

## Lookups

| Table | Column | Codes are behaviour | Codes | Rule |
|---|---|---|---|---|
| PurchaseOrders | StatusID | yes | taken from the design: the five status codes the code uses (New, Submitted, Approved, Received, Closed) | R-purchasing-003 |
| PurchaseOrders | PaymentMethod | yes | taken from the design: the form's fixed list of three methods (credit card, check, cash); see Q-purchasing-007 | R-purchasing-009 |
| Companies | CompanyTypeID | yes | taken from the design: the vendor company type used in the vendor criteria | R-purchasing-017 |
| EmployeePrivileges | PrivilegeID | yes | taken from the design: the approve-purchase-order privilege code (roles come from the foundation) | R-purchasing-005 |

No codes were supplied in answers.md, so every `values` entry is empty: the codes come from the design.

## Relations

| Table | Foreign key | On delete | Rule |
|---|---|---|---|
| PurchaseOrderDetails | PurchaseOrderID | CASCADE | R-purchasing-014 |
| PurchaseOrderDetails | ProductID | PROTECT | R-purchasing-019 |
| PurchaseOrders | VendorID | PROTECT | R-purchasing-002 |
| PurchaseOrders | StatusID | PROTECT | R-purchasing-003 |
| PurchaseOrders | SubmittedByID | PROTECT | R-purchasing-004 |
| PurchaseOrders | ApprovedByID | PROTECT | R-purchasing-005 |

## Workflows

### Purchase order to receiving to stock update (`purchase_order_to_stock`)

- Forms: frmPurchaseOrderList, frmPurchaseOrderDetails, sfrmPurchaseOrderLineItems
- Reports: none
- Rules: R-purchasing-001, R-purchasing-003, R-purchasing-004, R-purchasing-005, R-purchasing-006, R-purchasing-007, R-purchasing-008, R-purchasing-009, R-purchasing-010, R-purchasing-012, R-purchasing-019

1. open the purchase order list and start a new purchase order
2. choose the vendor and save the purchase order (status New)
3. add line items for the vendor's products, or add all no-stock products at once
4. submit the purchase order
5. approve it as a user with the approve-purchase-order privilege (its quantities now count as on order)
6. receive it after confirming (status Received; the received quantities raise available stock)
7. check the product's available stock on the product page
8. enter the shipping fee and payment method and close it (tax, payment amount and payment date stored)

### Reorder a product from its vendor (restocking) (`reorder_product`)

- Forms: frmSelectVendorDialog, frmPurchaseOrderDetails
- Reports: none
- Rules: R-purchasing-022, R-purchasing-023, R-purchasing-018

1. on a product page start a reorder (the inventory area's product form)
2. pick the vendor in the dialog when the product has several vendors
3. the product is added to the vendor's open New purchase order, or a new one is created
4. the purchase order opens for review and goes on through the purchase order workflow

## Services

| Service | Inputs | Outputs | Errors |
|---|---|---|---|
| submit_purchase_order | purchase order id, signed-in user | status Submitted, submitter, submitted date and time | purchase order is not New |
| approve_purchase_order | purchase order id, signed-in user | status Approved, approver, approved date and time, stock allocation re-run for its products | purchase order is not Submitted, user lacks the approve-purchase-order privilege |
| receive_purchase_order | purchase order id, confirmation | status Received, received date and time on the purchase order and every line, stock allocation re-run for its products | purchase order is not Approved, not confirmed |
| close_purchase_order | purchase order id, shipping fee, payment method | status Closed, payment date, tax amount, payment amount | purchase order is not Received, shipping fee missing, payment method missing |
| delete_purchase_order | purchase order id | purchase order and its lines deleted | purchase order is not New or Submitted |
| change_purchase_order_vendor | purchase order id, new vendor id, confirmation | vendor changed, all lines deleted | not confirmed, vendor is locked in the current status |
| add_purchase_order_line | purchase order id, product id, quantity, unit cost | line id (new line, or existing line with the quantity added) | purchase order is not New, quantity below the product's minimum reorder quantity, line could not be saved |
| add_no_stock_lines | purchase order id | number of lines added | purchase order not saved yet |
| reorder_product | product id, vendor id, quantity, unit cost | purchase order id (existing New purchase order of the vendor, or a new one) | product has no vendor, line could not be added |
| purchase_order_amounts | purchase order id | subtotal, tax, total | - |

## Open questions

- **Q-purchasing-001** (open): Once a purchase order is saved its vendor is locked in every status, yet the app also has a confirm-and-delete-all-lines path for changing the vendor. Should the vendor of a saved New purchase order be changeable (deleting its lines after confirmation), or fixed once the purchase order is saved, as the current app effectively behaves?
- **Q-purchasing-002** (open): The purchase order tab on a vendor's company page lists only purchase orders that already have a submitter, so New purchase orders do not appear there, while the main purchase order list shows them. Is that intended, or should the vendor tab show every purchase order of the vendor?
- **Q-purchasing-003** (open): Tax on a purchase order is the vendor tax rate from the system settings times the line subtotal, the shipping fee is not taxed, and the tax is stored only when the purchase order is closed. Please confirm, and confirm that the vendor tax rate stays a single system-wide setting.
- **Q-purchasing-004** (open): Any user with the approve-purchase-order privilege can approve, including the person who submitted the purchase order. Should self-approval be blocked?
- **Q-purchasing-005** (open): Receiving is all or nothing: the whole purchase order is received at once and every line gets the same received date. Do you need partial receipts (some lines or part quantities)?
- **Q-purchasing-006** (open): The table design describes the submitted, approved, received and payment dates as dates without a time, but the app stores the date and time. Should the new app keep date and time (the line received time matters for stock calculations) or store dates only on the purchase order?
- **Q-purchasing-007** (open): The received date stays editable while a purchase order is Approved, and the shipping fee and payment method only while it is Received. Is that intended? Also, the payment method is chosen from a fixed list of three (credit card, check, cash): is that the full list?
- **Q-purchasing-008** (open): When a line's quantity leaves the product below its target level, the app only warns and still saves the line. Keep it as a warning, or make it a hard stop?
- **Q-purchasing-009** (open): Audit fields record a user name; when nobody is signed in, the app falls back to the computer's user name. The new app always has a signed-in user. Is it acceptable to record the signed-in user only?

## Sign-off

This area file is merged into `analysis/rules.md`, which carries the sign-off block for the whole specification.
