# Orders, Invoicing and Shipping: business rules (area `orders`)

Engagement northwind-demo, spec version 1.0, status **kept**. Generated together with `analysis/rules/orders.json`; the JSON file is the source of truth and this page is its reader's copy. Statements are paraphrased from the scrubbed design; no code, query text or data is copied.

## Summary

This area covers taking a customer order, invoicing it as a printable PDF, shipping it, recording payment and closing it, plus the people and companies an order refers to: customers, shippers and vendors with their contacts, and employees (salespeople and supervisors). Stock levels and allocation belong to the inventory area and purchase orders to the purchasing area; this area calls the inventory area's allocation when order lines change. Sign-in and privileges move to the foundation (S4) as local sign-in and roles; the audit columns that every table carries are stamped by the foundation as well. Access-only plumbing (ribbon, message dialogs, error log, demo-data tools, help and welcome screens) is dropped.

- Rules: 50 (38 rule tests, 9 proven by equivalence units, 3 end-to-end)
- Objects: 323 (202 keep, 121 drop, 0 out of scope)
- Open questions: 12
- Must keep in this area: order entry to invoice (printable PDF) to shipping (workflow `order_to_ship`), and the invoice report `rptInvoice` (component `orders.reports`).

## Rules

| Id | Rule | Trigger | Sources | Tables | Confidence | Proven by | Questions |
|---|---|---|---|---|---|---|---|
| R-orders-001 | When a new order is started it is pre-filled: the salesperson is the signed-in employee, the tax rate is the default sales tax rate from system settings, the status is New and the order date is the current date and time. The default tax rate is stored in system settings as a whole number of thousandths and divided by 1000 when read. | `form:frmOrderDetails.BeforeInsert` | procedure Form_frmOrderDetails.Form_BeforeInsert<br>procedure modStartup.GetSystemSetting<br>procedure modGlobal.Get_UserID<br>table SystemSettings | Orders, SystemSettings | high | rule |  |
| R-orders-002 | Choosing the customer of an order sets the order's tax status to that customer's standard tax status; the user may still change it while the order is New. | `form:frmOrderDetails.CustomerID.AfterUpdate` | procedure Form_frmOrderDetails.CustomerID_AfterUpdate<br>procedure modCompanies.GetTaxStatusID | Orders, Companies | high | rule |  |
| R-orders-003 | The customer of an order is chosen only from companies whose type is Customer, and the shipper only from companies whose type is Shipper; both choice lists are sorted by company name. | `query:qrycboCustomers` | query qrycboCustomers<br>query qrycboShippers<br>query qryCustomers<br>query qryShippers | Companies | high | equivalence |  |
| R-orders-004 | Order lines cannot be entered until the order itself has been saved; trying to do so shows a message and sends the user back to the customer field. | `form:frmOrderDetails.sfrmOrderLineItems.Enter` | procedure Form_frmOrderDetails.sfrmOrderLineItems_Enter<br>procedure Form_sfrmOrderLineItems.Form_Error | Orders, OrderDetails | high | rule |  |
| R-orders-005 | A record on the order, order line, company, contact or employee screens cannot be saved while any column that the table marks as required is blank; the save is refused with a message and the blank required fields are highlighted until the record is saved. | `form:frmOrderDetails.BeforeUpdate` | procedure Form_frmOrderDetails.Form_BeforeUpdate<br>procedure Form_frmOrderDetails.Form_AfterUpdate<br>procedure Form_frmOrderDetails.sfrmOrderLineItems_Exit<br>procedure Form_sfrmOrderLineItems.Form_BeforeUpdate<br>procedure Form_frmCompanyDetail.Form_BeforeUpdate<br>procedure Form_frmCompanyDetail.cmdSave_Click<br>procedure Form_frmCompanyDetail.Form_AfterUpdate<br>procedure Form_sfrmCompanyDetail_Contacts.Form_BeforeUpdate<br>procedure Form_sfrmCompanyDetail_Contacts.Form_AfterUpdate<br>procedure Form_frmEmployeeList.Form_BeforeUpdate<br>procedure Form_frmEmployeeList.Form_AfterUpdate<br>procedure modValidation.ValidateForm<br>procedure modValidation.IsValidForm<br>procedure modValidation.IsBoundToRequiredField<br>procedure modValidation.HighlightInvalidControls<br>procedure modValidation.HighlightControl<br>procedure modValidation.ValidateForm_RemoveHighlights | Orders, OrderDetails, Companies, Contacts, Employees | high | rule |  |
| R-orders-006 | An order line's quantity must be greater than zero. | `form:sfrmOrderLineItems.BeforeUpdate` | table OrderDetails | OrderDetails | high | rule |  |
| R-orders-007 | A product can appear at most once on the same order (one line per order and product). | `form:sfrmOrderLineItems.BeforeUpdate` | table OrderDetails | OrderDetails | high | rule |  |
| R-orders-008 | On an order line the product list can be narrowed to one product category (or show all products); choosing a product copies the product's current list price into the line's unit price, and the line's discount starts at zero. A line whose chosen product has no price gets no product. | `form:sfrmOrderLineItems.ProductID.AfterUpdate` | procedure Form_sfrmOrderLineItems.ProductID_AfterUpdate<br>procedure Form_sfrmOrderLineItems.cboProductCategories_AfterUpdate<br>procedure Form_sfrmOrderLineItems.ProductID_GotFocus<br>table OrderDetails | OrderDetails, Products | high | rule |  |
| R-orders-009 | A new order line starts with status New. When the line is saved with both a product and a quantity, its status becomes Allocated if the product's available stock (computed by the inventory area) covers the whole quantity, otherwise No Stock. | `form:sfrmOrderLineItems.BeforeUpdate` | procedure Form_sfrmOrderLineItems.Form_BeforeInsert<br>procedure Form_sfrmOrderLineItems.Form_BeforeUpdate<br>procedure Form_sfrmOrderLineItems.SetOrderDetailStatus | OrderDetails, Products | high | rule |  |
| R-orders-010 | After an order line is saved, changed to another product, or deleted, stock allocation is run again for the affected product (and for the previous product when the product was changed), so waiting lines of other orders can move between Allocated, On Order and No Stock, oldest order first. Deleting a line asks for confirmation first. | `form:sfrmOrderLineItems.AfterUpdate` | procedure Form_sfrmOrderLineItems.Form_AfterUpdate<br>procedure Form_sfrmOrderLineItems.ReallocateInventory<br>procedure Form_sfrmOrderLineItems.Form_Current<br>procedure Form_sfrmOrderLineItems.Form_AfterDelConfirm<br>procedure Form_sfrmOrderLineItems.Form_Delete<br>procedure Form_sfrmOrderLineItems.Form_BeforeDelConfirm | OrderDetails, Products | high | rule |  |
| R-orders-011 | Deleting an order asks for confirmation, deletes all its lines with it and re-runs stock allocation for each of those lines' products. | `form:frmOrderDetails.Delete` | procedure Form_frmOrderDetails.Form_Delete<br>procedure Form_frmOrderDetails.Form_BeforeDelConfirm | Orders, OrderDetails | high | rule |  |
| R-orders-012 | An order can be deleted only while its status is New or Invoiced; deleting a Shipped, Paid or Closed order is refused with a message, and deleting an unsaved order does nothing. | `form:frmOrderDetails.cmdDeleteOrder.Click` | procedure Form_frmOrderDetails.cmdDeleteOrder_Click | Orders | high | rule |  |
| R-orders-013 | Order lines can be added, changed or deleted only while the order is unsaved or New; once the order is invoiced its lines are read-only. | `form:frmOrderDetails.Current` | procedure Form_frmOrderDetails.Form_Current<br>procedure Form_frmOrderDetails.SetFormStatus | Orders, OrderDetails | high | rule |  |
| R-orders-014 | Which order fields can be edited depends on the order status: on an unsaved order the customer, salesperson, notes, shipping fee, tax rate and tax status; when New the notes, shipping fee, tax rate and tax status (customer and salesperson are fixed once saved); when Invoiced the notes, shipped date and shipper; when Shipped the notes, payment method and paid date; when Paid only the notes; when Closed nothing. Order number, status, order date, invoice date, tax amount and total are never edited by hand. | `form:frmOrderDetails.Current` | procedure Form_frmOrderDetails.LockControls<br>procedure Form_frmOrderDetails.Form_Current<br>procedure Form_frmOrderDetails.SetFormStatus | Orders | high | rule | Q-orders-002 |
| R-orders-015 | Creating the invoice is allowed only for a New order that has at least one line, all of whose lines are Allocated (no partial invoices), and whose shipping fee is filled in (zero is accepted, blank is not; the blank field is highlighted). It saves the order, opens the invoice, sets the status to Invoiced, stamps the invoice date with the current date and time and sets every line to Invoiced. | `form:frmOrderDetails.cmdCreateInvoice.Click` | procedure Form_frmOrderDetails.cmdCreateInvoice_Click<br>procedure Form_frmOrderDetails.AllInvoiceLineItemsHaveStatus<br>procedure Form_frmOrderDetails.ShippingFeeFilledOut<br>procedure Form_frmOrderDetails.SetLineItemsStatus | Orders, OrderDetails | high | rule | Q-orders-003, Q-orders-012 |
| R-orders-016 | Shipping is allowed only for an Invoiced order and needs the shipped date, the shipper and the shipping fee (missing ones are highlighted and the user is told); it sets the order to Shipped and every line to Shipped. | `form:frmOrderDetails.cmdShipOrder.Click` | procedure Form_frmOrderDetails.cmdShipOrder_Click<br>procedure Form_frmOrderDetails.ShippingFieldsFilledOut<br>procedure Form_frmOrderDetails.SetLineItemsStatus | Orders, OrderDetails | high | rule | Q-orders-002 |
| R-orders-017 | Receiving payment is allowed only for a Shipped order and needs the payment method (one of the fixed methods offered by the order screen) and the paid date (missing ones are highlighted and the user is told); it sets the order to Paid. | `form:frmOrderDetails.cmdReceivePayment.Click` | procedure Form_frmOrderDetails.cmdReceivePayment_Click<br>procedure Form_frmOrderDetails.PaidFieldsFilledOut | Orders | high | rule | Q-orders-002 |
| R-orders-018 | Closing is allowed only for a Paid order and only after the user confirms; it sets the order to Closed, after which nothing on the order can be edited. | `form:frmOrderDetails.cmdCloseOrder.Click` | procedure Form_frmOrderDetails.cmdCloseOrder_Click | Orders | high | rule |  |
| R-orders-019 | Once an order is past New, its invoice can be opened again at any time; reopening it never changes the order or its lines. On an unsaved or New order the reprint action is not offered. | `form:frmOrderDetails.cmdPrintInvoice.Click` | procedure Form_frmOrderDetails.cmdPrintInvoice_Click<br>procedure Form_frmOrderDetails.Form_Current<br>procedure Form_frmOrderDetails.SetFormStatus | Orders | high | rule |  |
| R-orders-020 | The invoice is a printable document for one order: the invoice number is the order number; it shows the date it is printed, the customer's name and address (as bill-to and ship-to), the salesperson's full name and the trading company's own address (the company whose type is the trading company itself); one row per line with product code, product name, quantity, unit price, discount and extended price = quantity x unit price x (1 - discount); then subtotal = sum of extended prices, tax = tax rate x subtotal when the order's tax status is Taxable and 0 otherwise (shipping is not taxed), shipping = the order's shipping fee, and total = subtotal + tax + shipping. | `query:qryInvoice` | report rptInvoice<br>query qryInvoice<br>procedure modGlobal.GetNorthwindAddress | Orders, OrderDetails, Companies, Employees, Products | high | equivalence | Q-orders-001, Q-orders-003 |
| R-orders-021 | Opening the invoice for an order that has no lines shows a 'nothing to print' message instead of an empty invoice. | `report:rptInvoice.NoData` | procedure Report_rptInvoice.Report_NoData | Orders, OrderDetails | medium | rule |  |
| R-orders-022 | The order screen shows each line's price = quantity x (1 - discount) x unit price, the lines' subtotal, the tax amount = tax rate x subtotal when the order's tax status is Taxable and 0 otherwise, and the order total = subtotal + tax amount + shipping fee (a blank fee counts as 0). | `form:frmOrderDetails.Current` | form frmOrderDetails<br>form sfrmOrderLineItems | Orders, OrderDetails | high | rule | Q-orders-003 |
| R-orders-023 | An order's total is the sum over its lines of quantity x (1 - discount) x unit price, without tax and shipping; an order without lines has no total (blank). | `query:qryOrderTotal` | query qryOrderTotal | Orders, OrderDetails | high | equivalence |  |
| R-orders-024 | The order list shows every order whose customer is a Customer-type company, newest order number first, with the customer name, the salesperson's full name, the order total, the order status name, the order date without its time, and the least advanced status among its lines (the line status with the lowest sort order; blank when the order has no lines). | `query:qryOrderList` | query qryOrderList<br>query qryOrderList_DetailStatus<br>query qryOrderList_DetailStatus_Lowest | Orders, OrderDetails, OrderDetailStatus, OrderStatus, Companies, Employees | high | equivalence |  |
| R-orders-025 | The order list has four filters: Open orders (every status except Closed), Recent orders (order date within the last 30 days; when there are none the user is told), My orders (salesperson is the signed-in employee) and All orders. Any filter left over from an earlier session is cleared when the list opens and the selected filter is applied. | `form:frmOrderList.fraFilter.AfterUpdate` | procedure Form_frmOrderList.fraFilter_AfterUpdate<br>procedure Form_frmOrderList.Form_Open | Orders | high | rule | Q-orders-009 |
| R-orders-026 | The order list footer shows the number of orders and the sum of their order totals for the rows currently shown. | `form:frmOrderList.Current` | form frmOrderList | Orders, OrderDetails | medium | rule |  |
| R-orders-027 | The employee screen shows that employee's most recent orders (at most 20, newest order number first) with date, total, status, salesperson and customer. | `query:qryOrders_MostRecent` | query qryOrders_MostRecent<br>form sfrmOrders_MostRecent_ByEmployee | Orders, Employees | medium | equivalence | Q-orders-004 |
| R-orders-028 | For a Customer company the company screen lists all its orders (newest first) with salesperson, shipper, total and status; for a Shipper company it lists the orders it shipped with salesperson, customer, total and status; for a Vendor it shows its purchase orders (purchasing area); for the trading company itself it shows no orders. | `query:qryCustomerOrderList` | query qryCustomerOrderList<br>query qryShipperOrderList<br>form sfrmCompanyDetail_CustomerOrders<br>form sfrmCompanyDetail_ShipperOrders | Orders, Companies, Employees, OrderStatus | high | equivalence |  |
| R-orders-029 | Orders are opened from the order list, from a company's order lists and from an employee's recent orders, and a new order is started from the order list; each opens the order screen for that order (or a blank new order), several orders can be open side by side, and when an order screen closes the open list screens are refreshed. Double-clicking a line's product opens that product's screen. | `form:frmOrderList.OrderID.Click` | procedure modOrders.OpenOrderDetailsForm<br>procedure modOrders.CloseOrderDetailsForm<br>procedure modOrders.CloseAllOrderDetailsForms<br>procedure modForms.RequeryListForms<br>procedure Form_frmOrderDetails.Form_Load<br>procedure Form_frmOrderDetails.Form_Close<br>procedure Form_frmOrderDetails.cmdAddOrder_Click<br>procedure Form_frmOrderList.OrderID_Click<br>procedure Form_frmOrderList.cmdAddOrder_Click<br>procedure Form_sfrmCompanyDetail_CustomerOrders.Detail_DblClick<br>procedure Form_sfrmCompanyDetail_CustomerOrders.OpenForm_frmOrderDetails<br>procedure Form_sfrmCompanyDetail_ShipperOrders.Detail_DblClick<br>procedure Form_sfrmCompanyDetail_ShipperOrders.OpenForm_frmOrderDetails<br>procedure Form_sfrmOrders_MostRecent_ByEmployee.OrderID_Click<br>procedure Form_sfrmOrderLineItems.ProductName_DblClick | Orders | high | e2e |  |
| R-orders-030 | An order moves only forward through New, Invoiced, Shipped, Paid and Closed, one step at a time and only through its actions (create invoice, ship, receive payment, close); the next available action is highlighted on the order screen and actions offered out of turn are refused with a message. | `form:frmOrderDetails.Current` | procedure Form_frmOrderDetails.cmdCreateInvoice_Click<br>procedure Form_frmOrderDetails.cmdShipOrder_Click<br>procedure Form_frmOrderDetails.cmdReceivePayment_Click<br>procedure Form_frmOrderDetails.cmdCloseOrder_Click<br>procedure Form_frmOrderDetails.SetFormStatus<br>form frmOrderDetails<br>report rptInvoice | Orders, OrderDetails, OrderStatus | high | e2e |  |
| R-orders-031 | Every table with audit columns records who created a row and when, and who last changed it and when: inserting sets created-by, created-on, modified-by and modified-on; updating sets modified-by and modified-on and keeps the original created-by and created-on even if an update tries to change or blank them. The name recorded is the signed-in employee's full name (first then last), or the operating-system login when nobody is signed in. | `datamacro:Orders.BeforeChange` | data_macro Companies.BeforeChange<br>data_macro CompanyTypes.BeforeChange<br>data_macro Contacts.BeforeChange<br>data_macro EmployeePrivileges.BeforeChange<br>data_macro Employees.BeforeChange<br>data_macro OrderDetailStatus.BeforeChange<br>data_macro OrderDetails.BeforeChange<br>data_macro OrderStatus.BeforeChange<br>data_macro Orders.BeforeChange<br>data_macro Privileges.BeforeChange<br>data_macro Strings.BeforeChange<br>data_macro TaxStatus.BeforeChange<br>data_macro Titles.BeforeChange<br>procedure modTableDataMacros.GetAuditFieldsUserName | Companies, CompanyTypes, Contacts, EmployeePrivileges, Employees, OrderDetailStatus, OrderDetails, OrderStatus, Orders, Privileges, Strings, TaxStatus, Titles | high | rule |  |
| R-orders-032 | The order, company and employee screens show a one-line history of the record: when and by whom it was created and when and by whom it was last modified, leaving out the parts that are blank. | `form:frmOrderDetails.Current` | procedure modGlobal.RecordModifiedString<br>form frmCompanyDetail<br>form frmEmployeeList | Orders, Companies, Employees | high | rule |  |
| R-orders-033 | A company cannot be deleted while it has orders as customer, orders as shipper or purchase orders as vendor; the user is told how many of each. Otherwise the user confirms (the message says how many contacts and vendor-product links will go too) and the company is deleted together with its contacts and its vendor-product links. | `form:frmCompanyDetail.Delete` | procedure Form_frmCompanyDetail.Form_Delete<br>procedure Form_frmCompanyDetail.CompanyIsActive<br>procedure Form_frmCompanyDetail.CompanyCantBeDeleted<br>procedure Form_frmCompanyDetail.CompanyConfirmDelete<br>procedure Form_frmCompanyDetail.cmdDeleteCompany_Click<br>procedure Form_frmCompanyDetail.Form_BeforeDelConfirm<br>procedure Form_frmCompanyDetail.Form_AfterDelConfirm | Companies, Orders, PurchaseOrders, Contacts, ProductVendors | high | rule | Q-orders-007 |
| R-orders-034 | A company's type cannot be changed while it has orders as customer, orders as shipper, purchase orders as vendor or vendor-product links; the change is undone and the user is told why. | `form:frmCompanyDetail.cboCompanyTypeID.BeforeUpdate` | procedure Form_frmCompanyDetail.cboCompanyTypeID_BeforeUpdate<br>procedure Form_frmCompanyDetail.CompanyIsActive | Companies, Orders, PurchaseOrders, ProductVendors | high | rule |  |
| R-orders-035 | The company screen is titled with the company type and shows the related list that fits the type (customer orders, shipped orders, or purchase orders), switching as soon as the type changes. | `form:frmCompanyDetail.Current` | procedure Form_frmCompanyDetail.ManageFormOptions<br>procedure Form_frmCompanyDetail.Form_Current<br>procedure Form_frmCompanyDetail.cboCompanyTypeID_AfterUpdate | Companies, CompanyTypes | high | rule |  |
| R-orders-036 | Saving changes on the company screen asks the user to confirm; answering no discards the unsaved changes. | `form:frmCompanyDetail.BeforeUpdate` | procedure Form_frmCompanyDetail.Form_BeforeUpdate | Companies | medium | rule | Q-orders-006 |
| R-orders-037 | The company list is read-only and can be filtered to Customers, Shippers, Vendors or all companies (the heading follows the filter). Opening a company or adding one from the list opens the company screen restricted to the same filter, with a new company defaulting to the filtered type; only one company screen can be open at a time. | `form:frmCompanyList.fraFilter.AfterUpdate` | form frmCompanyList<br>procedure Form_frmCompanyList.fraFilter_AfterUpdate<br>procedure Form_frmCompanyList.Form_Open<br>procedure Form_frmCompanyList.Open_frmCompanyDetail<br>procedure Form_frmCompanyList.cmdAddNew_Click<br>procedure Form_frmCompanyList.txtCompanyID_Click<br>procedure Form_frmCompanyDetail.Form_Load | Companies, CompanyTypes | medium | rule |  |
| R-orders-038 | Typing a customer name that does not exist yet in the order's customer field opens the company screen on a new company with that name filled in. | `form:frmCompanyDetail.Load` | procedure Form_frmCompanyDetail.Form_Load | Companies | medium | rule |  |
| R-orders-039 | Company lists show companies sorted by name with a one-line business address built from street, city, state and zip, plus the company type and standard tax status names; contacts are sorted by last then first name. | `query:qryCompanyList` | query qryCompanies<br>query qryCompanyList<br>query qryContacts | Companies, CompanyTypes, TaxStatus, Contacts | high | equivalence |  |
| R-orders-040 | An employee cannot be deleted while they have orders, have submitted purchase orders, supervise other employees or hold privileges; the user is told every reason. Otherwise the user confirms the delete by the employee's name. | `form:frmEmployeeList.Delete` | procedure Form_frmEmployeeList.EmployeeCanBeDeleted<br>procedure Form_frmEmployeeList.Form_Delete<br>procedure Form_frmEmployeeList.Form_BeforeDelConfirm | Employees, Orders, PurchaseOrders, EmployeePrivileges | high | rule |  |
| R-orders-041 | An employee cannot be their own supervisor: the supervisor list leaves out the employee being edited. Typing a supervisor who is not an employee offers to start a new employee record. | `form:frmEmployeeList.cboSupervisorID.Enter` | query qryEmployeeSupervisor<br>procedure Form_frmEmployeeList.cboSupervisorID_Enter<br>procedure Form_frmEmployeeList.cboSupervisorID_NotInList<br>procedure Form_frmEmployeeList.Form_Current | Employees | high | rule |  |
| R-orders-042 | After a new employee is saved, the privilege assignment screen opens for that employee so privileges can be granted straight away. | `form:frmEmployeeList.AfterInsert` | procedure Form_frmEmployeeList.Form_AfterInsert<br>procedure Form_sfrmEmployee_Privileges.Form_Open | Employees, EmployeePrivileges | medium | rule |  |
| R-orders-043 | An employee's full name is shown as first name then last name in choice lists (sorted that way) and as last name, first name for the employee list (sorted that way). | `query:qryEmployees` | query qryEmployees<br>query qrycboEmployees | Employees | high | equivalence |  |
| R-orders-044 | An employee's courtesy title must be one of the titles in the titles list; a title that is not in the list can be added from the employee screen through a small title-entry screen pre-filled with the typed value. | `form:frmEmployeeTitles.Open` | query qryTitle<br>procedure Form_frmEmployeeTitles.Form_Open<br>table Employees | Employees, Titles | medium | rule |  |
| R-orders-045 | Phone numbers of companies, contacts and employees are entered as a ten-digit number shown as 3-3-4 digits, optionally followed by an extension of up to eight characters. | `form:frmCompanyDetail.BeforeUpdate` | table Companies<br>table Contacts<br>table Employees | Companies, Contacts, Employees | medium | rule | Q-orders-010 |
| R-orders-046 | Names are unique: a company name once per company type, a contact's first and last name once per company, an employee's first and last name once (a duplicate is refused with a message), an operating-system login on at most one employee, and status, type, tax status, privilege and title names once each. | `form:frmCompanyDetail.BeforeUpdate` | table Companies<br>table Contacts<br>table Employees<br>table OrderStatus<br>table OrderDetailStatus<br>table CompanyTypes<br>table TaxStatus<br>table Privileges<br>table Titles | Companies, Contacts, Employees, OrderStatus, OrderDetailStatus, CompanyTypes, TaxStatus, Privileges, Titles | high | rule |  |
| R-orders-047 | Order statuses, order line statuses, tax statuses and company types are fixed code lists that the logic depends on by identity (order: New, Invoiced, Shipped, Paid, Closed; line: New, Allocated, No Stock, On Order, Invoiced, Shipped; tax: Tax Exempt, Taxable; company: Customer, Shipper, Vendor and the trading company itself). Status choice lists are sorted by their sort order, company types by name, tax statuses by code and states by state name. | `query:qrycboOrderStatus` | query qrycboOrderStatus<br>query qrycboOrderDetailStatus<br>query qrycboTaxStatus<br>query qrycboCompanyType<br>query qrycboStates<br>table OrderStatus<br>table OrderDetailStatus<br>table TaxStatus<br>table CompanyTypes<br>table States | OrderStatus, OrderDetailStatus, TaxStatus, CompanyTypes, States | high | equivalence |  |
| R-orders-048 | A new company's standard tax status defaults to Tax Exempt until the user picks another. | `form:frmCompanyDetail.BeforeUpdate` | table Companies | Companies, TaxStatus | medium | rule | Q-orders-011 |
| R-orders-049 | At start-up (the auto-run macro, when the database is trusted) the start-up routine runs: on the very first run only, guarded by the first-run flag in system settings, it moves every date in every table forward by the number of days between the latest order date and today (never backwards) so the sample data looks current, then sets the flag so this never runs again; it then shows the welcome screen when that setting is on, asks the user to sign in and opens the order list. | `schedule:startup` | macro AutoExec<br>procedure modStartup.Startup<br>procedure modGlobal.OneTimeProcessing<br>procedure modOrders.SetDatesToCurrent<br>procedure modStartup.SaveSystemSetting | SystemSettings, Orders | high | rule | Q-orders-005 |
| R-orders-050 | After the user signs in, the order list is the first screen shown. | `form:frmLogin.cmdLogin.Click` | form frmOrderList<br>procedure modStartup.Startup | Orders | high | e2e |  |

