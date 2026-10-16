# Sales and Catalog Reports (area `reports`)

Engagement: northwind-demo. Spec version 1.0, not signed yet. The source of truth is
`analysis/rules/reports.json`. This page shows the same content for a reader.

## Summary

This area covers the report selection page, the sales reports it opens, and the printable
product catalog. Scope says to keep the invoice report plus at most four other reports. The
invoice report belongs to the orders area. We propose keeping these four:

| Kept report | What it shows |
|---|---|
| Monthly sales per employee (`rptSalesByEmployee`) | Net order totals per salesperson per month in a date range, with a chart. The user can filter it to one salesperson. |
| Monthly sales per product (`rptSalesByProduct`) | Net sales per product per month in a date range, with month subtotals, a grand total and a chart. |
| Quarterly sales per product (`rptSalesByProductQuarterly`) | The same figures per calendar quarter. |
| Product catalog (`rptProductCatalog` and its five sub-reports) | A printable catalog by category, with a generated table of contents, fixed text pages, and an order form that lists the shippers. |

We propose dropping these:
- The employee email list and the employee phone list. The employee list page already shows those columns (Q-reports-001).
- The Access learning page and its report.
- The table-diagram report.
- The report design template.
- An unused year-to-date query.
- The Access ribbon plumbing.

Counts: 76 objects in scope. 35 are kept and 41 are dropped. There are 16 rules and 7 open questions.

## Rules

| Id | Rule | Trigger | Sources | Test | Confidence | Questions |
|---|---|---|---|---|---|---|
| R-reports-001 | When the report selection page opens, the monthly sales per employee report is already selected and its date inputs are shown. | form:frmReports.Open | procedure Form_frmReports.Form_Open; form frmReports | rule | high | |
| R-reports-002 | Choosing a sales report shows the start and end date inputs. The end date defaults to the calendar date of the latest order, and the start date to the same day three calendar months earlier. Choosing the catalog hides and clears both dates. The page shows the name of the chosen report. | procedure:Form_frmReports.ReportFormInitialization | procedures ReportFormInitialization, cmdSalesByemployeeReport_Click, cmdSalesByProductReportMonthly_Click, cmdSalesByProductReportQuarterly_Click, cmdFallCatalog_Click | rule | high | Q-reports-002 |
| R-reports-003 | The sales report queries take their period from the selection page. Run without the page, they default to the same range: three calendar months up to the date of the latest order. | procedure:modReportParameters.reportParameterStartDate | procedures modReportParameters.reportParameterStartDate, reportParameterEndDate | rule | high | Q-reports-002 |
| R-reports-004 | Monthly sales per employee: for each salesperson and calendar month, the figure is the sum of the order totals of orders dated in the range. The bounds are inclusive and are compared with the full date and time. An order total is the sum of quantity × unit price × (1 − discount) over its lines. Orders of every status count. Months sort by year, then month. | query:qryrptSalesByEmployee | query qryrptSalesByEmployee | equivalence | high | Q-reports-002, Q-reports-003 |
| R-reports-005 | Monthly sales per product: the sum of quantity × unit price × (1 − discount) per product and calendar month, for orders dated in the range. Orders of every status count. | query:qryrptSalesByProduct_ByMonth | query qryrptSalesByProduct_ByMonth | equivalence | high | Q-reports-002, Q-reports-003 |
| R-reports-006 | Quarterly sales per product: the same net amounts, grouped by product and calendar quarter. Each quarter is labelled with its quarter number, then the year. | query:qryrptSalesByProduct_ByQuarter | query qryrptSalesByProduct_ByQuarter | equivalence | high | Q-reports-002, Q-reports-003, Q-reports-004 |
| R-reports-007 | Each sales report prints the order-date range it covers in its header. | report:rptSalesByEmployee.Open | procedures Report_Open of rptSalesByEmployee, rptSalesByProduct, rptSalesByProductQuarterly | rule | high | |
| R-reports-008 | A sales report with no orders in the period tells the user it has no data and does not open. | report:rptSalesByEmployee.NoData | procedures Report_NoData of the three sales reports | rule | high | |
| R-reports-009 | The sales per employee report opens in an interactive view. A list holds the salespeople in the report plus an "all employees" entry. Picking a person limits the rows, totals and chart to that person, and picking "all" removes the limit. | report:rptSalesByEmployee.cboFilterByEmployee.DblClick | procedure Report_rptSalesByEmployee.cboFilterByEmployee_DblClick; report rptSalesByEmployee | rule | high | |
| R-reports-010 | The product sales reports show a subtotal per month or quarter, a grand total for the range, and a chart. Every sales report shows when it was produced and "page n of m". | report:rptSalesByProduct.Open | reports rptSalesByProduct, rptSalesByProductQuarterly, rptSalesByEmployee | rule | medium | Q-reports-004 |
| R-reports-011 | A product's lifetime sales is the sum of quantity × unit price × (1 − discount) over all of its order lines, with no date or status filter. The catalog lists every product that has a category. A product that was never sold is still listed, with no sales. | query:qryrptProductCatalog | queries qryrptProductCatalog, qryTotalSalesByProduct | equivalence | high | Q-reports-003 |
| R-reports-012 | Each catalog category section shows the category's description and image, the number of priced items, the lowest and highest unit price, and the category's total lifetime sales, then its products. | report:rptProductCatalog.Open | report rptProductCatalog | rule | high | Q-reports-006 |
| R-reports-013 | The catalog's table of contents lists each category once, with the page where its section starts. The catalog is first rendered in full to PDF to record those pages, then shown. Every full generation discards the previous table of contents. Until a table of contents exists, the catalog shows a note asking the user to generate the PDF. | form:frmReports.cmdPreviewReport.Click | procedures Form_frmReports.cmdPreviewReport_Click, Report_rptProductCatalog.Report_Open, Report_rptProductCatalog.GroupHeader0_Print; report srptCatalog_TableOfContents | e2e | high | Q-reports-005 |
| R-reports-014 | The catalog has fixed pages: a quality statement and a gastronomic introduction, both taken from the app's maintained text strings. It also has an order form with the house company's address and phone and a tick-box list of shippers. The house company is the company whose company type marks it as the seller. | report:rptProductCatalog.Open | reports srptQuality, srptGastronomic, srptOrderForm, srptShipVia | e2e | high | Q-reports-005 |
| R-reports-015 | A catalog with no rows warns the user that there is no data but still opens. | report:rptProductCatalog.NoData | procedure Report_rptProductCatalog.Report_NoData | rule | high | |
| R-reports-016 | The main menu's Reports entry opens the selection page. Preview opens the chosen report: the sales per employee report in its interactive view, and the others as a print preview that can be saved as PDF. | form:frmReports.cmdPreviewReport.Click | procedures modRibbonCallback.cmdReports_OnAction, Form_frmReports.cmdPreviewReport_Click; form frmReports | e2e | high | Q-reports-001 |

