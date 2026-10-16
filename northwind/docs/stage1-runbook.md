# Stage 1 runbook: relink Northwind to PostgreSQL and SQL Server

This runbook moves the Northwind tables off the Access file onto a database server and relinks the Access front end to them over ODBC, so people keep using the same forms and reports. It covers the primary target, PostgreSQL, and SQL Server, on which the same load is also proven. It is written from the engagement settings (`database.primary` postgresql, `database.verify_also` mssql), from [stage1-frontend-changes.md](stage1-frontend-changes.md) and from the workflows in `analysis/rules.json`. The cutover itself, with its timing and sign-off, is in [stage1-cutover.md](stage1-cutover.md). The verified load of the demo data is in [stage1-report.md](stage1-report.md).

It holds names and settings only: no data values, no passwords and no secret values.

**Demo status.** This is the public Northwind demo. There is no client cutover: `database.stage1` is null, `secrets.stage1_target_url_ref` is null and no Windows + Access machine is set up yet (`environment.windows_box.available` is false). The data is loaded only into the local rehearsal databases `mpdata_northwind_demo_stage1` on PostgreSQL 16 and SQL Server 2022 (Docker on the operator host). The settings below that a client sets are marked "not set (demo)".

## Before you start

1. **Who.** The operator runs the load and the checks on the operator host. The client's database administrator (DBA) creates the empty target database and the logins. Someone with Access on a Windows machine relinks the front end and makes the front-end changes. The client's process owner runs the smoke checklist and signs off.
2. **Windows + Access machine.** Needed for the relink, the front-end changes and the smoke checklist. Note the Office version and whether Office is 32-bit or 64-bit (File > Account > About Access). For the demo none is available yet, so the relink has not been rehearsed.
3. **Target database.** The DBA creates one empty database on the client's server (PostgreSQL or SQL Server) and a login that owns it. Stage 1 never creates or drops the client's database; it only fills an empty one.
4. **Secret reference.** The operator stores the target's URL (`postgresql://...` or `mssql://...`, with the login's password) in `$HOME/.config/modernization/data.env` or in `pass`, and names it in the engagement as `secrets.stage1_target_url_ref` (`env:NAME` or `pass:<path>`). The URL never goes into a file in a repo, a chat or a ticket. For the demo this reference is not set.
5. **Network.** Every machine that runs the front end reaches the server's port (PostgreSQL 5432, SQL Server 1433 by default), with encryption on.
6. **Plan.** Read [stage1-cutover.md](stage1-cutover.md) and agree the freeze window and the rollback trigger before the day.
7. **Alternative for SQL Server clients.** A client who prefers a Microsoft tool on their Windows machine can move the tables with Microsoft SQL Server Migration Assistant for Access (SSMA). This pipeline does not call it; when SSMA is used, run the verify command of the cutover afterwards anyway, so the same checks and report apply.

## ODBC driver and Office bitness

| Setting | Value | Note |
|---|---|---|
| ODBC driver (`database.stage1.odbc_driver`) | not set (demo) | Install it on every machine that runs the front end |
| Office bitness (`database.stage1.office_bitness`) | not set (demo) | 32-bit Office needs the 32-bit driver and a 32-bit data source; 64-bit Office needs 64-bit |
| SQL Server driver | Microsoft ODBC Driver 18 for SQL Server | Use it, not the old "SQL Server" driver: with the old one, `datetime2` columns link as text |
| PostgreSQL driver | psqlODBC, the Unicode driver (`PostgreSQL Unicode`, or `PostgreSQL Unicode(x64)` for 64-bit Office) | Set the options below |

psqlODBC options for Access (Configure > Datasource and Page 2, or the connection-string keywords below):

- **True is -1**: on. Access stores Yes as -1; without it, Yes/No fields such as `Products.Discontinued` read wrongly.
- **Bools as Char**: off, so `boolean` columns link as Yes/No.
- **Row Versioning**: on. Access then compares the row version instead of every column when it saves, which stops false write-conflict messages on `Orders` and `OrderDetails` (they hold single-precision columns).
- **Text as LongVarChar**: on (the default), so `text` columns link as Long Text.

On SQL Server the same write-conflict problem is solved on the server: stage1 adds a `mp_rowversion` rowversion column to `Orders` and `OrderDetails`. Do not show it on forms; Access uses it on its own.

## Connection string

Use a DSN-less connection string, so no data source has to be set up on each machine. Fill in the server, port and database the DBA gives you. Do not put the password in the string and do not tick "Save password": Windows authentication (SQL Server) or a password asked when Access first connects keeps it out of the file.

SQL Server (Windows authentication):

```
ODBC;DRIVER={ODBC Driver 18 for SQL Server};SERVER=<server>,1433;DATABASE=<database>;Trusted_Connection=Yes;Encrypt=Yes;TrustServerCertificate=No
```

SQL Server (SQL login; Access asks for the password):

