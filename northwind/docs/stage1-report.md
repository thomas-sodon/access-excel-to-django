# Stage 1 load report

Written by `toolkit stage1` for engagement `northwind-demo`. It describes the verified state of each target database: row counts, whether the per-table digest of the canonical rows matches the dataset (the digests themselves are not written), foreign-key orphans, and everything that was not created. It holds names, counts and file hashes only, and no timestamps, so the same data gives the same bytes.

## Inputs

| Input | sha256 |
|---|---|
| schema.json | `301aeeaf6414d71515b78666b5ef87dad13ede703ce797d5a16f50a95e6c2074` |
| dataset.json | `92ab952fdece8a4b2773f4fcee7c8bf588095ec36a98b66e8c92c2efa61ce1d6` |

## Result

Every check passed.

## PostgreSQL

Target: local database `mpdata_northwind_demo_stage1`.

| Table | Dataset rows | Target rows | Digest match | FK orphans |
|---|---|---|---|---|
| `Catalog_TableOfContents` | 16 | 16 | yes | 0 |
| `CompanyTypes` | 4 | 4 | yes | 0 |
| `Learn` | 15 | 15 | yes | 0 |
| `NorthwindFeatures` | 39 | 39 | yes | 0 |
| `OrderDetailStatus` | 6 | 6 | yes | 0 |
| `OrderStatus` | 5 | 5 | yes | 0 |
| `Privileges` | 1 | 1 | yes | 0 |
| `ProductCategories` | 16 | 16 | yes | 0 |
| `Products` | 43 | 43 | yes | 0 |
| `PurchaseOrderStatus` | 5 | 5 | yes | 0 |
| `States` | 51 | 51 | yes | 0 |
| `StockTake` | 43 | 43 | yes | 0 |
| `Strings` | 49 | 49 | yes | 0 |
| `SystemSettings` | 5 | 5 | yes | 0 |
| `TaxStatus` | 2 | 2 | yes | 0 |
| `Companies` | 13 | 13 | yes | 0 |
| `Contacts` | 6 | 6 | yes | 0 |
| `ProductVendors` | 47 | 47 | yes | 0 |
| `Titles` | 3 | 3 | yes | 0 |
| `Employees` | 10 | 10 | yes | 0 |
| `EmployeePrivileges` | 3 | 3 | yes | 0 |
| `MRU` | 0 | 0 | yes | 0 |
| `Orders` | 52 | 52 | yes | 0 |
| `OrderDetails` | 130 | 130 | yes | 0 |
| `PurchaseOrders` | 2 | 2 | yes | 0 |
| `PurchaseOrderDetails` | 43 | 43 | yes | 0 |
| `UserSettings` | 1 | 1 | yes | 0 |
| `Welcome` | 1 | 1 | yes | 0 |

## SQL Server

Target: local database `mpdata_northwind_demo_stage1`.

| Table | Dataset rows | Target rows | Digest match | FK orphans |
|---|---|---|---|---|
| `Catalog_TableOfContents` | 16 | 16 | yes | 0 |
| `CompanyTypes` | 4 | 4 | yes | 0 |
| `Learn` | 15 | 15 | yes | 0 |
| `NorthwindFeatures` | 39 | 39 | yes | 0 |
| `OrderDetailStatus` | 6 | 6 | yes | 0 |
| `OrderStatus` | 5 | 5 | yes | 0 |
| `Privileges` | 1 | 1 | yes | 0 |
| `ProductCategories` | 16 | 16 | yes | 0 |
| `Products` | 43 | 43 | yes | 0 |
| `PurchaseOrderStatus` | 5 | 5 | yes | 0 |
| `States` | 51 | 51 | yes | 0 |
| `StockTake` | 43 | 43 | yes | 0 |
| `Strings` | 49 | 49 | yes | 0 |
| `SystemSettings` | 5 | 5 | yes | 0 |
| `TaxStatus` | 2 | 2 | yes | 0 |
| `Companies` | 13 | 13 | yes | 0 |
| `Contacts` | 6 | 6 | yes | 0 |
| `ProductVendors` | 47 | 47 | yes | 0 |
| `Titles` | 3 | 3 | yes | 0 |
| `Employees` | 10 | 10 | yes | 0 |
| `EmployeePrivileges` | 3 | 3 | yes | 0 |
| `MRU` | 0 | 0 | yes | 0 |
| `Orders` | 52 | 52 | yes | 0 |
| `OrderDetails` | 130 | 130 | yes | 0 |
| `PurchaseOrders` | 2 | 2 | yes | 0 |
| `PurchaseOrderDetails` | 43 | 43 | yes | 0 |
| `UserSettings` | 1 | 1 | yes | 0 |
| `Welcome` | 1 | 1 | yes | 0 |

