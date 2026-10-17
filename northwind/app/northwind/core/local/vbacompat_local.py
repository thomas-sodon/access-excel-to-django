"""Northwind's own Access functions for core/vbacompat.py lookup().

The kept queries and reports call these Access built-ins, all in core/vbacompat.py:
Format (with the custom date formats "yyyy-mm", "mmm-yyyy" and "q-yyyy"), Nz,
DateValue, Year, CDbl, Space, String, IIf, Date, Now and Time.

They also call functions the original application defines itself. Those read the
database, so they are services of the feature areas, not Access functions, and none
of them is registered here:

- ProductAllocated, ProductNoStock, ProductOnOrder, ProductToSell: stock figures of
  a product (inventory area; R-inventory-004, R-inventory-006).
- Get_UserID: the signed-in employee (the foundation's sign-in; the areas read the
  request's user).
- reportParameterStartDate, reportParameterEndDate: the date range of the sales
  reports (reports area; the report form's parameters).
- GetString, GetNorthwindAddress: text from the Strings table and the trading
  company's address (reports area).

FUNCTIONS maps an Access name to a Python function; lookup() lets these win over the
built-ins.
"""

FUNCTIONS: dict = {}