```
ODBC;DRIVER={ODBC Driver 18 for SQL Server};SERVER=<server>,1433;DATABASE=<database>;UID=<login>;Encrypt=Yes;TrustServerCertificate=No
```

PostgreSQL (64-bit Office; for 32-bit Office use `{PostgreSQL Unicode}`; Access asks for the password):

```
ODBC;DRIVER={PostgreSQL Unicode(x64)};SERVER=<server>;PORT=5432;DATABASE=<database>;UID=<login>;SSLmode=require;BoolsAsChar=0;TrueIsMinus1=1;RowVersioning=1;TextAsLongVarchar=1
```

`TrustServerCertificate=Yes` (SQL Server) or `SSLmode=prefer` (PostgreSQL) is only for a test server on a private network, such as the local rehearsal databases.

## Relink the tables

Northwind keeps its tables in the same file as its forms (`source.layout` single-file, no separate back end). Relinking therefore replaces each local table with a linked table of the same name. Work on a copy of the file made after the freeze (see the cutover), never on the only copy.

1. Open the copy with the Shift key held down, so the startup form and its code do not run.
2. For each table below, rename the local table (add `_local` to the name) so the link can take the original name.
3. External Data > New Data Source > From Other Sources > ODBC Database > "Link to the data source by creating a linked table". Choose the data source or enter the connection string above, sign in, and select all 28 tables of the default schema (`dbo` on SQL Server, `public` on PostgreSQL).
4. Access names the links `dbo_<table>` or `public_<table>`. Rename each link back to the original table name (the list below). Queries, forms, reports and code use these names.
5. Every table has a primary key on the server, so Access does not ask for a unique record identifier. If it does, the link went to the wrong table: delete it and link again.
6. Open each linked table once and check that it shows rows and that the row count matches the report of the cutover.
7. When every form in the smoke checklist works, delete the renamed `_local` tables and run Compact and Repair.

The 28 tables, all linked, none left local:

| | | | |
|---|---|---|---|
| `Catalog_TableOfContents` | `Companies` | `CompanyTypes` | `Contacts` |
| `EmployeePrivileges` | `Employees` | `Learn` | `MRU` |
| `NorthwindFeatures` | `OrderDetailStatus` | `OrderDetails` | `OrderStatus` |
| `Orders` | `Privileges` | `ProductCategories` | `ProductVendors` |
| `Products` | `PurchaseOrderDetails` | `PurchaseOrderStatus` | `PurchaseOrders` |
| `States` | `StockTake` | `Strings` | `SystemSettings` |
| `TaxStatus` | `Titles` | `UserSettings` | `Welcome` |

To move to another server later, use External Data > Linked Table Manager, select all links and choose Relink with the new connection string.

## Front-end changes

Each change comes from [stage1-frontend-changes.md](stage1-frontend-changes.md), which lists the procedure and line of every place. Make them in the relinked copy before it is handed out. Changes marked "decided at the gate" need a decision recorded in `answers.md` first.

1. **IDENTITY tables written from code (SQL Server; 43 places).** Add `dbSeeChanges` to the options of each `Database.Execute` call and each dynaset `OpenRecordset` call on a table with an auto-number column; for `Execute`, use `dbFailOnError + dbSeeChanges`. Without it Access stops with run-time error 3622. The places, by procedure and line:
   - `Form_frmCompanyDetail.Form_Delete` lines 451, 456
   - `Form_frmOrderDetails.SetLineItemsStatus` line 646
   - `Form_frmProductDetail.cmdDeleteProduct_Click` lines 144, 149
   - `Form_frmPurchaseOrderDetails.VendorID_BeforeUpdate` line 622
   - `Form_frmPurchaseOrderDetails.cmdAddNostock_Click` line 119
   - `Form_frmPurchaseOrderDetails.cmdReceivePO_Click` line 258
   - `Form_sfrmAdmin_DeleteTestData.cmdRemoveTestData_Click` lines 21, 24, 28, 30, 32, 35, 37, 40, 42, 45, 47, 50, 52, 54, 58, 61, 63, 66, 70, 72, 75, 77
   - `modGlobal.AddToMRU` lines 114, 124; `modGlobal.RemoveFromMRU` line 327
   - `modStartup.SaveSystemSetting` line 115; `modStartup.SaveUserSetting` line 131
   - `modInventory.AllocateInventory` line 19; `modInventory.ProductLastStockTakeDate` line 179
   - `modOrders.CreateRandomOrders` lines 71, 72; `modOrders.SetDatesToCurrent` line 214 (the table name is built at run time, so it may be any IDENTITY table; see item 2)
   - `modPurchaseOrders.AddPurchaseOrderDetail` line 18; `modPurchaseOrders.ReorderProduct` line 157
   - `modRibbonCallback.ddMRU_GetItemCount` line 234

   PostgreSQL does not need this option, and it does no harm there, so make the change once for both.