## Keep and drop

### Keep (202)

| Type | Name | Component | Note |
|---|---|---|---|
| data_macro | Companies.BeforeChange | foundation:audit-fields |  |
| data_macro | CompanyTypes.BeforeChange | foundation:audit-fields |  |
| data_macro | Contacts.BeforeChange | foundation:audit-fields |  |
| data_macro | EmployeePrivileges.BeforeChange | foundation:audit-fields |  |
| data_macro | Employees.BeforeChange | foundation:audit-fields |  |
| data_macro | OrderDetailStatus.BeforeChange | foundation:audit-fields |  |
| data_macro | OrderDetails.BeforeChange | foundation:audit-fields |  |
| data_macro | OrderStatus.BeforeChange | foundation:audit-fields |  |
| data_macro | Orders.BeforeChange | foundation:audit-fields |  |
| data_macro | Privileges.BeforeChange | foundation:audit-fields |  |
| data_macro | Strings.BeforeChange | foundation:audit-fields |  |
| data_macro | TaxStatus.BeforeChange | foundation:audit-fields |  |
| data_macro | Titles.BeforeChange | foundation:audit-fields |  |
| form | frmCompanyDetail | orders.views |  |
| form | frmCompanyList | orders.views |  |
| form | frmCredentials | foundation:sign-in | first-run self-registration of an unknown Windows user as an employee; replaced by the foundation's local sign-in and user admin (S4) |
| form | frmEmployeeList | orders.views |  |
| form | frmEmployeeTitles | orders.views | small entry screen that adds one title to the titles list; covered by the title rule's procedure, no rule of its own |
| form | frmLogin | foundation:sign-in | Windows-user login picker; replaced by the foundation's local sign-in (S4), so it holds no area rule |
| form | frmOrderDetails | orders.views |  |
| form | frmOrderList | orders.views |  |
| form | sfrmCompanyDetail_Contacts | orders.views | contacts grid of the company screen; plain data entry under the shared required-field rule, no rule of its own |
| form | sfrmCompanyDetail_CustomerOrders | orders.views |  |
| form | sfrmCompanyDetail_ShipperOrders | orders.views |  |
| form | sfrmEmployee_Privileges | foundation:roles | grants privileges to employees; becomes role assignment in the foundation (S4) |
| form | sfrmOrderLineItems | orders.views |  |
| form | sfrmOrders_MostRecent_ByEmployee | orders.views |  |
| macro | AutoExec | orders.jobs |  |
| procedure | Form_frmCompanyDetail.CompanyCantBeDeleted | orders.services |  |
| procedure | Form_frmCompanyDetail.CompanyConfirmDelete | orders.services |  |
| procedure | Form_frmCompanyDetail.CompanyIsActive | orders.services |  |
| procedure | Form_frmCompanyDetail.Form_AfterDelConfirm | orders.views |  |
| procedure | Form_frmCompanyDetail.Form_AfterInsert | orders.views | refreshes the company list after a new company is saved; screen refresh only, no rule |
| procedure | Form_frmCompanyDetail.Form_AfterUpdate | orders.views |  |
| procedure | Form_frmCompanyDetail.Form_BeforeDelConfirm | orders.views |  |
| procedure | Form_frmCompanyDetail.Form_BeforeUpdate | orders.views |  |
| procedure | Form_frmCompanyDetail.Form_Current | orders.views |  |
| procedure | Form_frmCompanyDetail.Form_Delete | orders.services |  |
| procedure | Form_frmCompanyDetail.Form_Load | orders.views |  |
| procedure | Form_frmCompanyDetail.ManageFormOptions | orders.views |  |
| procedure | Form_frmCompanyDetail.cboCompanyTypeID_AfterUpdate | orders.views |  |
| procedure | Form_frmCompanyDetail.cboCompanyTypeID_BeforeUpdate | orders.services |  |
| procedure | Form_frmCompanyDetail.cmdAdd_Click | orders.views | starts a new company record (tells the user when already on one); plain add action, no rule |
| procedure | Form_frmCompanyDetail.cmdCancel_Click | orders.views | discards unsaved edits and returns to the company the user came from, or closes; plain cancel action, no rule |
| procedure | Form_frmCompanyDetail.cmdDeleteCompany_Click | orders.views |  |
| procedure | Form_frmCompanyDetail.cmdSave_Click | orders.views |  |
| procedure | Form_frmCompanyDetail.txtWebsite_DblClick | orders.views | opens the company's website; becomes an ordinary link, no rule |
| procedure | Form_frmCompanyList.Form_Open | orders.views |  |
| procedure | Form_frmCompanyList.Open_frmCompanyDetail | orders.views |  |
| procedure | Form_frmCompanyList.cmdAddNew_Click | orders.views |  |
| procedure | Form_frmCompanyList.fraFilter_AfterUpdate | orders.views |  |
| procedure | Form_frmCompanyList.txtCompanyID_Click | orders.views |  |
| procedure | Form_frmCredentials.Form_BeforeUpdate | foundation:sign-in | part of the first-run self-registration of a Windows user; replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmCredentials.Form_Load | foundation:sign-in | part of the first-run self-registration of a Windows user; replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmCredentials.UserID | foundation:sign-in | part of the first-run self-registration of a Windows user; replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmCredentials.cmdAddMe_Click | foundation:sign-in | part of the first-run self-registration of a Windows user; replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmCredentials.cmdExit_Click | foundation:sign-in | part of the first-run self-registration of a Windows user; replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmEmployeeList.EmployeeCanBeDeleted | orders.services |  |
| procedure | Form_frmEmployeeList.Form_AfterDelConfirm | orders.views | shows or hides the new-employee button after a delete; screen state only, no rule |
| procedure | Form_frmEmployeeList.Form_AfterInsert | orders.views |  |
| procedure | Form_frmEmployeeList.Form_AfterUpdate | orders.views |  |
| procedure | Form_frmEmployeeList.Form_BeforeDelConfirm | orders.views |  |
| procedure | Form_frmEmployeeList.Form_BeforeUpdate | orders.views |  |
| procedure | Form_frmEmployeeList.Form_Current | orders.views |  |
| procedure | Form_frmEmployeeList.Form_Delete | orders.services |  |
| procedure | Form_frmEmployeeList.RequeryEmployeeList | orders.views | reloads the list and stays on the same employee after a save; screen refresh only, no rule |
| procedure | Form_frmEmployeeList.cboSupervisorID_Enter | orders.views |  |
| procedure | Form_frmEmployeeList.cboSupervisorID_NotInList | orders.views |  |
| procedure | Form_frmEmployeeList.cmdEmailEmployee_Click | orders.views | starts an e-mail to the employee signed with the sender's name; becomes a mail link, no rule |
| procedure | Form_frmEmployeeList.cmdNewEmployee_Click | orders.views | starts a new employee record; plain add action, no rule |
| procedure | Form_frmEmployeeTitles.Form_Open | orders.views |  |
| procedure | Form_frmLogin.AutoLogin_chk_AfterUpdate | foundation:sign-in | part of the Windows-user login picker (pick an employee, optional auto-login, quit when closed without signing in); replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmLogin.Form_Load | foundation:sign-in | part of the Windows-user login picker (pick an employee, optional auto-login, quit when closed without signing in); replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmLogin.Form_Unload | foundation:sign-in | part of the Windows-user login picker (pick an employee, optional auto-login, quit when closed without signing in); replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmLogin.UserID | foundation:sign-in | part of the Windows-user login picker (pick an employee, optional auto-login, quit when closed without signing in); replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmLogin.cmdLogin_Click | foundation:sign-in | part of the Windows-user login picker (pick an employee, optional auto-login, quit when closed without signing in); replaced by the foundation's local sign-in, no area rule |
| procedure | Form_frmOrderDetails.AllInvoiceLineItemsHaveStatus | orders.services |  |
| procedure | Form_frmOrderDetails.CustomerID_AfterUpdate | orders.services |  |
| procedure | Form_frmOrderDetails.Form_AfterUpdate | orders.views |  |
| procedure | Form_frmOrderDetails.Form_BeforeDelConfirm | orders.views |  |
| procedure | Form_frmOrderDetails.Form_BeforeInsert | orders.services |  |
| procedure | Form_frmOrderDetails.Form_BeforeUpdate | orders.views |  |
| procedure | Form_frmOrderDetails.Form_Close | orders.views |  |
| procedure | Form_frmOrderDetails.Form_Current | orders.views |  |
| procedure | Form_frmOrderDetails.Form_Delete | orders.services |  |
| procedure | Form_frmOrderDetails.Form_Load | orders.views |  |
| procedure | Form_frmOrderDetails.LockControls | orders.views |  |
| procedure | Form_frmOrderDetails.PaidFieldsFilledOut | orders.services |  |
| procedure | Form_frmOrderDetails.SetFormStatus | orders.views |  |
| procedure | Form_frmOrderDetails.SetLineItemsStatus | orders.services |  |
| procedure | Form_frmOrderDetails.ShippingFeeFilledOut | orders.services |  |
| procedure | Form_frmOrderDetails.ShippingFieldsFilledOut | orders.services |  |
| procedure | Form_frmOrderDetails.cmdAddOrder_Click | orders.views |  |
| procedure | Form_frmOrderDetails.cmdCloseOrder_Click | orders.services |  |
| procedure | Form_frmOrderDetails.cmdCreateInvoice_Click | orders.services |  |
| procedure | Form_frmOrderDetails.cmdDeleteOrder_Click | orders.services |  |
| procedure | Form_frmOrderDetails.cmdPrintInvoice_Click | orders.views |  |
| procedure | Form_frmOrderDetails.cmdReceivePayment_Click | orders.services |  |
| procedure | Form_frmOrderDetails.cmdShipOrder_Click | orders.services |  |
| procedure | Form_frmOrderDetails.sfrmOrderLineItems_Enter | orders.views |  |
| procedure | Form_frmOrderDetails.sfrmOrderLineItems_Exit | orders.views |  |
| procedure | Form_frmOrderList.Form_Open | orders.views |  |
| procedure | Form_frmOrderList.OrderID_Click | orders.views |  |
| procedure | Form_frmOrderList.cmdAddOrder_Click | orders.views |  |
| procedure | Form_frmOrderList.fraFilter_AfterUpdate | orders.views |  |
| procedure | Form_sfrmCompanyDetail_Contacts.Form_AfterUpdate | orders.views |  |
| procedure | Form_sfrmCompanyDetail_Contacts.Form_BeforeUpdate | orders.views |  |
| procedure | Form_sfrmCompanyDetail_CustomerOrders.Detail_DblClick | orders.views |  |
| procedure | Form_sfrmCompanyDetail_CustomerOrders.OpenForm_frmOrderDetails | orders.views |  |
| procedure | Form_sfrmCompanyDetail_ShipperOrders.Detail_DblClick | orders.views |  |
| procedure | Form_sfrmCompanyDetail_ShipperOrders.OpenForm_frmOrderDetails | orders.views |  |
| procedure | Form_sfrmEmployee_Privileges.Form_AfterDelConfirm | foundation:roles | refreshes the admin screen's privilege count when shown inside it; screen plumbing of the privilege grid, no rule |
| procedure | Form_sfrmEmployee_Privileges.Form_AfterInsert | foundation:roles | refreshes the admin screen's privilege count when shown inside it; screen plumbing of the privilege grid, no rule |
| procedure | Form_sfrmEmployee_Privileges.Form_Open | foundation:roles |  |
| procedure | Form_sfrmEmployee_Privileges.frmLoadedAsSubform | foundation:roles | refreshes the admin screen's privilege count when shown inside it; screen plumbing of the privilege grid, no rule |
| procedure | Form_sfrmOrderLineItems.Form_AfterDelConfirm | orders.services |  |
| procedure | Form_sfrmOrderLineItems.Form_AfterUpdate | orders.services |  |
| procedure | Form_sfrmOrderLineItems.Form_BeforeDelConfirm | orders.views |  |
| procedure | Form_sfrmOrderLineItems.Form_BeforeInsert | orders.services |  |
| procedure | Form_sfrmOrderLineItems.Form_BeforeUpdate | orders.services |  |
| procedure | Form_sfrmOrderLineItems.Form_Current | orders.views |  |
| procedure | Form_sfrmOrderLineItems.Form_Delete | orders.views |  |
| procedure | Form_sfrmOrderLineItems.Form_Error | orders.views |  |
| procedure | Form_sfrmOrderLineItems.ProductID_AfterUpdate | orders.services |  |
| procedure | Form_sfrmOrderLineItems.ProductID_GotFocus | orders.views |  |
| procedure | Form_sfrmOrderLineItems.ProductName_DblClick | orders.views |  |
| procedure | Form_sfrmOrderLineItems.ReallocateInventory | orders.services |  |
| procedure | Form_sfrmOrderLineItems.SetOrderDetailStatus | orders.services |  |
| procedure | Form_sfrmOrderLineItems.cboProductCategories_AfterUpdate | orders.views |  |
| procedure | Form_sfrmOrders_MostRecent_ByEmployee.OrderID_Click | orders.views |  |
| procedure | Report_rptInvoice.Report_NoData | orders.reports |  |
| procedure | modCompanies.GetTaxStatusID | orders.services |  |
| procedure | modForms.RequeryListForms | orders.views |  |
| procedure | modGlobal.GetNorthwindAddress | orders.reports |  |
| procedure | modGlobal.GetWindowsUserName | foundation:sign-in | reads the operating-system login used to find the employee and as the audit name when nobody is signed in; replaced by the signed-in user |
| procedure | modGlobal.Get_EmployeeFNLN | foundation:sign-in | full name of the signed-in employee for the window title; the foundation shows the signed-in user |
| procedure | modGlobal.Get_UserID | foundation:sign-in |  |
| procedure | modGlobal.Get_UserID_ForWindowsUser | foundation:sign-in | maps the Windows login to an employee for auto-login; replaced by local sign-in |
| procedure | modGlobal.InitializeUser | foundation:sign-in | start-up sign-in flow (register unknown Windows users, auto-login or show the login picker); replaced by local sign-in |
| procedure | modGlobal.OneTimeProcessing | orders.jobs |  |
| procedure | modGlobal.RecordModifiedString | orders.views |  |
| procedure | modOrders.CloseAllOrderDetailsForms | orders.views |  |
| procedure | modOrders.CloseOrderDetailsForm | orders.views |  |
| procedure | modOrders.OpenOrderDetailsForm | orders.views |  |
| procedure | modOrders.SetDatesToCurrent | orders.jobs |  |
| procedure | modSecurity.HasPrivilege | foundation:roles | checks whether the signed-in employee holds a privilege; the only privilege (approve purchase orders) is used by purchasing and becomes a role check in the foundation |
| procedure | modStartup.GetSystemSetting | orders.services |  |
| procedure | modStartup.GetUserSetting | foundation:sign-in | reads the auto-login preference; replaced by the foundation's sign-in session |
| procedure | modStartup.SaveSystemSetting | orders.jobs |  |
| procedure | modStartup.SaveUserSetting | foundation:sign-in | stores the auto-login preference; replaced by the foundation's sign-in session |
| procedure | modStartup.Startup | orders.jobs |  |
| procedure | modTableDataMacros.GetAuditFieldsUserName | foundation:audit-fields |  |
| procedure | modValidation.HighlightControl | orders.views |  |
| procedure | modValidation.HighlightInvalidControls | orders.views |  |
| procedure | modValidation.IsBoundToRequiredField | orders.views |  |
| procedure | modValidation.IsValidForm | orders.views |  |
| procedure | modValidation.ValidateForm | orders.views |  |
| procedure | modValidation.ValidateForm_RemoveHighlights | orders.views |  |
| query | qryCompanies | orders.saved_queries |  |
| query | qryCompanyList | orders.saved_queries |  |
| query | qryContacts | orders.saved_queries |  |
| query | qryCustomerOrderList | orders.saved_queries |  |
| query | qryCustomers | orders.saved_queries |  |
| query | qryEmployeeLogin | foundation:sign-in | employee list behind the first-run registration screen; replaced by the foundation's user admin |
| query | qryEmployeePrivileges | foundation:roles | privilege grants per employee; becomes role membership in the foundation |
| query | qryEmployeeSupervisor | orders.saved_queries |  |
| query | qryEmployees | orders.saved_queries |  |
| query | qryInvoice | orders.saved_queries |  |
| query | qryOrder | orders.saved_queries | record source of the order screen (the order with its status name); its unit proves it, no rule |
| query | qryOrderLineItems | orders.saved_queries | record source of the order lines grid (lines with product and category names); its unit proves it, no rule |
| query | qryOrderList | orders.saved_queries |  |
| query | qryOrderList_DetailStatus | orders.saved_queries |  |
| query | qryOrderList_DetailStatus_Lowest | orders.saved_queries |  |
| query | qryOrderTotal | orders.saved_queries |  |
| query | qryOrders_MostRecent | orders.saved_queries |  |
| query | qryPrivileges | foundation:roles | privilege names sorted by name; becomes the foundation's role list |
| query | qryShipperOrderList | orders.saved_queries |  |
| query | qryShippers | orders.saved_queries |  |
| query | qryTitle | orders.saved_queries |  |
| query | qrycboCompanyType | orders.saved_queries |  |
| query | qrycboCustomers | orders.saved_queries |  |
| query | qrycboEmployees | orders.saved_queries |  |
| query | qrycboOrderDetailStatus | orders.saved_queries |  |
| query | qrycboOrderStatus | orders.saved_queries |  |
| query | qrycboShippers | orders.saved_queries |  |
| query | qrycboStates | orders.saved_queries |  |
| query | qrycboTaxStatus | orders.saved_queries |  |
| report | rptInvoice | orders.reports |  |
| table | Companies | legacy.models |  |
| table | CompanyTypes | legacy.models |  |
| table | Contacts | legacy.models |  |
| table | EmployeePrivileges | foundation:roles |  |
| table | Employees | legacy.models |  |
| table | OrderDetailStatus | legacy.models |  |
| table | OrderDetails | legacy.models |  |
| table | OrderStatus | legacy.models |  |
| table | Orders | legacy.models |  |
| table | Privileges | foundation:roles |  |
| table | States | legacy.models |  |
| table | SystemSettings | legacy.models |  |
| table | TaxStatus | legacy.models |  |
| table | Titles | legacy.models |  |

