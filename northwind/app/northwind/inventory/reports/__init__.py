"""Reports and exports of the Products and Inventory area.

The area keeps no Access report. Its one export is the product list download
(R-inventory-024), an .xlsx written with openpyxl from the rows of the
qryProductList_Export saved query (saved_queries.product_list_export_rows), never
from a copy of its SQL.
"""
