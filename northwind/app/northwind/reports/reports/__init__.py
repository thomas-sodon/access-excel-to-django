"""Reports of the Sales and Catalog Reports area: each kept report as an HTML print
view and an A4 PDF (django-weasyprint). The original's reports did not export to
Excel, so there is no xlsx export. Reports use the area's saved queries and services,
never their own copy of the SQL.

- pdf.py: the PDF response and the page layout with local static files.
- catalog.py: the two-pass catalog layout that fills the table of contents.
"""