### Drop (121)

| Type | Name | Reason |
|---|---|---|
| form | _Design | layout sample of the template with no record source and no behaviour |
| form | frmAbout | about box of the Access template |
| form | frmAdmin | launcher for the template's maintenance tools (demo data, messages, settings); privileges go to foundation roles, settings to the Django admin, product categories to the inventory area |
| form | frmGenericDialog | generic message box used by other screens; web messages replace it |
| form | frmNorthwindFeatures | help catalogue of the Access template's features |
| form | frmStartup | shown only when Access has not trusted the database; no web equivalent |
| form | frmWelcome | welcome screen of the Access template |
| form | sfrmAdmin_DeleteTestData | admin tool that wipes the template's sample data |
| form | sfrmAdmin_InternetOrders | admin tool that generates random sample orders |
| form | sfrmAdmin_ResetDates | admin tool that shifts sample dates on demand; the first-run shift is kept by the start-up rule |
| form | sfrmAdmin_Strings | editor for the Access message texts, which are dropped |
| form | sfrmAdmin_SystemSettings | settings grid of the admin screen; the settings table is kept and edited through the Django admin |
| procedure | Form_frmAbout.cmdClose_Click | part of the dropped about box |
| procedure | Form_frmAdmin.Form_Open | part of the dropped admin launcher |
| procedure | Form_frmAdmin.UpdateSubLabels | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdDeleteTestData_Click | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdInternetOrders_Click | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdPrivileges_Click | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdProductCategories_Click | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdRelationshipsDiagram_Click | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdResetDates_Click | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdStrings_Click | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdSystemSettings_Click | part of the dropped admin launcher |
| procedure | Form_frmCompanyDetail.Form_Open | clears a filter left by an earlier Access session; the web screen has no persisted filter |
| procedure | Form_frmCompanyDetail.cmdClickToMap_Click | opens the address in a retired consumer map site (see open question on dropped conveniences) |
| procedure | Form_frmCompanyDetail.cmdEmail_Click | e-mails the Access screen through the mail client (see open question on dropped conveniences) |
| procedure | Form_frmCompanyDetail.cmdShowFilter_Click | shows the raw filter expression in a dialog |
| procedure | Form_frmCompanyDetail.txtBusinessPhone_Click | places the cursor at the start of an empty masked field; Access input behaviour only |
| procedure | Form_frmCompanyList.cmdLabelWizard_Click | starts the Access mailing-label wizard (see open question on dropped conveniences) |
| procedure | Form_frmCompanyList.cmdShowFilter_Click | shows the raw filter expression in a dialog |
| procedure | Form_frmCompanyList.cmdShowHideFields_Click | opens the Access unhide-columns dialog |
| procedure | Form_frmGenericDialog.Form_Load | part of the dropped generic message box |
| procedure | Form_frmGenericDialog.cmdCancelClose_Click | part of the dropped generic message box |
| procedure | Form_frmGenericDialog.cmdOK_Click | part of the dropped generic message box |
| procedure | Form_frmNorthwindFeatures.txtHelpKeywords_Click | part of the dropped feature help catalogue |
| procedure | Form_frmOrderDetails.Form_AfterInsert | only adds the new order to the dropped recently-used list |
| procedure | Form_frmOrderDetails.Form_Open | empty handler (work is done on load) |
| procedure | Form_frmOrderList.cmdShowFilter_Click | shows the raw filter expression in a dialog; the web list shows its filter controls |
| procedure | Form_frmWelcome.Form_Close | part of the dropped welcome screen |
| procedure | Form_frmWelcome.Form_Open | part of the dropped welcome screen |
| procedure | Form_frmWelcome.cmdGetStarted_Click | part of the dropped welcome screen |
| procedure | Form_sfrmAdmin_DeleteTestData.cmdRemoveTestData_Click | wipes the template's sample data; demo tool |
| procedure | Form_sfrmAdmin_InternetOrders.cmdCreate_Click | generates random sample orders; demo tool |
| procedure | Form_sfrmAdmin_InternetOrders.txtCount_BeforeUpdate | input check of the dropped sample-order generator |
| procedure | Form_sfrmAdmin_ResetDates.cmdResetDates_Click | on-demand sample date shift; demo tool |
| procedure | Form_sfrmAdmin_Strings.Form_AfterDelConfirm | empty handler of the dropped message-text editor |
| procedure | Form_sfrmAdmin_Strings.Form_AfterInsert | empty handler of the dropped message-text editor |
| procedure | Form_sfrmAdmin_SystemSettings.Form_AfterDelConfirm | empty handler of the dropped settings grid |
| procedure | Form_sfrmAdmin_SystemSettings.Form_AfterInsert | empty handler of the dropped settings grid |
| procedure | Form_sfrmCompanyDetail_Contacts.txtPrimaryPhone_Click | places the cursor at the start of an empty masked field; Access input behaviour only |
| procedure | Form_sfrmCompanyDetail_Contacts.txtSecondaryPhone_Click | places the cursor at the start of an empty masked field; Access input behaviour only |
| procedure | Form_sfrmOrderLineItems.ProductCategoryName_GotFocus | moves keyboard focus between two grid columns; layout only |
| procedure | Form_sfrmOrderLineItems.ProductName_GotFocus | moves keyboard focus to the product list; layout only |
| procedure | Report_rptInvoice.Report_Activate | shows the report group on the Access ribbon |
| procedure | Report_rptInvoice.Report_Close | hides the report group on the Access ribbon |
| procedure | clsErrorHandler.Class_Initialize | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.ErrorHandlerExample | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.ErrorHandlerExample_EventProcedure | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.HandleError | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.LogErrorToFile | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | modCompanies.GetRandomCustomerID | random customer for the dropped sample-order generator |
| procedure | modDAO.GetRandomPkValue | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDAO.HasDataMacro | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDAO.HasField | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDAO.HasProperty | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDebug.DumpTempVars | developer debugging helper |
| procedure | modDebug.NotImplemented | developer debugging helper |
| procedure | modFiles.FileExists | file helper used only by the Access first run |
| procedure | modFiles.StringToFile | file helper used only by the Access first run |
| procedure | modForms.ControlCurrentView | Access view probe used to colour highlighted fields; the web forms mark errors themselves |
| procedure | modForms.ControlDefaultView | Access view probe used to colour highlighted fields; the web forms mark errors themselves |
| procedure | modForms.IsFormOpen | Access window probe; no business behaviour |
| procedure | modGlobal.AddToMRU | maintains the dropped recently-used list |
| procedure | modGlobal.RemoveFromMRU | maintains the dropped recently-used list |
| procedure | modGlobal.SetCtrlCurrencyFormat | re-applies Access currency formats for regional settings at first run |
| procedure | modGlobal.ToAccessDate | formats dates for Access SQL text |
| procedure | modGlobal.g_dbApp | returns the Access database handle |
| procedure | modMath.GetRandom | random numbers for the dropped sample-order generator |
| procedure | modMath.MaxValue | generic helper not used by any kept behaviour |
| procedure | modOrders.CreateRandomOrders | generates random sample orders for the dropped admin tool |
| procedure | modOrders.GetRandomProductID | random product for the dropped sample-order generator |
| procedure | modRibbonCallback.ActivateTab | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.RibbonFinish | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.Ribbon_RefreshMRU | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdAbout_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdAddOrder_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdAdmin_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdCustomers_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdEmployees_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdExitApplication_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdExportToExcel_OnAction | Access export of the current list to Excel (see open question on dropped conveniences) |
| procedure | modRibbonCallback.cmdFeatures_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdNorthwindDocumentation_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdOrders_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetItemCount | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetItemID | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetItemLabel | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetSelectedItemIndex | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_OnAction | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_OnChange | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ribbonLoaded | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modStartup.CloseAllForms | closes Access windows on exit |
| procedure | modStartup.CloseAllReports | closes Access windows on exit |
| procedure | modStartup.Finish | Access shutdown routine |
| procedure | modStartup.SetAppTitle | puts the app name, version and user in the Access title bar; the web layout shows the signed-in user |
| procedure | modStrings.GetString | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modStrings.StringFormat | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modStrings.StringFormatSQL | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modStrings.StringToDictionary | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modTableDataMacros.AddDataMacros | installs the audit data macros on Access first run; the audit rule is kept in the model layer |
| query | qryMRU | feeds the dropped recently-used ribbon list |
| query | qryOrders_MostRecent_Customer | unused: no form, report, query or code refers to it |
| query | qryOrders_MostRecent_Employee | unused: no form, report, query or code refers to it |
| query | qryOrders_MostRecent_ModifiedOn | unused: no form, report, query or code refers to it |
| query | qryStrings | feeds the dropped message-text editor |
| query | qrySystemSettings | feeds only the dropped admin sub-screens; settings are edited through the Django admin |
| table | MRU | recently-used list behind the Access ribbon; the web app's lists and browser history replace it |
| table | NorthwindFeatures | help catalogue of the Access template's own features; no business data |
| table | Strings | message texts for Access message boxes; the new app keeps its messages in its templates and forms |
| table | UserSettings | per-machine auto-login preference for the Windows user; local sign-in (foundation) replaces it |
| table | Welcome | welcome-screen text and the data-macro template used by the Access first run; no business data |

