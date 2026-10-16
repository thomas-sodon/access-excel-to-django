# Stage 1 cutover plan: Northwind to PostgreSQL and SQL Server

This is the plan for the day the Northwind tables move off the Access file onto the client's database server. It is written from the engagement settings (`database.stage1`, `secrets.stage1_target_url_ref`), from [stage1-runbook.md](stage1-runbook.md) and from the workflows in `analysis/rules.json`. The runbook holds the how-to for each step (driver, connection string, relinking, front-end changes, backups); this plan holds the order, the checks and the decisions.

It holds names and settings only: no data values and no secret values.

**Demo status.** This is the public Northwind demo: `database.stage1` is null and `secrets.stage1_target_url_ref` is null, so there is no client cutover. The settings below are marked "not set (demo)". The same load and checks were run on the demo data against the local rehearsal databases `mpdata_northwind_demo_stage1` (PostgreSQL and SQL Server); see [stage1-report.md](stage1-report.md). For a client, the operator fills these settings in the engagement before the day.

| Setting | Value |
|---|---|
| Freeze window (`database.stage1.freeze_window`) | not set (demo) |
| Fresh copy (`database.stage1.fresh_copy`) | not set (demo) |
| Relink by (`database.stage1.relink_by`) | not set (demo) |
| Rollback (`database.stage1.rollback`) | not set (demo) |
| Target database (`secrets.stage1_target_url_ref`) | not set (demo); a reference (`env:NAME` or `pass:<path>`), never the URL |
| Primary dialect (`database.primary`) | PostgreSQL; the same plan works for SQL Server (`database.verify_also`) |

## Freeze window

1. Agree the window with the client's process owner: long enough for the copy, the load, the relink and the smoke checklist, plus time to roll back. Northwind's data loads in seconds; the relink and the checklist take most of the time.
2. Tell every user when the window starts and that changes made after it are lost.
3. At the start, everyone closes Northwind. The operator checks that no lock file (`.laccdb`) sits next to the Access file before copying it.
4. Until sign-off or rollback, nobody opens the old file for editing.

## Fresh copy

1. Copy the Access file that holds the tables (for Northwind, the app file itself; for an app with a separate back end, the back-end file) to the operator host, at the path the engagement names in `database.stage1.fresh_copy`. That path lies under the private `sources/` directory, which only `mp-data` reads.
2. Never compact or repair the original. If the copy needs it, compact the copy.
3. Record the copy's size and the sha256 that the report prints; the report names it as the fresh copy.
4. Keep the original, read-only, as the rollback copy.

## Load and verify

Before the day, the DBA creates the empty target database and the operator stores its URL under the secret reference `secrets.stage1_target_url_ref`.

Run both commands in a plain terminal on the operator host, outside any Claude session. The first creates the schema in the empty database and loads the fresh copy; it reads the URL from the secret reference and never prints it. The second checks tables, columns, types, keys, foreign keys, row counts, a digest per table, foreign-key orphans and identities, and writes the report.

```
mp-data stage1 /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/engagement.json --target-db secret:stage1_target_url_ref --dataset fresh-copy
mp-data stage1 /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/engagement.json --target-db secret:stage1_target_url_ref --dataset fresh-copy --verify --require-rows --report /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/stage1-cutover-report.md
```

Both must print `"status":"ok"`. The load refuses a database that is not empty ("target not empty; ask the DBA to drop and recreate it").

If the load stops part-way, have the DBA drop and recreate the empty database, then run both commands again.

## Relink

1. On the Windows + Access machine, follow [stage1-runbook.md](stage1-runbook.md), "Relink the tables", on a copy made after the freeze: all 28 tables, renamed back to their original names.
2. Make the front-end changes of the runbook ("Front-end changes") in the same copy.
3. Decide, with the process owner, about the one write to a table named at run time: `modOrders.SetDatesToCurrent` (runbook "Front-end changes", item 2). It runs from the first-run startup routine and the admin form `sfrmAdmin_ResetDates` and, once relinked, changes dates in the server tables. Unless the process owner wants it kept, disable both calls before the copy is handed out, and do not open the relinked copy for the first time before that is done. If it is kept, first check that the first-run (one-time processing) setting carried into the loaded data already marks one-time processing as done, so the startup call does not shift the dates when users first open the relinked copy.
4. Install the ODBC driver whose bitness matches Office on every machine that runs Northwind, then hand out the relinked copy (the person named in `database.stage1.relink_by` does this; not set for the demo).

## Smoke checklist

Run each item on the relinked copy, signed in as a user with the needed privileges. Each must work as it did before the cutover.

- [ ] **Sign in.** The login form opens, a user signs in and the order list opens.
- [ ] **Order entry to invoice to shipping** (workflow `order_to_ship`). Start a new order for a customer, save the header, add order lines (each is allocated or marked no stock), create the invoice and open it as a PDF, enter the shipped date, shipper and fee and ship the order, enter the payment and close it.
- [ ] **Inventory levels and restocking** (workflow `inventory_restock`). Enter a stock take on a product and confirm a differing count, check the product list's stock figures, reorder a product below its target level (picking the vendor when it has several) and see it on a purchase order.
- [ ] **Purchase order to receiving to stock update** (workflow `purchase_order_to_stock`). Create a purchase order for a vendor, add lines, submit, approve (as a user with that privilege), receive it, and see the product's available stock rise; then close it with the shipping fee and payment method.
- [ ] **The invoice and the four chosen reports** (workflow `kept_reports`). Reopen an invoiced order's invoice as a PDF; preview monthly sales per employee, sales per product monthly and quarterly, and the product catalog, and save one as PDF.
- [ ] **Company list and details.** Open a customer and a vendor; their contacts, orders and purchase orders show.
- [ ] **Employee list and details.** Open an employee; titles and privileges show (the attachments control is gone, see the runbook).
- [ ] **Dates unchanged.** After the first start of the relinked copy, the order and purchase-order dates still match the fresh copy (the verify command's digests still match unless people have entered rows).
- [ ] **No error dialogs.** No ODBC error, run-time error 3622 or write-conflict message appeared during the checklist.

## Rollback

Roll back when an item of the smoke checklist fails and cannot be fixed inside the freeze window, or when the verify command does not print `"status":"ok"` and the DBA cannot recreate the database in time. The client's process owner decides, after hearing the operator (the engagement's `database.stage1.rollback` records the agreed trigger; not set for the demo).

1. Everyone closes the relinked copy.
2. Hand out the pre-cutover Access file again (or, for an app with a separate back end, relink to the old back-end file), as in the runbook's Rollback section.
3. Rows entered on the server since the relink must be re-entered in the old file; the operator gives the row counts per table.
4. Leave the server database untouched; before the next attempt the DBA drops and recreates it empty.

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Client process owner (smoke checklist passed) | | | |
| Client DBA (database, logins and first backup in place) | | | |
| Operator (both commands printed `"status":"ok"`) | | | |

Record with the sign-off the sha256 of the fresh copy (in the report's Inputs), the sha256 of `stage1-cutover-report.md` itself, and the date the old file was set read-only.