How each test kind is proven:
- `rule`: one test each in `app/northwind/reports/tests/test_rules.py`.
- `equivalence`: proven by the equivalence units of the cited queries.
- `e2e`: proven by the workflows below.

## Keep and drop

### Keep

| Type | Name | Component |
|---|---|---|
| form | frmReports | reports.views |
| procedure | Form_frmReports.Form_Open | reports.views |
| procedure | Form_frmReports.ReportFormInitialization | reports.views |
| procedure | Form_frmReports.cmdSalesByemployeeReport_Click | reports.views |
| procedure | Form_frmReports.cmdSalesByProductReportMonthly_Click | reports.views |
| procedure | Form_frmReports.cmdSalesByProductReportQuarterly_Click | reports.views |
| procedure | Form_frmReports.cmdFallCatalog_Click | reports.views |
| procedure | Form_frmReports.cmdPreviewReport_Click | reports.views |
| procedure | modRibbonCallback.cmdReports_OnAction | reports.views |
| procedure | modReportParameters.reportParameterStartDate | reports.services |
| procedure | modReportParameters.reportParameterEndDate | reports.services |
| query | qryrptSalesByEmployee | reports.saved_queries |
| query | qryrptSalesByProduct_ByMonth | reports.saved_queries |
| query | qryrptSalesByProduct_ByQuarter | reports.saved_queries |
| query | qryrptProductCatalog | reports.saved_queries |
| query | qryTotalSalesByProduct | reports.saved_queries |
| report | rptSalesByEmployee | reports.reports |
| report | rptSalesByProduct | reports.reports |
| report | rptSalesByProductQuarterly | reports.reports |
| report | rptProductCatalog | reports.reports |
| report | srptCatalog_TableOfContents | reports.reports |
| report | srptGastronomic | reports.reports |
| report | srptOrderForm | reports.reports |
| report | srptQuality | reports.reports |
| report | srptShipVia | reports.reports |
| procedure | Report_rptSalesByEmployee.Report_Open | reports.reports |
| procedure | Report_rptSalesByEmployee.Report_NoData | reports.reports |
| procedure | Report_rptSalesByEmployee.cboFilterByEmployee_DblClick | reports.reports |
| procedure | Report_rptSalesByProduct.Report_Open | reports.reports |
| procedure | Report_rptSalesByProduct.Report_NoData | reports.reports |
| procedure | Report_rptSalesByProductQuarterly.Report_Open | reports.reports |
| procedure | Report_rptSalesByProductQuarterly.Report_NoData | reports.reports |
| procedure | Report_rptProductCatalog.Report_Open | reports.reports |
| procedure | Report_rptProductCatalog.GroupHeader0_Print | reports.reports |
| procedure | Report_rptProductCatalog.Report_NoData | reports.reports |

### Drop