### Out of scope (0)

None.

## Code lists (lookups)

These code lists are behaviour: the logic refers to the codes by identity, so the synthetic data copies them from the design (code constants, value lists and query criteria) rather than inventing them. None of them needed codes from the client, so `values` is empty in the JSON; the codes below come from the design and are listed for sign-off.

| Table.column | Codes (from the design) | Rule |
|---|---|---|
| Orders.OrderStatusID | New, Invoiced, Shipped, Paid, Closed | R-orders-030 |
| OrderDetails.OrderDetailStatusID | New, Allocated, No Stock, On Order, Invoiced, Shipped | R-orders-009 |
| Orders.TaxStatusID | Tax Exempt, Taxable | R-orders-020 |
| Companies.StandardTaxStatusID | Tax Exempt, Taxable (default Tax Exempt) | R-orders-048 |
| Companies.CompanyTypeID | Customer, Shipper, Vendor, the trading company itself | R-orders-003 |
| Orders.PaymentMethod | the fixed list of payment methods offered by the order screen's value list | R-orders-017 |
| Employees.Title | the courtesy titles offered by the employee title value list and the titles table | R-orders-044 |
| SystemSettings.SettingID | default sales tax rate, last reset date, show welcome, vendor tax rate, first-run flag | R-orders-001 |

