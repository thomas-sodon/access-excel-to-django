"""The product list download (R-inventory-024): one row per product sorted by name
with its number, code and name, allocated quantity, quantity to sell, on-order
quantity, reorder level, target level, minimum reorder quantity and discontinued
flag. It replaces the Access spreadsheet export (Q-inventory-004).

The workbook is written from scratch with openpyxl, in memory.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

from northwind.inventory.saved_queries import product_list_export_rows

#: The export's column headings, as the original query names its columns.
HEADINGS = (
    "Product ID",
    "Product Code",
    "Product",
    "Allocated Inventory",
    "Inventory To Sell",
    "Qty On Order",
    "Reorder Level",
    "Target Level",
    "Min Reorder Qty",
    "Discontinued",
)
SHEET_TITLE = "Products"
FILENAME = "product-list.xlsx"
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
WIDTHS = {"A": 11, "B": 16, "C": 40}


def build_workbook(rows: list[tuple] | None = None) -> Workbook:
    """The export as an openpyxl workbook: a heading row, then one row per product."""
    if rows is None:
        rows = product_list_export_rows()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = SHEET_TITLE
    sheet.append(HEADINGS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(list(row))
    for column, width in WIDTHS.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"
    return workbook


def workbook_bytes(rows: list[tuple] | None = None) -> bytes:
    """The export as .xlsx bytes."""
    buffer = BytesIO()
    build_workbook(rows).save(buffer)
    return buffer.getvalue()