2. **Writes to a table named at run time (1 place, both servers).** `modOrders.SetDatesToCurrent` (line 214) updates whichever table its name resolves to; once relinked, that is the server table. It runs from the first-run startup routine `modGlobal.OneTimeProcessing` and from the admin form `sfrmAdmin_ResetDates`, and moves the demo's dates forward. Confirm with the process owner whether it should still run after the cutover; if not, disable the call in both places before the copy is handed out. The cutover lists it under "Relink".
3. **Data macros stop firing (20 tables).** The BeforeChange data macros of `Companies`, `CompanyTypes`, `Contacts`, `EmployeePrivileges`, `Employees`, `OrderDetailStatus`, `OrderDetails`, `OrderStatus`, `Orders`, `Privileges`, `ProductCategories`, `ProductVendors`, `Products`, `PurchaseOrderDetails`, `PurchaseOrderStatus`, `PurchaseOrders`, `StockTake`, `Strings`, `TaxStatus` and `Titles` do not run on linked tables. They keep the added-by and modified-on audit fields and one purchase-order status rule (rule ids R-orders-031, R-inventory-028, R-purchasing-027 and R-purchasing-003). Replace them with database triggers or with code in the forms' BeforeUpdate events (decided at the gate). Until then the audit fields stay empty on new and changed rows.
4. **Columns not moved (2).** `Employees.Attachments` and `ProductCategories.ProductCategoryImage` are attachment fields, which a server table cannot hold; stage1 does not create or load them. Remove the controls bound to them, and move the files to a child table or a file store (decided at the gate).
5. **Yes/No field.** `Products.Discontinued` is `boolean NOT NULL DEFAULT false` on PostgreSQL (set 'True is -1' in the driver) and `bit NOT NULL DEFAULT 0` on SQL Server. No front-end change beyond the driver setting.
6. **Hyperlink fields (2).** `Companies.Website` and `NorthwindFeatures.LearnMore` arrive as plain text. Set the Is Hyperlink property of the bound text boxes so they still open as links.
7. **Validation rules (3).** The field rules on `OrderDetails.Quantity`, `StockTake.QuantityOnHand` and `StockTake.ExpectedQuantity` are not enforced on linked tables, and stage1 does not create them. Add the same check to the form's BeforeUpdate event, or ask the DBA for a CHECK constraint (decided at the gate).
8. **Expression default.** `Orders.OrderDate` defaulted to `Now()`. stage1 creates a `CURRENT_TIMESTAMP` server default instead, so new orders still get the date. Access shows the value only after the record is saved.
9. **System table lookup.** `modDAO.HasDataMacro` (line 43) reads `MSysObjects` to find data macros. On linked tables it finds none; once item 3 is done, remove the lookup or make it return False.
10. **Indexes.** Only primary keys and unique indexes are created on the server. Indexes that are not unique (the ones Access adds for each relationship and for sorting) are listed in [stage1-report.md](stage1-report.md); the DBA adds the ones that slow searches down.

## Backups and restore

Back up the server database from the day of the cutover. Keep the backup files on the client's backup storage, never in a repo (the pipeline's guard refuses `.bak` files).

PostgreSQL:

```
pg_dump --format=custom --file=northwind-<date>.dump --host=<server> --username=<login> <database>
pg_restore --clean --if-exists --host=<server> --username=<login> --dbname=<database> northwind-<date>.dump
```

To test a backup, restore it into a new, empty database (`createdb`, then `pg_restore --dbname=<new database>`) and open a few tables.

SQL Server (in SQL Server Management Studio or `sqlcmd`):

```
BACKUP DATABASE [<database>] TO DISK = N'<backup folder>\northwind-<date>.bak' WITH CHECKSUM, INIT;
RESTORE VERIFYONLY FROM DISK = N'<backup folder>\northwind-<date>.bak' WITH CHECKSUM;
RESTORE DATABASE [<database>] FROM DISK = N'<backup folder>\northwind-<date>.bak' WITH REPLACE;
```

A managed server (Azure SQL, Amazon RDS) takes automatic backups with point-in-time restore; check the retention with the DBA instead.

Also keep the pre-cutover copy of the Access file (read-only) and each released copy of the relinked front end.

## Rollback

Rollback puts people back on the Access file they used before the cutover.

1. Everyone closes the relinked front end.
2. Hand out the pre-cutover copy of the Access file again (its tables are local, so it does not touch the server). For an app with a separate back end, rollback means relinking the front end to the old back-end file with the Linked Table Manager instead.
3. Rows entered on the server after the relink are not in the old file. Before deciding, ask the operator for the row counts per table (`mp-data stage1 ... --verify` reports them) and re-enter or copy those rows by hand.
4. Leave the server database as it is until the cause is fixed; the next attempt starts with the DBA dropping and recreating it empty, as the cutover describes.

The cutover's rollback section says when to roll back and who decides.