## Relations

| Table.foreign key | On delete | Rule |
|---|---|---|
| OrderDetails.OrderID | CASCADE | R-orders-011 |
| OrderDetails.OrderDetailStatusID | PROTECT | R-orders-047 |
| OrderDetails.ProductID | PROTECT | R-orders-008 |
| Orders.CustomerID | PROTECT | R-orders-033 |
| Orders.ShipperID | PROTECT | R-orders-033 |
| Orders.EmployeeID | PROTECT | R-orders-040 |
| Orders.OrderStatusID | PROTECT | R-orders-047 |
| Orders.TaxStatusID | PROTECT | R-orders-047 |
| Contacts.CompanyID | CASCADE | R-orders-033 |
| Companies.CompanyTypeID | PROTECT | R-orders-034 |
| Companies.StandardTaxStatusID | PROTECT | R-orders-047 |
| Companies.StateAbbrev | PROTECT | R-orders-047 |
| Employees.SupervisorID | PROTECT | R-orders-040 |
| Employees.Title | PROTECT | R-orders-044 |
| EmployeePrivileges.EmployeeID | PROTECT | R-orders-040 |
| EmployeePrivileges.PrivilegeID | PROTECT | R-orders-042 |

## Workflows

### order_to_ship: Order entry to invoice (printable PDF) to shipping