## Omitted columns

| Column | Type | Reason | Dialects |
|---|---|---|---|
| `Employees.Attachments` | complex | complex: not created, not loaded | PostgreSQL, SQL Server |
| `ProductCategories.ProductCategoryImage` | complex | complex: not created, not loaded | PostgreSQL, SQL Server |

## Relationships not created

None: every relationship with enforced integrity is a foreign key.

### Cascade rules changed to NO ACTION

None.

## Other objects not created

Indexes that are not unique (Access keeps one per relationship and for sorting) are left to the database administrator:

| Table | Indexes not created | Dialects |
|---|---|---|
| `Catalog_TableOfContents` | `TocPage` | PostgreSQL, SQL Server |
| `Companies` | `CompanyTypesCompanies`, `New_CompanyTypesCompanies`, `New_StatesCompanies`, `New_TaxStatusCompanies`, `StatesCompanies`, `TaxStatusCompanies` | PostgreSQL, SQL Server |
| `Contacts` | `CompaniesContacts`, `New_CompaniesContacts` | PostgreSQL, SQL Server |
| `EmployeePrivileges` | `EmployeesEmployeePrivileges`, `New_EmployeesEmployeePrivileges`, `New_PrivilegesEmployeePrivileges`, `PrivilegeID`, `PrivilegesEmployeePrivileges` | PostgreSQL, SQL Server |
| `Employees` | `EmployeesEmployees`, `New_EmployeesEmployees`, `New_SalutationsEmployees`, `SalutationsEmployees` | PostgreSQL, SQL Server |
| `MRU` | `EmployeesMRU`, `New_EmployeesMRU` | PostgreSQL, SQL Server |
| `OrderDetails` | `New_OrderDetailsStatusOrderDetails`, `New_OrdersOrderDetails`, `New_ProductsOrderDetails`, `OrderDetailsStatusOrderDetails`, `OrdersOrderDetails`, `ProductID`, `ProductsOrderDetails`, `StatusID` | PostgreSQL, SQL Server |
| `Orders` | `CompaniesOrders`, `CompaniesOrders1`, `EmployeesOrders`, `New_CompaniesOrders`, `New_CompaniesOrders1`, `New_EmployeesOrders`, `New_OrdersStatusOrders`, `New_TaxStatusOrders`, `OrderDate`, `OrdersStatusOrders`, `TaxStatusOrders` | PostgreSQL, SQL Server |
| `ProductVendors` | `CompaniesProductVendors`, `New_CompaniesProductVendors`, `New_ProductsProductVendors`, `ProductsProductVendors`, `VendorID` | PostgreSQL, SQL Server |
| `Products` | `New_ProductCategories_NEWProducts`, `ProductCategories_NEWProducts` | PostgreSQL, SQL Server |
| `PurchaseOrderDetails` | `New_ProductsPurchaseOrderDetails`, `New_PurchaseOrdersPurchaseOrderDetails`, `ProductsPurchaseOrderDetails`, `PurchaseOrdersPurchaseOrderDetails` | PostgreSQL, SQL Server |
| `PurchaseOrders` | `CompaniesPurchaseOrders`, `EmployeesPurchaseOrders1`, `EmployeesPurchaseOrders2`, `New_CompaniesPurchaseOrders`, `New_EmployeesPurchaseOrders1`, `New_EmployeesPurchaseOrders2`, `New_PurchaseOrdersStatusPurchaseOrders`, `PurchaseOrdersStatusPurchaseOrders`, `StatusCode`, `SubmittedDate` | PostgreSQL, SQL Server |
| `StockTake` | `New_ProductsStockTake`, `ProductsStockTake` | PostgreSQL, SQL Server |

| Kind | Object | Reason | Dialects |
|---|---|---|---|
| validation rule | `OrderDetails.Quantity` | field validation rule | PostgreSQL, SQL Server |
| validation rule | `StockTake.ExpectedQuantity` | field validation rule | PostgreSQL, SQL Server |
| validation rule | `StockTake.QuantityOnHand` | field validation rule | PostgreSQL, SQL Server |

## Columns added

| Column | Dialects | Why |
|---|---|---|
| `OrderDetails.mp_rowversion` | SQL Server | row version, so Access stops reporting write conflicts on floating-point columns |
| `Orders.mp_rowversion` | SQL Server | row version, so Access stops reporting write conflicts on floating-point columns |
