# Northwind: service interfaces

Engagement `northwind-demo`, spec version 1.0. One section per `services[]` entry of `analysis/rules.json`, then the order of operations of each workflow. These are target-neutral business operations: each takes the inputs listed, either completes with the outputs listed or refuses with one of the errors listed and changes nothing, and enforces the rules named (statements in `analysis/rules.md`). Screens, reports and jobs call them; how they are exposed is a build decision.

## Services

### Area `orders`: Orders, Invoicing and Shipping

#### `create_invoice`

- Area: `orders`
- Inputs: order id
- Outputs: order status Invoiced with invoice date; all lines Invoiced; invoice PDF
- Errors: order not saved; order is not New; order has no lines; a line is not Allocated; shipping fee missing
- Rules enforced: R-orders-015, R-orders-020, R-orders-021, R-orders-030

#### `ship_order`

- Area: `orders`
- Inputs: order id; shipped date; shipper id; shipping fee
- Outputs: order status Shipped; all lines Shipped
- Errors: order not saved; order is not Invoiced; shipped date, shipper or shipping fee missing
- Rules enforced: R-orders-016, R-orders-030

#### `receive_payment`

- Area: `orders`
- Inputs: order id; payment method; paid date
- Outputs: order status Paid
- Errors: order not saved; order is not Shipped; payment method or paid date missing
- Rules enforced: R-orders-017, R-orders-030

#### `close_order`

- Area: `orders`
- Inputs: order id
- Outputs: order status Closed
- Errors: order not saved; order is not Paid
- Rules enforced: R-orders-018, R-orders-030

#### `delete_order`

- Area: `orders`
- Inputs: order id
- Outputs: order and its lines deleted; stock re-allocated for the lines' products
- Errors: order not saved; order is Shipped, Paid or Closed
- Rules enforced: R-orders-011, R-orders-012, R-inventory-007

#### `save_order_line`

- Area: `orders`
- Inputs: order id; product id; quantity; discount; previous product id
- Outputs: line status Allocated or No Stock; unit price from the product; stock re-allocated for the old and new product
- Errors: order not saved; order is not New; quantity not above zero; product already on the order; required field missing
- Rules enforced: R-orders-004, R-orders-006, R-orders-007, R-orders-008, R-orders-009, R-orders-010, R-orders-013, R-inventory-007

#### `delete_order_line`

- Area: `orders`
- Inputs: order line id
- Outputs: line deleted; stock re-allocated for its product
- Errors: order is not New
- Rules enforced: R-orders-010, R-orders-013, R-inventory-007

#### `delete_company`

- Area: `orders`
- Inputs: company id
- Outputs: company, its contacts and its vendor-product links deleted
- Errors: company has orders as customer, orders as shipper or purchase orders
- Rules enforced: R-orders-033

#### `change_company_type`

- Area: `orders`
- Inputs: company id; company type id
- Outputs: company type changed
- Errors: company has orders, shipments, purchase orders or vendor-product links
- Rules enforced: R-orders-034

#### `delete_employee`

- Area: `orders`
- Inputs: employee id
- Outputs: employee deleted
- Errors: employee has orders; employee submitted purchase orders; employee supervises others; employee holds privileges
- Rules enforced: R-orders-040

#### `first_run`

- Area: `orders`
- Inputs: today's date
- Outputs: all dates shifted forward by the gap to the latest order date; first-run flag set
- Errors: none
- Rules enforced: R-orders-049

### Area `inventory`: Products and Inventory

#### `product_stock_levels`

- Area: `inventory`
- Inputs: product id
- Outputs: physical stock; allocated quantity; no-stock quantity; on-order quantity; quantity to sell; suggested reorder quantity
- Errors: unknown product
- Rules enforced: R-inventory-001, R-inventory-002, R-inventory-003, R-inventory-004, R-inventory-005, R-inventory-006, R-purchasing-008

#### `allocate_inventory`

- Area: `inventory`
- Inputs: product id
- Outputs: order lines whose status changed
- Errors: unknown product
- Rules enforced: R-inventory-007, R-inventory-008, R-orders-010, R-purchasing-006

#### `record_stock_take`

- Area: `inventory`
- Inputs: product id; counted quantity; mismatch confirmed
- Outputs: stock take id; expected quantity
- Errors: negative quantity; count differs from expected and was not confirmed
- Rules enforced: R-inventory-008, R-inventory-009, R-inventory-010, R-inventory-011

