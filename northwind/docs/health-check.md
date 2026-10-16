# Health check: Northwind

An automated scan of the accdt source (12.3 MB). It counts the design (object names and counts only); it reads no data values.

## Size

| What | Count |
|---|---|
| Tables | 28 |
| Saved queries | 65 |
| Queries kept as a design grid | 63 |
| Queries kept as SQL text | 2 |
| Forms | 40 |
| Reports | 15 |
| VBA modules (standard and class) | 18 |
| Class modules | 1 |
| Macros (standalone) | 1 |
| Macros embedded in form and report events | 1 |
| Data macro files | 20 |
| Data macros | 20 |
| Forms and reports with code behind | 48 |
| VBA lines (non-blank) | 6,886 |

## Risk flags

- **VBA present**: 6,886 lines of VBA: Office blocks macros in files from the internet, so every copy must be trusted by hand.

## Complexity

**High** (6,886 VBA lines; 55 forms plus reports). High above 5,000 VBA lines or 40 screens and reports; medium above 1,000 lines or 20.

Largest objects by lines of code:

| Object | Type | Lines |
|---|---|---|
| frmOrderDetails | form | 562 |
| frmCompanyDetail | form | 550 |
| frmPurchaseOrderDetails | form | 478 |
| frmProductDetail | form | 476 |
| modGlobal | module | 368 |
| modRibbonCallback | module | 338 |
| modInventory | module | 293 |
| frmEmployeeList | form | 220 |
| sfrmOrderLineItems | form | 219 |
| modStrings | module | 186 |

## Effort and price band

| Offer | Hours | Price (USD) |
|---|---|---|
| Stage 2: the web app | 128.5 to 200.8 (point 160.6) | 16,800 to 26,200 (point 20,900) |
| Stage 1 alone: data off the Access file | 16.5 to 25.8 (point 20.6) | 2,200 to 3,400 (point 2,700) |

- Price band: **stage2-standard** (several modules, integrations), 18,000 to 35,000 USD for 110 to 200 hours.
- Stage 1 band: 2,000 to 5,000 USD for 12 to 30 hours.
- Rate 130 USD per hour. Starting coefficients, not measured; the assessment fixes the quote.

## Next step

Book the paid assessment (1,500 to 3,000 USD: inventory, keep/drop list, rules spec, fixed quote; credited toward the migration).

Or start with Stage 1 alone (move tables to Postgres or SQL Server, re-link the Access screens, backups): 2,200 to 3,400 USD for this app.