- Screens: frmOrderList, frmOrderDetails, sfrmOrderLineItems
- Reports: rptInvoice
- Rules proven end to end: R-orders-050, R-orders-029, R-orders-030
- Steps:
  1. sign in and land on the order list
  2. start a new order and choose the customer
  3. save the order header
  4. add order lines (each line is allocated or marked no stock)
  5. create the invoice and download it as a PDF
  6. enter shipped date, shipper and shipping fee and ship the order
  7. enter payment method and paid date and receive payment
  8. close the order

## Services

| Service | Inputs | Outputs | Errors |
|---|---|---|---|
| `create_invoice` | order id | order status Invoiced with invoice date; all lines Invoiced; invoice PDF | order not saved; order is not New; order has no lines; a line is not Allocated; shipping fee missing |
| `ship_order` | order id; shipped date; shipper id; shipping fee | order status Shipped; all lines Shipped | order not saved; order is not Invoiced; shipped date, shipper or shipping fee missing |
| `receive_payment` | order id; payment method; paid date | order status Paid | order not saved; order is not Shipped; payment method or paid date missing |
| `close_order` | order id | order status Closed | order not saved; order is not Paid |
| `delete_order` | order id | order and its lines deleted; stock re-allocated for the lines' products | order not saved; order is Shipped, Paid or Closed |
| `save_order_line` | order id; product id; quantity; discount; previous product id | line status Allocated or No Stock; unit price from the product; stock re-allocated for the old and new product | order not saved; order is not New; quantity not above zero; product already on the order; required field missing |
| `delete_order_line` | order line id | line deleted; stock re-allocated for its product | order is not New |
| `delete_company` | company id | company, its contacts and its vendor-product links deleted | company has orders as customer, orders as shipper or purchase orders |
| `change_company_type` | company id; company type id | company type changed | company has orders, shipments, purchase orders or vendor-product links |
| `delete_employee` | employee id | employee deleted | employee has orders; employee submitted purchase orders; employee supervises others; employee holds privileges |
| `first_run` | today's date | all dates shifted forward by the gap to the latest order date; first-run flag set | none |