#### `reorder_product`

- Area: `inventory`
- Inputs: product id; vendor id (required when the product has several vendors); quantity (only when neither a suggested nor a minimum reorder quantity applies)
- Outputs: purchase order id (the vendor's oldest New purchase order with the line added or its quantity increased, or a new New purchase order); whether an outstanding purchase order was opened instead
- Errors: product is discontinued; no vendor linked to the product; vendor choice required; quantity required; line could not be added (the purchase order exists without it); reorder failed
- Rules enforced: R-inventory-017, R-inventory-018, R-inventory-019, R-inventory-020, R-inventory-021, R-purchasing-001, R-purchasing-020, R-purchasing-023

#### `delete_product`

- Area: `inventory`
- Inputs: product id; delete confirmed
- Outputs: deleted (the product with its stock takes and vendor links, in one step)
- Errors: product is on an order line; product is on a purchase-order line; delete not confirmed (nothing is deleted)
- Rules enforced: R-inventory-016

### Area `purchasing`: Purchasing and receiving

#### `submit_purchase_order`

- Area: `purchasing`
- Inputs: purchase order id; signed-in user
- Outputs: status Submitted; submitter; submitted date and time
- Errors: purchase order is not New
- Rules enforced: R-purchasing-003, R-purchasing-004

#### `approve_purchase_order`

- Area: `purchasing`
- Inputs: purchase order id; signed-in user
- Outputs: status Approved; approver; approved date and time; stock allocation re-run for its products
- Errors: purchase order is not Submitted; user lacks the approve-purchase-order privilege
- Rules enforced: R-purchasing-003, R-purchasing-005, R-purchasing-006

#### `receive_purchase_order`

- Area: `purchasing`
- Inputs: purchase order id; confirmation
- Outputs: status Received; received date and time on the purchase order and every line; stock allocation re-run for its products
- Errors: purchase order is not Approved; not confirmed
- Rules enforced: R-purchasing-003, R-purchasing-006, R-purchasing-007, R-purchasing-008

#### `close_purchase_order`

- Area: `purchasing`
- Inputs: purchase order id; shipping fee; payment method
- Outputs: status Closed; payment date; tax amount; payment amount
- Errors: purchase order is not Received; shipping fee missing; payment method missing
- Rules enforced: R-purchasing-003, R-purchasing-009, R-purchasing-010

#### `delete_purchase_order`

- Area: `purchasing`
- Inputs: purchase order id
- Outputs: purchase order and its lines deleted
- Errors: purchase order is not New or Submitted
- Rules enforced: R-purchasing-014

#### `add_purchase_order_line`

- Area: `purchasing`
- Inputs: purchase order id; product id; quantity; unit cost
- Outputs: line id (new line, or existing line with the quantity added)
- Errors: purchase order is not New; quantity below the product's minimum reorder quantity; line could not be saved
- Rules enforced: R-purchasing-012, R-purchasing-013, R-purchasing-018, R-purchasing-019, R-purchasing-020

#### `add_no_stock_lines`

- Area: `purchasing`
- Inputs: purchase order id
- Outputs: number of lines added
- Errors: purchase order not saved yet
- Rules enforced: R-purchasing-020, R-purchasing-021

#### `purchase_order_amounts`

- Area: `purchasing`
- Inputs: purchase order id
- Outputs: subtotal; tax; total
- Errors: none
- Rules enforced: R-purchasing-010, R-purchasing-024

### Area `reports`: Sales and Catalog Reports

#### `sales_report_period`

- Area: `reports`
- Inputs: start date (optional); end date (optional)
- Outputs: start date; end date
- Errors: no orders in the database to derive a default period from
- Rules enforced: R-reports-002, R-reports-003

#### `sales_report`

- Area: `reports`
- Inputs: report kind (by employee monthly, by product monthly, by product quarterly); start date; end date; employee id (optional, by employee only)
- Outputs: rows per period and employee or product; period subtotals; grand total; chart series
- Errors: no data for the chosen period
- Rules enforced: R-reports-004, R-reports-005, R-reports-006, R-reports-007, R-reports-008, R-reports-009, R-reports-010

#### `product_catalog_pdf`

- Area: `reports`
- Inputs: none
- Outputs: catalog PDF; table of contents (category, starting page)
- Errors: no catalog rows (warn, still render)
- Rules enforced: R-reports-011, R-reports-012, R-reports-013, R-reports-014, R-reports-015

## Workflows: order of operations

Each step names the service it calls, or the record save or read it relies on.

### `order_to_ship`: Order entry to invoice (printable PDF) to shipping

1. sign in and land on the order list: foundation sign-in
2. start a new order and choose the customer: record save of the order header (defaults R-orders-001, R-orders-002)
3. save the order header: record save of the order header (required fields R-orders-005)
4. add order lines (each line is allocated or marked no stock): save_order_line, which calls allocate_inventory
5. create the invoice and download it as a PDF: create_invoice
6. enter shipped date, shipper and shipping fee and ship the order: ship_order
7. enter payment method and paid date and receive payment: receive_payment
8. close the order: close_order

Rules proven along the way: R-orders-050, R-orders-029, R-orders-030, R-orders-001, R-orders-009, R-orders-015, R-orders-016, R-orders-017, R-orders-018, R-orders-020

### `inventory_restock`: Inventory levels and restocking

1. open a product's stock takes and enter a counted quantity: record_stock_take
2. when the count differs from the expected quantity, confirm it: record_stock_take (mismatch confirmed)
3. see the stock take saved with the system date and the expected quantity, and the product's figures and order line allocations updated: allocate_inventory, then product_stock_levels
4. open the product list and read each product's stock figures: product_stock_levels for each product
5. open a product whose quantity to sell is below its target level and check its suggested reorder quantity: product_stock_levels
6. reorder it, picking the vendor in the dialog when the product has several vendors: reorder_product
7. see the product added to the vendor's oldest New purchase order, or a new one, on the product's purchase-order history: reorder_product (result shown in the product's purchase order history, R-inventory-026)
8. after that purchase order is approved and received, see the physical stock rise and waiting order lines allocated: approve_purchase_order and receive_purchase_order (purchase_order_to_stock), then allocate_inventory and product_stock_levels

Rules proven along the way: R-inventory-030, R-inventory-010, R-purchasing-023, R-inventory-001, R-inventory-006, R-inventory-008, R-inventory-009, R-inventory-011, R-inventory-017, R-inventory-018, R-inventory-019, R-inventory-020, R-inventory-021, R-inventory-022, R-purchasing-018, R-purchasing-001, R-purchasing-020

### `purchase_order_to_stock`: Purchase order to receiving to stock update

1. open the purchase order list and start a new purchase order: read the purchase order list (R-purchasing-025)
2. choose the vendor and save the purchase order (status New): record save of the purchase order (R-purchasing-001, R-purchasing-002)
3. add line items for the vendor's products, or add all no-stock products at once: add_purchase_order_line or add_no_stock_lines
4. submit the purchase order: submit_purchase_order
5. approve it as a user with the approve-purchase-order privilege (its quantities now count as on order): approve_purchase_order, which calls allocate_inventory
6. receive it after confirming (status Received; the received quantities raise available stock): receive_purchase_order, which calls allocate_inventory
7. check the product's available stock on the product page: product_stock_levels
8. enter the shipping fee and payment method and close it (tax, payment amount and payment date stored): purchase_order_amounts, then close_purchase_order

Rules proven along the way: R-purchasing-001, R-purchasing-003, R-purchasing-004, R-purchasing-005, R-purchasing-006, R-purchasing-007, R-purchasing-008, R-purchasing-009, R-purchasing-010, R-purchasing-012, R-purchasing-019

### `kept_reports`: The invoice and the four chosen reports

1. open an invoiced order and open its invoice again as a PDF: render the invoice document as in create_invoice, without changing the order (R-orders-019)
2. open Reports from the main menu and see monthly sales per employee preselected with the default period: sales_report_period
3. change the start and end dates, preview the report and filter it to one salesperson: sales_report_period, then sales_report
4. switch to monthly and to quarterly sales per product and preview each: sales_report
5. save a sales report as PDF: sales_report (document output)
6. choose the product catalog, see the date inputs hidden, and generate it: product_catalog_pdf
7. check the table of contents, the fixed pages and the order form with the shipper list: product_catalog_pdf
8. save the catalog as PDF: product_catalog_pdf (document output)

Rules proven along the way: R-reports-016, R-reports-013, R-reports-014, R-orders-019, R-orders-020, R-orders-021, R-reports-001, R-reports-002, R-reports-007, R-reports-008, R-reports-009, R-reports-010, R-reports-012
