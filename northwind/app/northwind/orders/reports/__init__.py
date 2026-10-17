"""Reports of the Orders, Invoicing and Shipping area: each kept report as an HTML
print view and an A4 PDF (django-weasyprint). The area keeps one report, the invoice
(rptInvoice, reports/invoice.py); the original did not export it to Excel, so it has
no xlsx export. Reports read through the area's queries and services, never their own
copy of the SQL."""