| Type | Name | Reason |
|---|---|---|
| table | Catalog_TableOfContents | A scratch table that each catalog run empties and refills; it holds no business data. The new catalog builds its table of contents while rendering. |
| table | Learn | Help text about Microsoft Access that ships with the template. |
| form | frmLearn | Access learning page. |
| macro | frmLearn.cmdOpenReport.Click | Opens only the learning report. |
| query | qrySales_SalesRep | Nothing uses it. It gives a year-to-date gross total per salesperson (Q-reports-007). |
| query | qryrptEmployeeEmailList | Feeds the dropped email list. |
| query | qryrptEmployeePhoneList | Feeds the dropped phone list. |
| report | rptEmployeeEmailList | Outside the four kept reports; the employee list page shows the same data (Q-reports-001). |
| report | rptEmployeePhoneList | Outside the four kept reports; the employee list page shows the same data (Q-reports-001). |
| report | rptLearn | Printable copy of the Access learning text. |
| report | rptRelationshipsWindow | Static picture of the Access table diagram. |
| report | _Design | Layout template for building new reports. |
| procedure | Form_frmReports.Form_Close | Clears the Access session variables only. |
| procedure | Form_frmReports.cmdEmployeeEmailList_Click | Selects a dropped report. |
| procedure | Form_frmReports.cmdEmployeePhoneList_Click | Selects a dropped report. |
| procedure | modRibbonCallback.cmdLearn_OnAction | Menu entry for the dropped learning page. |
| procedure | modRibbonCallback.Ribbon_ShowReportsGroup | Access ribbon refresh. |
| procedure | modRibbonCallback.gReportOptions_GetVisible | Access ribbon visibility callback. |
| procedure | Report_Activate and Report_Close of rptSalesByEmployee, rptSalesByProduct, rptSalesByProductQuarterly, rptProductCatalog | Refresh the Access ribbon only. |
| procedure | Report_Activate, Report_Close and Report_NoData of rptEmployeeEmailList, rptEmployeePhoneList, rptLearn, rptRelationshipsWindow, _Design | Events of dropped reports. |

## Workflows

| Id | Title | Forms | Reports | Rules | Steps |
|---|---|---|---|---|---|
| sales_reports | Choose a sales report, set the period, preview, filter and save as PDF | frmReports | rptSalesByEmployee, rptSalesByProduct, rptSalesByProductQuarterly | R-reports-016, R-reports-001, R-reports-002, R-reports-007, R-reports-008, R-reports-009, R-reports-010 | 1. Open Reports from the main menu. 2. See the employee report preselected with the default period. 3. Change the dates. 4. Preview the report and filter it to one salesperson. 5. Preview the monthly and quarterly product reports. 6. Save a report as PDF. |
| product_catalog | Generate the printable product catalog | frmReports | rptProductCatalog, srptCatalog_TableOfContents, srptQuality, srptGastronomic, srptOrderForm, srptShipVia | R-reports-016, R-reports-013, R-reports-014, R-reports-012 | 1. Open Reports. 2. Choose the catalog; the date inputs are hidden. 3. Generate the catalog. 4. Check the table of contents. 5. Check the fixed pages and the order form. 6. Save as PDF. |

The scope keeps the invoice report plus at most four other reports. The four reports above
are this area's part of that. The invoice report and its workflow belong to the orders area.

## Services

| Name | Inputs | Outputs | Errors |
|---|---|---|---|
| sales_report_period | start date (optional), end date (optional) | start date, end date | no orders in the database to derive a default period from |
| sales_report | report kind, start date, end date, employee id (optional) | rows per period and employee or product, period subtotals, grand total, chart series | no data for the chosen period |
| product_catalog_pdf | none | catalog PDF, table of contents (category, starting page) | no catalog rows (warn, still render) |

## Lookups and relations

- `CompanyTypes.CompanyType` has copy_values true (rule R-reports-014). The catalog's order form finds the house company by its company-type code. That code is a literal in the design's criterion, so the synthetic data copies it from the design. No client-supplied codes are needed, and `values` is null.
- Relations the rules rely on:
  - `Orders.EmployeeID` (R-reports-004)
  - `OrderDetails.ProductID` (R-reports-005)
  - `Products.ProductCategoryID` (R-reports-011)

  All three are PROTECT: a salesperson, product or category that has sales cannot be deleted from under the reports.

## Open questions

| Id | Question | Status |
|---|---|---|
| Q-reports-001 | Besides the invoice, we propose keeping the monthly sales per employee, monthly sales per product, quarterly sales per product and product catalog reports, and dropping the employee email and phone lists. Confirm, or name the reports you would swap in. | open |
| Q-reports-002 | Order dates include a time of day, but the end date is compared at midnight. Orders placed on the end date after midnight are therefore missed, and with the default period that includes the latest orders themselves. Should the end date count the whole day (our recommendation), or must the current results be kept? | open |
| Q-reports-003 | The sales figures and the catalog's lifetime sales count orders of every status, including orders not yet invoiced or shipped. Is that intended? | open |
| Q-reports-004 | The quarterly report's chart is fed by the monthly figures. Its quarter labels put the quarter before the year, so a sort on the label would mix years. Should the chart use quarterly figures, sorted by year then quarter? | open |
| Q-reports-005 | The catalog is titled as a seasonal (fall) catalog and needs a full PDF render for its table of contents. Is one generated catalog enough, or do you need seasonal editions, and must generated catalogs be stored? | open |
| Q-reports-006 | The catalog shows a placeholder picture per category. Should it show the stored category images? | open |
| Q-reports-007 | A saved year-to-date sales per salesperson query (without discounts) is not used anywhere. May we drop it? | open |
