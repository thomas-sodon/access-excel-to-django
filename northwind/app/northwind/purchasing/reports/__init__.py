"""Reports of the Purchasing and receiving area.

The area keeps no report of the original (analysis/rules.json: the area's reports
list is empty). The printable purchase order (views.PurchaseOrderPrintView, A4 PDF
through django-weasyprint) uses the area's querysets and services, never its own
copy of the SQL.
"""
