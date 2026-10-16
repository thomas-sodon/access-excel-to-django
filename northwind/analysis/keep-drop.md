_Generated from analysis/rules.json by `toolkit rules-render`. Do not edit by hand._

# Keep and drop list

Engagement `northwind-demo`, spec version 1.0.

## Keep

| type | name | area | target component |
|---|---|---|---|
| data_macro | ProductCategories.BeforeChange | inventory | foundation:audit-fields |
| data_macro | ProductVendors.BeforeChange | inventory | foundation:audit-fields |
| data_macro | Products.BeforeChange | inventory | foundation:audit-fields |
| data_macro | StockTake.BeforeChange | inventory | foundation:audit-fields |
| form | frmProductDetail | inventory | inventory.views |
| form | frmProductList | inventory | inventory.views |
| form | sfrmProductCategories | inventory | inventory.views |
| form | sfrmProductDetail_Orders | inventory | inventory.views |
| form | sfrmProductDetail_PurchaseOrders | inventory | inventory.views |
| form | sfrmProductDetail_StockTake | inventory | inventory.views |
| form | sfrmProductDetail_Vendors | inventory | inventory.views |
| procedure | Form_frmProductDetail.CalculateLevels | inventory | inventory.views |
| procedure | Form_frmProductDetail.ControlStates | inventory | inventory.views |
| procedure | Form_frmProductDetail.Form_BeforeUpdate | inventory | inventory.forms |
| procedure | Form_frmProductDetail.SetProductCode | inventory | inventory.models |
| procedure | Form_frmProductDetail.cboFindProduct_AfterUpdate | inventory | inventory.views |
| procedure | Form_frmProductDetail.cboProductCategoryID_AfterUpdate | inventory | inventory.models |
| procedure | Form_frmProductDetail.chkDiscontinued_AfterUpdate | inventory | inventory.views |
| procedure | Form_frmProductDetail.cmdAddProduct_Click | inventory | inventory.views |
| procedure | Form_frmProductDetail.cmdDeleteProduct_Click | inventory | inventory.services |
| procedure | Form_frmProductDetail.cmdReorderProduct_Click | inventory | inventory.services |
| procedure | Form_frmProductDetail.txtTargetLevel_AfterUpdate | inventory | inventory.views |
| procedure | Form_frmProductList.ProductID_Click | inventory | inventory.views |
| procedure | Form_frmProductList.cmdAddProduct_Click | inventory | inventory.views |
| procedure | Form_frmProductList.cmdExport_Click | inventory | inventory.views |
| procedure | Form_sfrmProductCategories.cmdAdd_Click | inventory | inventory.views |
| procedure | Form_sfrmProductCategories.cmdDelete_Click | inventory | inventory.services |
| procedure | Form_sfrmProductCategories.lstCategory_AfterUpdate | inventory | inventory.views |
| procedure | Form_sfrmProductCategories.txtProductCategoryCode_BeforeUpdate | inventory | inventory.forms |
| procedure | Form_sfrmProductDetail_Orders.txtOrderID_Click | inventory | inventory.views |
| procedure | Form_sfrmProductDetail_PurchaseOrders.txtPOID_Click | inventory | inventory.views |
| procedure | Form_sfrmProductDetail_StockTake.Form_AfterUpdate | inventory | inventory.services |
| procedure | Form_sfrmProductDetail_StockTake.Form_BeforeUpdate | inventory | inventory.forms |
| procedure | Form_sfrmProductDetail_StockTake.Form_Current | inventory | inventory.views |
| procedure | Form_sfrmProductDetail_StockTake.QuantityOnHand_AfterUpdate | inventory | inventory.services |
| procedure | Form_sfrmProductDetail_StockTake.QuantityOnHand_BeforeUpdate | inventory | inventory.forms |
| procedure | Form_sfrmProductDetail_Vendors.Form_BeforeUpdate | inventory | inventory.models |
| procedure | Form_sfrmProductDetail_Vendors.txtVendorID_Click | inventory | inventory.views |
| procedure | modInventory.AllocateInventory | inventory | inventory.services |
| procedure | modInventory.OrderQuantity_ByStatus | inventory | inventory.services |
| procedure | modInventory.ProductAllocated | inventory | inventory.services |
| procedure | modInventory.ProductAvailable | inventory | inventory.services |
| procedure | modInventory.ProductBought | inventory | inventory.services |
| procedure | modInventory.ProductLastStockTakeDate | inventory | inventory.services |
| procedure | modInventory.ProductLastStockTakeQuantity | inventory | inventory.services |
| procedure | modInventory.ProductNoStock | inventory | inventory.services |
| procedure | modInventory.ProductOnOrder | inventory | inventory.services |
| procedure | modInventory.ProductReorderQuantity | inventory | inventory.services |
| procedure | modInventory.ProductSold | inventory | inventory.services |
| procedure | modInventory.ProductToSell | inventory | inventory.services |
| procedure | modRibbonCallback.cmdProducts_OnAction | inventory | inventory.views |
| query | qryPOProducts_ByStatus | inventory | inventory.saved_queries |
| query | qryProductCategories | inventory | inventory.saved_queries |
| query | qryProductDetail | inventory | inventory.saved_queries |
| query | qryProductList | inventory | inventory.saved_queries |
| query | qryProductList_Export | inventory | inventory.saved_queries |
| query | qryProductOrders | inventory | inventory.saved_queries |
| query | qryProductPurchaseOrder | inventory | inventory.saved_queries |
| query | qryProductVendors | inventory | inventory.saved_queries |
| query | qryStockTake | inventory | inventory.saved_queries |
| query | qrycboProductCategories | inventory | inventory.saved_queries |
| query | qrycboProductCategory | inventory | inventory.saved_queries |
| query | qrycboProducts | inventory | inventory.saved_queries |
| query | qrycboProducts_All | inventory | inventory.saved_queries |
| table | ProductCategories | inventory | legacy.models |
| table | ProductVendors | inventory | legacy.models |
| table | Products | inventory | legacy.models |
| table | StockTake | inventory | legacy.models |
| data_macro | Companies.BeforeChange | orders | foundation:audit-fields |
| data_macro | CompanyTypes.BeforeChange | orders | foundation:audit-fields |
| data_macro | Contacts.BeforeChange | orders | foundation:audit-fields |
| data_macro | EmployeePrivileges.BeforeChange | orders | foundation:audit-fields |
| data_macro | Employees.BeforeChange | orders | foundation:audit-fields |
| data_macro | OrderDetailStatus.BeforeChange | orders | foundation:audit-fields |
| data_macro | OrderDetails.BeforeChange | orders | foundation:audit-fields |
| data_macro | OrderStatus.BeforeChange | orders | foundation:audit-fields |
| data_macro | Orders.BeforeChange | orders | foundation:audit-fields |
| data_macro | Privileges.BeforeChange | orders | foundation:audit-fields |
| data_macro | Strings.BeforeChange | orders | foundation:audit-fields |
| data_macro | TaxStatus.BeforeChange | orders | foundation:audit-fields |
| data_macro | Titles.BeforeChange | orders | foundation:audit-fields |
| form | frmCompanyDetail | orders | orders.views |
| form | frmCompanyList | orders | orders.views |
| form | frmCredentials | orders | foundation:sign-in |
| form | frmEmployeeList | orders | orders.views |
| form | frmEmployeeTitles | orders | orders.views |
| form | frmLogin | orders | foundation:sign-in |
| form | frmOrderDetails | orders | orders.views |
| form | frmOrderList | orders | orders.views |
| form | sfrmCompanyDetail_Contacts | orders | orders.views |
| form | sfrmCompanyDetail_CustomerOrders | orders | orders.views |
| form | sfrmCompanyDetail_ShipperOrders | orders | orders.views |
| form | sfrmEmployee_Privileges | orders | foundation:roles |
| form | sfrmOrderLineItems | orders | orders.views |
| form | sfrmOrders_MostRecent_ByEmployee | orders | orders.views |
| macro | AutoExec | orders | orders.jobs |
| procedure | Form_frmCompanyDetail.CompanyCantBeDeleted | orders | orders.services |
| procedure | Form_frmCompanyDetail.CompanyConfirmDelete | orders | orders.services |
| procedure | Form_frmCompanyDetail.CompanyIsActive | orders | orders.services |
| procedure | Form_frmCompanyDetail.Form_AfterDelConfirm | orders | orders.views |
| procedure | Form_frmCompanyDetail.Form_AfterInsert | orders | orders.views |
| procedure | Form_frmCompanyDetail.Form_AfterUpdate | orders | orders.views |
| procedure | Form_frmCompanyDetail.Form_BeforeDelConfirm | orders | orders.views |
| procedure | Form_frmCompanyDetail.Form_BeforeUpdate | orders | orders.views |
| procedure | Form_frmCompanyDetail.Form_Current | orders | orders.views |
| procedure | Form_frmCompanyDetail.Form_Delete | orders | orders.services |
| procedure | Form_frmCompanyDetail.Form_Load | orders | orders.views |
| procedure | Form_frmCompanyDetail.ManageFormOptions | orders | orders.views |
| procedure | Form_frmCompanyDetail.cboCompanyTypeID_AfterUpdate | orders | orders.views |
| procedure | Form_frmCompanyDetail.cboCompanyTypeID_BeforeUpdate | orders | orders.services |
| procedure | Form_frmCompanyDetail.cmdAdd_Click | orders | orders.views |
| procedure | Form_frmCompanyDetail.cmdCancel_Click | orders | orders.views |
| procedure | Form_frmCompanyDetail.cmdDeleteCompany_Click | orders | orders.views |
| procedure | Form_frmCompanyDetail.cmdSave_Click | orders | orders.views |
| procedure | Form_frmCompanyDetail.txtWebsite_DblClick | orders | orders.views |
| procedure | Form_frmCompanyList.Form_Open | orders | orders.views |
| procedure | Form_frmCompanyList.Open_frmCompanyDetail | orders | orders.views |
| procedure | Form_frmCompanyList.cmdAddNew_Click | orders | orders.views |
| procedure | Form_frmCompanyList.fraFilter_AfterUpdate | orders | orders.views |
| procedure | Form_frmCompanyList.txtCompanyID_Click | orders | orders.views |
| procedure | Form_frmCredentials.Form_BeforeUpdate | orders | foundation:sign-in |
| procedure | Form_frmCredentials.Form_Load | orders | foundation:sign-in |
| procedure | Form_frmCredentials.UserID | orders | foundation:sign-in |
| procedure | Form_frmCredentials.cmdAddMe_Click | orders | foundation:sign-in |
| procedure | Form_frmCredentials.cmdExit_Click | orders | foundation:sign-in |
| procedure | Form_frmEmployeeList.EmployeeCanBeDeleted | orders | orders.services |
| procedure | Form_frmEmployeeList.Form_AfterDelConfirm | orders | orders.views |
| procedure | Form_frmEmployeeList.Form_AfterInsert | orders | orders.views |
| procedure | Form_frmEmployeeList.Form_AfterUpdate | orders | orders.views |
| procedure | Form_frmEmployeeList.Form_BeforeDelConfirm | orders | orders.views |
| procedure | Form_frmEmployeeList.Form_BeforeUpdate | orders | orders.views |
| procedure | Form_frmEmployeeList.Form_Current | orders | orders.views |
| procedure | Form_frmEmployeeList.Form_Delete | orders | orders.services |
| procedure | Form_frmEmployeeList.RequeryEmployeeList | orders | orders.views |
| procedure | Form_frmEmployeeList.cboSupervisorID_Enter | orders | orders.views |
| procedure | Form_frmEmployeeList.cboSupervisorID_NotInList | orders | orders.views |
| procedure | Form_frmEmployeeList.cmdEmailEmployee_Click | orders | orders.views |
| procedure | Form_frmEmployeeList.cmdNewEmployee_Click | orders | orders.views |
| procedure | Form_frmEmployeeTitles.Form_Open | orders | orders.views |
| procedure | Form_frmLogin.AutoLogin_chk_AfterUpdate | orders | foundation:sign-in |
| procedure | Form_frmLogin.Form_Load | orders | foundation:sign-in |
| procedure | Form_frmLogin.Form_Unload | orders | foundation:sign-in |
| procedure | Form_frmLogin.UserID | orders | foundation:sign-in |
| procedure | Form_frmLogin.cmdLogin_Click | orders | foundation:sign-in |
| procedure | Form_frmOrderDetails.AllInvoiceLineItemsHaveStatus | orders | orders.services |
| procedure | Form_frmOrderDetails.CustomerID_AfterUpdate | orders | orders.services |
| procedure | Form_frmOrderDetails.Form_AfterUpdate | orders | orders.views |
| procedure | Form_frmOrderDetails.Form_BeforeDelConfirm | orders | orders.views |
| procedure | Form_frmOrderDetails.Form_BeforeInsert | orders | orders.services |
| procedure | Form_frmOrderDetails.Form_BeforeUpdate | orders | orders.views |
| procedure | Form_frmOrderDetails.Form_Close | orders | orders.views |
| procedure | Form_frmOrderDetails.Form_Current | orders | orders.views |
| procedure | Form_frmOrderDetails.Form_Delete | orders | orders.services |
| procedure | Form_frmOrderDetails.Form_Load | orders | orders.views |
| procedure | Form_frmOrderDetails.LockControls | orders | orders.views |
| procedure | Form_frmOrderDetails.PaidFieldsFilledOut | orders | orders.services |
| procedure | Form_frmOrderDetails.SetFormStatus | orders | orders.views |
| procedure | Form_frmOrderDetails.SetLineItemsStatus | orders | orders.services |
| procedure | Form_frmOrderDetails.ShippingFeeFilledOut | orders | orders.services |
| procedure | Form_frmOrderDetails.ShippingFieldsFilledOut | orders | orders.services |
| procedure | Form_frmOrderDetails.cmdAddOrder_Click | orders | orders.views |
| procedure | Form_frmOrderDetails.cmdCloseOrder_Click | orders | orders.services |
| procedure | Form_frmOrderDetails.cmdCreateInvoice_Click | orders | orders.services |
| procedure | Form_frmOrderDetails.cmdDeleteOrder_Click | orders | orders.services |
| procedure | Form_frmOrderDetails.cmdPrintInvoice_Click | orders | orders.views |
| procedure | Form_frmOrderDetails.cmdReceivePayment_Click | orders | orders.services |
| procedure | Form_frmOrderDetails.cmdShipOrder_Click | orders | orders.services |
| procedure | Form_frmOrderDetails.sfrmOrderLineItems_Enter | orders | orders.views |
| procedure | Form_frmOrderDetails.sfrmOrderLineItems_Exit | orders | orders.views |
| procedure | Form_frmOrderList.Form_Open | orders | orders.views |
| procedure | Form_frmOrderList.OrderID_Click | orders | orders.views |
| procedure | Form_frmOrderList.cmdAddOrder_Click | orders | orders.views |
| procedure | Form_frmOrderList.fraFilter_AfterUpdate | orders | orders.views |
| procedure | Form_sfrmCompanyDetail_Contacts.Form_AfterUpdate | orders | orders.views |
| procedure | Form_sfrmCompanyDetail_Contacts.Form_BeforeUpdate | orders | orders.views |
| procedure | Form_sfrmCompanyDetail_CustomerOrders.Detail_DblClick | orders | orders.views |
| procedure | Form_sfrmCompanyDetail_CustomerOrders.OpenForm_frmOrderDetails | orders | orders.views |
| procedure | Form_sfrmCompanyDetail_ShipperOrders.Detail_DblClick | orders | orders.views |
| procedure | Form_sfrmCompanyDetail_ShipperOrders.OpenForm_frmOrderDetails | orders | orders.views |
| procedure | Form_sfrmEmployee_Privileges.Form_AfterDelConfirm | orders | foundation:roles |
| procedure | Form_sfrmEmployee_Privileges.Form_AfterInsert | orders | foundation:roles |
| procedure | Form_sfrmEmployee_Privileges.Form_Open | orders | foundation:roles |
| procedure | Form_sfrmEmployee_Privileges.frmLoadedAsSubform | orders | foundation:roles |
| procedure | Form_sfrmOrderLineItems.Form_AfterDelConfirm | orders | orders.services |
| procedure | Form_sfrmOrderLineItems.Form_AfterUpdate | orders | orders.services |
| procedure | Form_sfrmOrderLineItems.Form_BeforeDelConfirm | orders | orders.views |
| procedure | Form_sfrmOrderLineItems.Form_BeforeInsert | orders | orders.services |
| procedure | Form_sfrmOrderLineItems.Form_BeforeUpdate | orders | orders.services |
| procedure | Form_sfrmOrderLineItems.Form_Current | orders | orders.views |
| procedure | Form_sfrmOrderLineItems.Form_Delete | orders | orders.views |
| procedure | Form_sfrmOrderLineItems.Form_Error | orders | orders.views |
| procedure | Form_sfrmOrderLineItems.ProductID_AfterUpdate | orders | orders.services |
| procedure | Form_sfrmOrderLineItems.ProductID_GotFocus | orders | orders.views |
| procedure | Form_sfrmOrderLineItems.ProductName_DblClick | orders | orders.views |
| procedure | Form_sfrmOrderLineItems.ReallocateInventory | orders | orders.services |
| procedure | Form_sfrmOrderLineItems.SetOrderDetailStatus | orders | orders.services |
| procedure | Form_sfrmOrderLineItems.cboProductCategories_AfterUpdate | orders | orders.views |
| procedure | Form_sfrmOrders_MostRecent_ByEmployee.OrderID_Click | orders | orders.views |
| procedure | Report_rptInvoice.Report_NoData | orders | orders.reports |
| procedure | modCompanies.GetTaxStatusID | orders | orders.services |
| procedure | modForms.RequeryListForms | orders | orders.views |
| procedure | modGlobal.GetNorthwindAddress | orders | orders.reports |
| procedure | modGlobal.GetWindowsUserName | orders | foundation:sign-in |
| procedure | modGlobal.Get_EmployeeFNLN | orders | foundation:sign-in |
| procedure | modGlobal.Get_UserID | orders | foundation:sign-in |
| procedure | modGlobal.Get_UserID_ForWindowsUser | orders | foundation:sign-in |
| procedure | modGlobal.InitializeUser | orders | foundation:sign-in |
| procedure | modGlobal.OneTimeProcessing | orders | orders.jobs |
| procedure | modGlobal.RecordModifiedString | orders | orders.views |
| procedure | modOrders.CloseAllOrderDetailsForms | orders | orders.views |
| procedure | modOrders.CloseOrderDetailsForm | orders | orders.views |
| procedure | modOrders.OpenOrderDetailsForm | orders | orders.views |
| procedure | modOrders.SetDatesToCurrent | orders | orders.jobs |
| procedure | modSecurity.HasPrivilege | orders | foundation:roles |
| procedure | modStartup.GetSystemSetting | orders | orders.services |
| procedure | modStartup.GetUserSetting | orders | foundation:sign-in |
| procedure | modStartup.SaveSystemSetting | orders | orders.jobs |
| procedure | modStartup.SaveUserSetting | orders | foundation:sign-in |
| procedure | modStartup.Startup | orders | orders.jobs |
| procedure | modTableDataMacros.GetAuditFieldsUserName | orders | foundation:audit-fields |
| procedure | modValidation.HighlightControl | orders | orders.views |
| procedure | modValidation.HighlightInvalidControls | orders | orders.views |
| procedure | modValidation.IsBoundToRequiredField | orders | orders.views |
| procedure | modValidation.IsValidForm | orders | orders.views |
| procedure | modValidation.ValidateForm | orders | orders.views |
| procedure | modValidation.ValidateForm_RemoveHighlights | orders | orders.views |
| query | qryCompanies | orders | orders.saved_queries |
| query | qryCompanyList | orders | orders.saved_queries |
| query | qryContacts | orders | orders.saved_queries |
| query | qryCustomerOrderList | orders | orders.saved_queries |
| query | qryCustomers | orders | orders.saved_queries |
| query | qryEmployeeLogin | orders | foundation:sign-in |
| query | qryEmployeePrivileges | orders | foundation:roles |
| query | qryEmployeeSupervisor | orders | orders.saved_queries |
| query | qryEmployees | orders | orders.saved_queries |
| query | qryInvoice | orders | orders.saved_queries |
| query | qryOrder | orders | orders.saved_queries |
| query | qryOrderLineItems | orders | orders.saved_queries |
| query | qryOrderList | orders | orders.saved_queries |
| query | qryOrderList_DetailStatus | orders | orders.saved_queries |
| query | qryOrderList_DetailStatus_Lowest | orders | orders.saved_queries |
| query | qryOrderTotal | orders | orders.saved_queries |
| query | qryOrders_MostRecent | orders | orders.saved_queries |
| query | qryPrivileges | orders | foundation:roles |
| query | qryShipperOrderList | orders | orders.saved_queries |
| query | qryShippers | orders | orders.saved_queries |
| query | qryTitle | orders | orders.saved_queries |
| query | qrycboCompanyType | orders | orders.saved_queries |
| query | qrycboCustomers | orders | orders.saved_queries |
| query | qrycboEmployees | orders | orders.saved_queries |
| query | qrycboOrderDetailStatus | orders | orders.saved_queries |
| query | qrycboOrderStatus | orders | orders.saved_queries |
| query | qrycboShippers | orders | orders.saved_queries |
| query | qrycboStates | orders | orders.saved_queries |
| query | qrycboTaxStatus | orders | orders.saved_queries |
| report | rptInvoice | orders | orders.reports |
| table | Companies | orders | legacy.models |
| table | CompanyTypes | orders | legacy.models |
| table | Contacts | orders | legacy.models |
| table | EmployeePrivileges | orders | foundation:roles |
| table | Employees | orders | legacy.models |
| table | OrderDetailStatus | orders | legacy.models |
| table | OrderDetails | orders | legacy.models |
| table | OrderStatus | orders | legacy.models |
| table | Orders | orders | legacy.models |
| table | Privileges | orders | foundation:roles |
| table | States | orders | legacy.models |
| table | Strings | orders | legacy.models |
| table | SystemSettings | orders | legacy.models |
| table | TaxStatus | orders | legacy.models |
| table | Titles | orders | legacy.models |
| data_macro | PurchaseOrderDetails.BeforeChange | purchasing | foundation:audit-fields |
| data_macro | PurchaseOrderStatus.BeforeChange | purchasing | foundation:audit-fields |
| data_macro | PurchaseOrders.BeforeChange | purchasing | foundation:audit-fields |
| form | frmPurchaseOrderDetails | purchasing | purchasing.views |
| form | frmPurchaseOrderList | purchasing | purchasing.views |
| form | frmSelectVendorDialog | purchasing | purchasing.views |
| form | sfrmCompanyDetail_VendorPurchaseOrders | purchasing | purchasing.views |
| form | sfrmPurchaseOrderLineItems | purchasing | purchasing.views |
| procedure | Form_frmPurchaseOrderDetails.AllocatePurchaseOrder | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.Form_BeforeInsert | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.Form_BeforeUpdate | purchasing | purchasing.forms |
| procedure | Form_frmPurchaseOrderDetails.Form_Current | purchasing | purchasing.views |
| procedure | Form_frmPurchaseOrderDetails.Form_Load | purchasing | purchasing.views |
| procedure | Form_frmPurchaseOrderDetails.LockControls | purchasing | purchasing.forms |
| procedure | Form_frmPurchaseOrderDetails.PoCloseFieldsFilledOut | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.SetWorkflowLabelColors | purchasing | purchasing.views |
| procedure | Form_frmPurchaseOrderDetails.VendorID_AfterUpdate | purchasing | purchasing.forms |
| procedure | Form_frmPurchaseOrderDetails.cmdAddNostock_Click | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.cmdAddPO_Click | purchasing | purchasing.views |
| procedure | Form_frmPurchaseOrderDetails.cmdApprovePO_Click | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.cmdClosePO_Click | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.cmdDeletePO_Click | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.cmdReceivePO_Click | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderDetails.cmdSubmitPO_Click | purchasing | purchasing.services |
| procedure | Form_frmPurchaseOrderList.PurchaseOrderID_Click | purchasing | purchasing.views |
| procedure | Form_frmPurchaseOrderList.cmdAddPO_Click | purchasing | purchasing.views |
| procedure | Form_frmSelectVendorDialog.Form_Load | purchasing | purchasing.views |
| procedure | Form_frmSelectVendorDialog.cmdCancel_Click | purchasing | purchasing.views |
| procedure | Form_frmSelectVendorDialog.cmdOK_Click | purchasing | purchasing.forms |
| procedure | Form_frmSelectVendorDialog.lstVendor_DblClick | purchasing | purchasing.views |
| procedure | Form_sfrmCompanyDetail_VendorPurchaseOrders.Detail_DblClick | purchasing | purchasing.views |
| procedure | Form_sfrmCompanyDetail_VendorPurchaseOrders.OpenForm_frmPurchaseOrderDetails | purchasing | purchasing.views |
| procedure | Form_sfrmPurchaseOrderLineItems.Form_BeforeUpdate | purchasing | purchasing.forms |
| procedure | Form_sfrmPurchaseOrderLineItems.Form_Error | purchasing | purchasing.views |
| procedure | Form_sfrmPurchaseOrderLineItems.ProductID_AfterUpdate | purchasing | purchasing.forms |
| procedure | Form_sfrmPurchaseOrderLineItems.PurchaseOrderDetailID_Click | purchasing | purchasing.views |
| procedure | Form_sfrmPurchaseOrderLineItems.ValidateLineItem | purchasing | purchasing.forms |
| procedure | modPurchaseOrders.AddPurchaseOrderDetail | purchasing | purchasing.services |
| procedure | modPurchaseOrders.ReorderProduct | purchasing | purchasing.services |
| query | qryPurchaseOrder | purchasing | purchasing.saved_queries |
| query | qryPurchaseOrderCost | purchasing | purchasing.saved_queries |
| query | qryPurchaseOrderLineItems | purchasing | purchasing.saved_queries |
| query | qryPurchaseOrderList | purchasing | purchasing.saved_queries |
| query | qryVendorPurchaseOrderList | purchasing | purchasing.saved_queries |
| query | qrycboProducts_PO | purchasing | purchasing.saved_queries |
| query | qrycboVendors | purchasing | purchasing.saved_queries |
| table | PurchaseOrderDetails | purchasing | legacy.models |
| table | PurchaseOrderStatus | purchasing | legacy.models |
| table | PurchaseOrders | purchasing | legacy.models |
| form | frmReports | reports | reports.views |
| procedure | Form_frmReports.Form_Open | reports | reports.views |
| procedure | Form_frmReports.ReportFormInitialization | reports | reports.views |
| procedure | Form_frmReports.cmdFallCatalog_Click | reports | reports.views |
| procedure | Form_frmReports.cmdPreviewReport_Click | reports | reports.views |
| procedure | Form_frmReports.cmdSalesByProductReportMonthly_Click | reports | reports.views |
| procedure | Form_frmReports.cmdSalesByProductReportQuarterly_Click | reports | reports.views |
| procedure | Form_frmReports.cmdSalesByemployeeReport_Click | reports | reports.views |
| procedure | Report_rptProductCatalog.GroupHeader0_Print | reports | reports.reports |
| procedure | Report_rptProductCatalog.Report_NoData | reports | reports.reports |
| procedure | Report_rptProductCatalog.Report_Open | reports | reports.reports |
| procedure | Report_rptSalesByEmployee.Report_NoData | reports | reports.reports |
| procedure | Report_rptSalesByEmployee.Report_Open | reports | reports.reports |
| procedure | Report_rptSalesByEmployee.cboFilterByEmployee_DblClick | reports | reports.reports |
| procedure | Report_rptSalesByProduct.Report_NoData | reports | reports.reports |
| procedure | Report_rptSalesByProduct.Report_Open | reports | reports.reports |
| procedure | Report_rptSalesByProductQuarterly.Report_NoData | reports | reports.reports |
| procedure | Report_rptSalesByProductQuarterly.Report_Open | reports | reports.reports |
| procedure | modReportParameters.reportParameterEndDate | reports | reports.services |
| procedure | modReportParameters.reportParameterStartDate | reports | reports.services |
| procedure | modRibbonCallback.cmdReports_OnAction | reports | reports.views |
| query | qryTotalSalesByProduct | reports | reports.saved_queries |
| query | qryrptProductCatalog | reports | reports.saved_queries |
| query | qryrptSalesByEmployee | reports | reports.saved_queries |
| query | qryrptSalesByProduct_ByMonth | reports | reports.saved_queries |
| query | qryrptSalesByProduct_ByQuarter | reports | reports.saved_queries |
| report | rptProductCatalog | reports | reports.reports |
| report | rptSalesByEmployee | reports | reports.reports |
| report | rptSalesByProduct | reports | reports.reports |
| report | rptSalesByProductQuarterly | reports | reports.reports |
| report | srptCatalog_TableOfContents | reports | reports.reports |
| report | srptGastronomic | reports | reports.reports |
| report | srptOrderForm | reports | reports.reports |
| report | srptQuality | reports | reports.reports |
| report | srptShipVia | reports | reports.reports |

