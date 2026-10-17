# Walkthrough script: Northwind

The walkthrough follows the first must-keep workflow, `order_to_ship` (order entry to invoice, printable PDF, to shipping), from sign-in to closing the order. It is recorded from the end-to-end test `test_walkthrough` in `app/tests/e2e/test_walkthrough.py`, which runs the same steps and checks as `test_order_to_ship`, pausing 1.2 seconds between steps. Every name and figure on screen comes from synthetic seed 1 (invented data); no data of the original application appears. The narration below runs about 3 minutes; slow the video down or hold a frame where a scene needs more time.

## Before you record

- The S6 demo gate records it from the merged main in a plain terminal: from `northwind/app/`, with the env file sourced and `MP_DB_SUFFIX=s6_gate`, `E2E_VIDEO_DIR=/home/cloudcli/engagements/northwind-demo/private/synthetic/media/walkthrough uv run pytest -q --create-db -m walkthrough tests/e2e`. The video lands as `walkthrough.webm` in that folder (1280x800). It stays in the private directory's design zone and is never committed.
- Record the voice separately and keep to the scenes below; the test signs in with a random password that never appears on screen.
- Upload the video unlisted; the operator puts its link into the root README at the S6 gate.

## Scenes

### 1. Opening (about 15 s)

**On screen:** the app's start page in the browser, before sign-in.

**Say:** "This is Northwind, Microsoft's sample order-management app for Access, rebuilt as a Django web app by our modernization pipeline. The original has 28 tables, 65 queries, 40 forms, 15 reports and about 6,900 lines of VBA. We'll take one order from entry to invoice to shipping, the first workflow the client must keep. Everything you see is synthetic test data."

### 2. Sign in and land on the order list (about 15 s)

**On screen:** the sign-in page, then the Orders list with its footer showing the number of orders and their total.

**Say:** "A staff user signs in. As in Access, the first screen after signing in is the order list (rule R-orders-050). Sign-in and roles are new: staff, and approvers who may approve purchase orders, mirroring the original's privilege."

### 3. Start a new order and choose the customer (about 20 s)

**On screen:** New order; the customer, the salesperson, the shipping fee and the tax status are filled in; the tax rate is already filled.

**Say:** "A new order starts from the order list (R-orders-029). The tax rate comes pre-filled with the default from the system settings, as it did in the original (R-orders-001). We pick a customer and a salesperson, enter a shipping fee and make the order taxable."

### 4. Save the order header (about 15 s)

**On screen:** the order screen with the badge New and Create invoice highlighted as the next action.

**Say:** "Saved, the order is New. The screen highlights the next allowed step, Create invoice: as in the original, an order moves forward one step at a time, New, Invoiced, Shipped, Paid, Closed, and only through its actions (R-orders-030)."

### 5. Add order lines (about 20 s)

**On screen:** two lines added; one shows Allocated, the other No Stock; the product name of a line is a link to the product screen.

**Say:** "Each line checks stock as it is added. One product has enough to sell, so its line is Allocated; the other has none, so its line is No Stock (R-orders-009). A line's product opens that product's screen, as a double-click did in Access."

### 6. Out of turn: refused (about 20 s)

**On screen:** Ship order pressed on a New order: a message names the rule, the badge stays New; Create invoice pressed: a message says every line must be Allocated (R-orders-015); the No Stock line is deleted after a confirmation; the amounts show subtotal, tax, shipping and total.

**Say:** "Trying to ship before invoicing is refused with a message, and so is invoicing while a line has no stock: an order is invoiced only when every line is Allocated, the rule the client confirmed. We delete the No Stock line after confirming. The totals are worked out as in the original: tax on the line subtotal only, never on the shipping fee."

### 7. Create the invoice and download the PDF (about 25 s)

**On screen:** the invoice page with the invoice number (the order number) and the total; back on the order, the badge Invoiced and the line Invoiced; Invoice PDF downloads.

**Say:** "Create invoice opens the invoice: its number is the order number and its total matches the order (R-orders-020). The order and its lines are now Invoiced. The same invoice downloads as a printable PDF, generated with WeasyPrint; the test reads the PDF's text and checks the number and the total."

### 8. Ship the order (about 15 s)

**On screen:** Ship order highlighted; shipped date and shipper entered; the badge Shipped and the line Shipped.

**Say:** "Shipping is the next step: it needs a shipped date, a shipper and the shipping fee, which came with the order, and the order and its lines become Shipped (R-orders-016)."

### 9. Receive payment (about 10 s)

**On screen:** payment method and paid date entered; the badge Paid.

**Say:** "Then payment: a payment method and the paid date, and the order is Paid (R-orders-017)."

### 10. Close the order (about 15 s)

**On screen:** the confirmation box ticked, Close order; the badge Closed, no Edit link, the total unchanged.

**Say:** "Finally the order is closed after a confirmation (R-orders-018). A closed order can no longer be edited, and its total is the one we started with."

## Closing

### 11. Where the evidence is (about 25 s)

**On screen:** hold the closed order (or an end card with the repository path `northwind/docs/equivalence-report.md`).

**Say:** "How do we check the new app against the old one? For every query the client keeps, an open-source Access engine, UCanAccess, recorded the original query's output, on the original data and on three synthetic datasets; that is a reference, not Microsoft Access itself. The new app's outputs matched those references in 428 of 428 checks, on PostgreSQL and SQL Server, the lowest of the 8 cells at 100 percent. Seven of the queries use date or formatting functions that were not confirmed on Access, and the report lists them. The 157 rule tests and the 5 end-to-end tests pass too. The full report, with its limits, is in `northwind/docs/equivalence-report.md` in the repository, and the README shows how to re-run the synthetic checks yourself."