## Open questions

- **Q-orders-001** (open): The printed invoice shows the date it is printed, not the stored invoice date, so a reprint carries a new date. Should the invoice show the stored invoice date instead? (Assumption until answered: keep the original behaviour.)
- **Q-orders-002** (open): The original enforces no rules on the invoice, shipped and paid dates (they can be any date, also before the order date). Should the new app require shipped date and paid date to be on or after the order date (and paid on or after shipped)? (Assumption: no extra date checks.)
- **Q-orders-003** (open): Tax is charged on the line subtotal only, never on the shipping fee, and a shipping fee of zero is accepted while a blank fee blocks invoicing. Is that correct for your business? (Assumption: keep as is.)
- **Q-orders-004** (open): The employee screen's recent orders list is built from the 20 most recent orders overall and then narrowed to the employee, so an employee may see fewer than 20 or none. Should it show the employee's own 20 most recent orders instead? (Assumption: the employee's own 20 most recent.)
- **Q-orders-005** (open): On the first start the original shifts every date in the database forward so the sample data looks current. Keep this as a one-off start-up command in the new app (useful for demo data), or drop it? (Assumption: keep as a one-off command guarded by the first-run flag.)
- **Q-orders-006** (open): Saving a company asks 'do you want to save your changes?' while other screens save without asking. Keep the confirmation for companies? (Assumption: keep.)
- **Q-orders-007** (open): Deleting a company that has no orders or purchase orders also deletes its contacts and vendor-product links after one confirmation. Is that cascade wanted? (Assumption: yes.)
- **Q-orders-008** (open): These Access conveniences are dropped and replaced by standard web features: the recently-used list on the ribbon, export of any list to Excel, the mailing-label wizard, the 'click to map' link, e-mailing the company screen, the show-filter and show/hide-columns buttons. Is any of them needed in the new app?
- **Q-orders-009** (open): Which order list filter should be selected when the list opens? The design does not record the default. (Assumption: Open orders.)
- **Q-orders-010** (open): Phone numbers are forced into a US ten-digit format with an optional extension. Keep the US format, or accept international numbers? (Assumption: keep the US format.)
- **Q-orders-011** (open): A new company is tax exempt by default. Should new customers default to Taxable instead? (Assumption: keep exempt.)
- **Q-orders-012** (open): An order can be invoiced only when every line is Allocated (no partial invoices or backorders). Is that still the rule? (Assumption: yes.)