## Drop

| type | name | area | reason |
|---|---|---|---|
| procedure | Form_frmProductDetail.Form_Activate | inventory | Access screen refresh when the window regains focus; a web page recalculates the figures on every load |
| procedure | Form_frmProductDetail.Form_AfterDelConfirm | inventory | refreshes the product picker and any open product list after a delete; web pages are rebuilt on load |
| procedure | Form_frmProductDetail.Form_AfterInsert | inventory | refreshes on-screen state and open lists after an insert; the web page redirects and reloads |
| procedure | Form_frmProductDetail.Form_AfterUpdate | inventory | refreshes on-screen state and open lists after a save; the web page redirects and reloads |
| procedure | Form_frmProductDetail.Form_Close | inventory | Access lazy-loading cleanup and refresh of other open windows; not needed on the web |
| procedure | Form_frmProductDetail.Form_Current | inventory | only re-applies the screen states of ControlStates on record navigation; that behaviour is kept through R-inventory-021 and R-inventory-022 |
| procedure | Form_frmProductDetail.Form_Delete | inventory | removes the product from the Access recently-used navigation list; no such list in the web app |
| procedure | Form_frmProductDetail.Form_Load | inventory | Access lazy loading of tab subforms; not needed on the web |
| procedure | Form_frmProductDetail.imgHelp_Click | inventory | empty help handler; does nothing |
| procedure | Form_frmProductDetail.tabProducts_Change | inventory | Access lazy loading of tab subforms; not needed on the web |
| procedure | Form_sfrmProductCategories.Form_AfterInsert | inventory | refreshes the category list box after an insert; web pages are rebuilt on load |
| procedure | Form_sfrmProductCategories.Form_Current | inventory | keeps the list box selection in step with the record shown; Access UI only |
| procedure | Form_sfrmProductCategories.Form_Delete | inventory | refreshes the category list box after a delete; web pages are rebuilt on load |
| procedure | Form_sfrmProductDetail_StockTake.Form_AfterInsert | inventory | refreshes the parent window's figures after an insert; the web page reloads |
| procedure | Form_sfrmProductDetail_StockTake.RequeryQuantities | inventory | refreshes the parent window and any open product list; the web page reloads |
| procedure | modForms.RequeryProductList | inventory | refreshes the product list window if it is open; web pages are rebuilt on load |
| query | qryMaxStockTakeDate | inventory | unused: no form, report, query or code refers to it; the latest stock take is found in code (R-inventory-002) |
| form | _Design | orders | layout sample of the template with no record source and no behaviour |
| form | frmAbout | orders | about box of the Access template |
| form | frmAdmin | orders | launcher for the template's maintenance tools (demo data, messages, settings); privileges go to foundation roles, settings to the Django admin, product categories to the inventory area |
| form | frmGenericDialog | orders | generic message box used by other screens; web messages replace it |
| form | frmNorthwindFeatures | orders | help catalogue of the Access template's features |
| form | frmStartup | orders | shown only when Access has not trusted the database; no web equivalent |
| form | frmWelcome | orders | welcome screen of the Access template |
| form | sfrmAdmin_DeleteTestData | orders | admin tool that wipes the template's sample data |
| form | sfrmAdmin_InternetOrders | orders | admin tool that generates random sample orders |
| form | sfrmAdmin_ResetDates | orders | admin tool that shifts sample dates on demand; the first-run shift is kept by the start-up rule |
| form | sfrmAdmin_Strings | orders | editor for the Access message texts, which are dropped |
| form | sfrmAdmin_SystemSettings | orders | settings grid of the admin screen; the settings table is kept and edited through the Django admin |
| procedure | Form_frmAbout.cmdClose_Click | orders | part of the dropped about box |
| procedure | Form_frmAdmin.Form_Open | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.UpdateSubLabels | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdDeleteTestData_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdInternetOrders_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdPrivileges_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdProductCategories_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdRelationshipsDiagram_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdResetDates_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdStrings_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmAdmin.cmdSystemSettings_Click | orders | part of the dropped admin launcher |
| procedure | Form_frmCompanyDetail.Form_Open | orders | clears a filter left by an earlier Access session; the web screen has no persisted filter |
| procedure | Form_frmCompanyDetail.cmdClickToMap_Click | orders | opens the address in a retired consumer map site (not needed, client answer to Q-orders-008) |
| procedure | Form_frmCompanyDetail.cmdEmail_Click | orders | e-mails the Access screen through the mail client (not needed, client answer to Q-orders-008) |
| procedure | Form_frmCompanyDetail.cmdShowFilter_Click | orders | shows the raw filter expression in a dialog |
| procedure | Form_frmCompanyDetail.txtBusinessPhone_Click | orders | places the cursor at the start of an empty masked field; Access input behaviour only |
| procedure | Form_frmCompanyList.cmdLabelWizard_Click | orders | starts the Access mailing-label wizard (not needed, client answer to Q-orders-008) |
| procedure | Form_frmCompanyList.cmdShowFilter_Click | orders | shows the raw filter expression in a dialog |
| procedure | Form_frmCompanyList.cmdShowHideFields_Click | orders | opens the Access unhide-columns dialog |
| procedure | Form_frmGenericDialog.Form_Load | orders | part of the dropped generic message box |
| procedure | Form_frmGenericDialog.cmdCancelClose_Click | orders | part of the dropped generic message box |
| procedure | Form_frmGenericDialog.cmdOK_Click | orders | part of the dropped generic message box |
| procedure | Form_frmNorthwindFeatures.txtHelpKeywords_Click | orders | part of the dropped feature help catalogue |
| procedure | Form_frmOrderDetails.Form_AfterInsert | orders | only adds the new order to the dropped recently-used list |
| procedure | Form_frmOrderDetails.Form_Open | orders | empty handler (work is done on load) |
| procedure | Form_frmOrderList.cmdShowFilter_Click | orders | shows the raw filter expression in a dialog; the web list shows its filter controls |
| procedure | Form_frmWelcome.Form_Close | orders | part of the dropped welcome screen |
| procedure | Form_frmWelcome.Form_Open | orders | part of the dropped welcome screen |
| procedure | Form_frmWelcome.cmdGetStarted_Click | orders | part of the dropped welcome screen |
| procedure | Form_sfrmAdmin_DeleteTestData.cmdRemoveTestData_Click | orders | wipes the template's sample data; demo tool |
| procedure | Form_sfrmAdmin_InternetOrders.cmdCreate_Click | orders | generates random sample orders; demo tool |
| procedure | Form_sfrmAdmin_InternetOrders.txtCount_BeforeUpdate | orders | input check of the dropped sample-order generator |
| procedure | Form_sfrmAdmin_ResetDates.cmdResetDates_Click | orders | on-demand sample date shift; demo tool |
| procedure | Form_sfrmAdmin_Strings.Form_AfterDelConfirm | orders | empty handler of the dropped message-text editor |
| procedure | Form_sfrmAdmin_Strings.Form_AfterInsert | orders | empty handler of the dropped message-text editor |
| procedure | Form_sfrmAdmin_SystemSettings.Form_AfterDelConfirm | orders | empty handler of the dropped settings grid |
| procedure | Form_sfrmAdmin_SystemSettings.Form_AfterInsert | orders | empty handler of the dropped settings grid |
| procedure | Form_sfrmCompanyDetail_Contacts.txtPrimaryPhone_Click | orders | places the cursor at the start of an empty masked field; Access input behaviour only |
| procedure | Form_sfrmCompanyDetail_Contacts.txtSecondaryPhone_Click | orders | places the cursor at the start of an empty masked field; Access input behaviour only |
| procedure | Form_sfrmOrderLineItems.ProductCategoryName_GotFocus | orders | moves keyboard focus between two grid columns; layout only |
| procedure | Form_sfrmOrderLineItems.ProductName_GotFocus | orders | moves keyboard focus to the product list; layout only |
| procedure | Report_rptInvoice.Report_Activate | orders | shows the report group on the Access ribbon |
| procedure | Report_rptInvoice.Report_Close | orders | hides the report group on the Access ribbon |
| procedure | clsErrorHandler.Class_Initialize | orders | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.ErrorHandlerExample | orders | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.ErrorHandlerExample_EventProcedure | orders | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.HandleError | orders | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | clsErrorHandler.LogErrorToFile | orders | Access error dialog and text-file error log; the web app uses framework logging |
| procedure | modCompanies.GetRandomCustomerID | orders | random customer for the dropped sample-order generator |
| procedure | modDAO.GetRandomPkValue | orders | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDAO.HasDataMacro | orders | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDAO.HasField | orders | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDAO.HasProperty | orders | Access object-model helper (random key, data-macro and property probes); no business behaviour |
| procedure | modDebug.DumpTempVars | orders | developer debugging helper |
| procedure | modDebug.NotImplemented | orders | developer debugging helper |
| procedure | modFiles.FileExists | orders | file helper used only by the Access first run |
| procedure | modFiles.StringToFile | orders | file helper used only by the Access first run |
| procedure | modForms.ControlCurrentView | orders | Access view probe used to colour highlighted fields; the web forms mark errors themselves |
| procedure | modForms.ControlDefaultView | orders | Access view probe used to colour highlighted fields; the web forms mark errors themselves |
| procedure | modForms.IsFormOpen | orders | Access window probe; no business behaviour |
| procedure | modGlobal.AddToMRU | orders | maintains the dropped recently-used list |
| procedure | modGlobal.RemoveFromMRU | orders | maintains the dropped recently-used list |
| procedure | modGlobal.SetCtrlCurrencyFormat | orders | re-applies Access currency formats for regional settings at first run |
| procedure | modGlobal.ToAccessDate | orders | formats dates for Access SQL text |
| procedure | modGlobal.g_dbApp | orders | returns the Access database handle |
| procedure | modMath.GetRandom | orders | random numbers for the dropped sample-order generator |
| procedure | modMath.MaxValue | orders | generic helper not used by any kept behaviour |
| procedure | modOrders.CreateRandomOrders | orders | generates random sample orders for the dropped admin tool |
| procedure | modOrders.GetRandomProductID | orders | random product for the dropped sample-order generator |
| procedure | modRibbonCallback.ActivateTab | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.RibbonFinish | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.Ribbon_RefreshMRU | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdAbout_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdAddOrder_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdAdmin_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdCustomers_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdEmployees_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdExitApplication_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdExportToExcel_OnAction | orders | Access export of the current list to Excel (not needed, client answer to Q-orders-008) |
| procedure | modRibbonCallback.cmdFeatures_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdNorthwindDocumentation_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.cmdOrders_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetItemCount | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetItemID | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetItemLabel | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_GetSelectedItemIndex | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_OnAction | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ddMRU_OnChange | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modRibbonCallback.ribbonLoaded | orders | Access ribbon callback (navigation buttons and recently-used list); the web navigation bar replaces it |
| procedure | modStartup.CloseAllForms | orders | closes Access windows on exit |
| procedure | modStartup.CloseAllReports | orders | closes Access windows on exit |
| procedure | modStartup.Finish | orders | Access shutdown routine |
| procedure | modStartup.SetAppTitle | orders | puts the app name, version and user in the Access title bar; the web layout shows the signed-in user |
| procedure | modStrings.GetString | orders | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modStrings.StringFormat | orders | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modStrings.StringFormatSQL | orders | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modStrings.StringToDictionary | orders | message-text and argument-string helper; the new app keeps messages in templates and passes parameters in URLs |
| procedure | modTableDataMacros.AddDataMacros | orders | installs the audit data macros on Access first run; the audit rule is kept in the model layer |
| query | qryMRU | orders | feeds the dropped recently-used ribbon list |
| query | qryOrders_MostRecent_Customer | orders | unused: no form, report, query or code refers to it |
| query | qryOrders_MostRecent_Employee | orders | unused: no form, report, query or code refers to it |
| query | qryOrders_MostRecent_ModifiedOn | orders | unused: no form, report, query or code refers to it |
| query | qryStrings | orders | feeds the dropped message-text editor |
| query | qrySystemSettings | orders | feeds only the dropped admin sub-screens; settings are edited through the Django admin |
| table | MRU | orders | recently-used list behind the Access ribbon; the web app's lists and browser history replace it |
| table | NorthwindFeatures | orders | help catalogue of the Access template's own features; no business data |
| table | UserSettings | orders | per-machine auto-login preference for the Windows user; local sign-in (foundation) replaces it |
| table | Welcome | orders | welcome-screen text and the data-macro template used by the Access first run; no business data |
| procedure | Form_frmPurchaseOrderDetails.Form_AfterInsert | purchasing | adds the new purchase order to the Access ribbon's recently-used list; a desktop UI convenience with no web equivalent |
| procedure | Form_frmPurchaseOrderDetails.Form_AfterUpdate | purchasing | clears field highlights and refreshes the open list window; a web page reloads from the database |
| procedure | Form_frmPurchaseOrderDetails.Form_Close | purchasing | window bookkeeping for several open purchase order windows; not needed in a browser |
| procedure | Form_frmPurchaseOrderDetails.Form_Delete | purchasing | removes the deleted purchase order from the Access ribbon's recently-used list; a desktop UI convenience |
| procedure | Form_frmPurchaseOrderDetails.Form_Open | purchasing | empty handler (only its error handling); no behaviour |
| procedure | Form_frmPurchaseOrderDetails.VendorID_BeforeUpdate | purchasing | its only behaviour is the confirm-and-delete-all-lines prompt for changing the vendor of a saved purchase order; the client fixed the vendor once a purchase order is saved (Q-purchasing-001), so the new app has no vendor change (R-purchasing-015) |
| procedure | Form_frmPurchaseOrderList.Form_Open | purchasing | clears a filter left over from an earlier Access session; the web list starts unfiltered |
| procedure | Form_sfrmPurchaseOrderLineItems.Form_Current | purchasing | clears field highlights when moving between lines; UI only |
| procedure | modPurchaseOrders.CloseAllPurchaseOrderDetailsForms | purchasing | releases the list of open purchase order windows at shutdown; not needed in a browser |
| procedure | modPurchaseOrders.ClosePurchaseOrderDetailsForm | purchasing | removes a closed purchase order window from the list of open windows; not needed in a browser |
| procedure | modPurchaseOrders.OpenPurchaseOrderDetailsForm | purchasing | opens a purchase order in an extra Access window (several at once); the purchase order detail URL replaces it |
| procedure | modRibbonCallback.cmdAddPurchaseOrder_OnAction | purchasing | Access ribbon button that opens a new purchase order; the app's navigation bar and the list's new button replace it |
| procedure | modRibbonCallback.cmdPurchaseOrders_OnAction | purchasing | Access ribbon button that opens the purchase order list; the app's navigation bar replaces it |
| query | qryVendors | purchasing | not used by any form, report, query or code; qrycboVendors already lists the vendors |
| form | frmLearn | reports | Access learning page (embedded browser and links to Microsoft training); no business function |
| macro | frmLearn.cmdOpenReport.Click | reports | only opens the Access learning report; dropped with frmLearn |
| procedure | Form_frmReports.Form_Close | reports | only clears the Access session variables that hold the chosen report; a web page keeps that choice in the request |
| procedure | Form_frmReports.cmdEmployeeEmailList_Click | reports | selects the dropped employee email list report |
| procedure | Form_frmReports.cmdEmployeePhoneList_Click | reports | selects the dropped employee phone list report |
| procedure | Report__Design.Report_Activate | reports | event of the dropped report design template |
| procedure | Report__Design.Report_Close | reports | event of the dropped report design template |
| procedure | Report__Design.Report_NoData | reports | event of the dropped report design template |
| procedure | Report_rptEmployeeEmailList.Report_Activate | reports | event of the dropped employee email list report; only refreshes the Access ribbon |
| procedure | Report_rptEmployeeEmailList.Report_Close | reports | event of the dropped employee email list report; only refreshes the Access ribbon |
| procedure | Report_rptEmployeeEmailList.Report_NoData | reports | event of the dropped employee email list report |
| procedure | Report_rptEmployeePhoneList.Report_Activate | reports | event of the dropped employee phone list report; only refreshes the Access ribbon |
| procedure | Report_rptEmployeePhoneList.Report_Close | reports | event of the dropped employee phone list report; only refreshes the Access ribbon |
| procedure | Report_rptEmployeePhoneList.Report_NoData | reports | event of the dropped employee phone list report |
| procedure | Report_rptLearn.Report_Activate | reports | event of the dropped Access learning report |
| procedure | Report_rptLearn.Report_Close | reports | event of the dropped Access learning report |
| procedure | Report_rptLearn.Report_NoData | reports | event of the dropped Access learning report |
| procedure | Report_rptProductCatalog.Report_Activate | reports | only refreshes the Access ribbon |
| procedure | Report_rptProductCatalog.Report_Close | reports | only refreshes the Access ribbon |
| procedure | Report_rptRelationshipsWindow.Report_Activate | reports | event of the dropped table diagram report |
| procedure | Report_rptRelationshipsWindow.Report_Close | reports | event of the dropped table diagram report |
| procedure | Report_rptRelationshipsWindow.Report_NoData | reports | event of the dropped table diagram report |
| procedure | Report_rptSalesByEmployee.Report_Activate | reports | only refreshes the Access ribbon |
| procedure | Report_rptSalesByEmployee.Report_Close | reports | only refreshes the Access ribbon |
| procedure | Report_rptSalesByProduct.Report_Activate | reports | only refreshes the Access ribbon |
| procedure | Report_rptSalesByProduct.Report_Close | reports | only refreshes the Access ribbon |
| procedure | Report_rptSalesByProductQuarterly.Report_Activate | reports | only refreshes the Access ribbon |
| procedure | Report_rptSalesByProductQuarterly.Report_Close | reports | only refreshes the Access ribbon |
| procedure | modRibbonCallback.Ribbon_ShowReportsGroup | reports | refreshes the Access ribbon so its report options group appears; the web report pages carry their own print and PDF actions |
| procedure | modRibbonCallback.cmdLearn_OnAction | reports | menu entry for the dropped Access learning page |
| procedure | modRibbonCallback.gReportOptions_GetVisible | reports | Access ribbon callback that shows the report options group only while a report is open; no web equivalent needed |
| query | qrySales_SalesRep | reports | not used by any form, report, query or code; a year-to-date gross sales total per salesperson that the kept monthly sales per employee report supersedes (Q-reports-007) |
| query | qryrptEmployeeEmailList | reports | record source of the dropped employee email list report |
| query | qryrptEmployeePhoneList | reports | record source of the dropped employee phone list report |
| report | _Design | reports | Access design template (logo and title layout) for building new reports; holds no data and no business behaviour |
| report | rptEmployeeEmailList | reports | not one of the at most four reports kept beside the invoice; a plain list of employee names and email addresses that the employee list page already shows (Q-reports-001) |
| report | rptEmployeePhoneList | reports | not one of the at most four reports kept beside the invoice; a plain list of employee names and phone numbers that the employee list page already shows (Q-reports-001) |
| report | rptLearn | reports | printable copy of the Access learning text; no business function |
| report | rptRelationshipsWindow | reports | a static picture of the Access table diagram for developers; the new app documents its data model separately |
| table | Catalog_TableOfContents | reports | scratch table that the catalog empties and refills on every generation; it holds no business data, and the new catalog builds its table of contents while rendering (R-reports-013) |
| table | Learn | reports | help text about Microsoft Access shipped with the template; no business data |

## Out of scope

None.
