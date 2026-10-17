"""URLs of the Sales and Catalog Reports area, mounted at /reports/ by the overlay.

The contract names one URL per kept form, form_<file-safe id>, and one per kept
report, report_<file-safe id> (docs/contracts.md#feature-app-contract). Every report
URL returns an A4 PDF with ?format=pdf.
"""

from django.urls import path

from . import services
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportSelectionView.as_view(), name="form_frmReports"),
    path(
        "sales-by-employee/",
        views.SalesReportView.as_view(report_name=services.SALES_BY_EMPLOYEE),
        name="report_rptSalesByEmployee",
    ),
    path(
        "sales-by-product/",
        views.SalesReportView.as_view(report_name=services.SALES_BY_PRODUCT),
        name="report_rptSalesByProduct",
    ),
    path(
        "sales-by-product-quarterly/",
        views.SalesReportView.as_view(report_name=services.SALES_BY_PRODUCT_QUARTERLY),
        name="report_rptSalesByProductQuarterly",
    ),
    path(
        "product-catalog/",
        views.CatalogView.as_view(),
        name="report_rptProductCatalog",
    ),
    path(
        "product-catalog/contents/",
        views.CatalogPartView.as_view(part="toc", source="srptCatalog_TableOfContents"),
        name="report_srptCatalog_TableOfContents",
    ),
    path(
        "product-catalog/quality/",
        views.CatalogPartView.as_view(part="quality", source="srptQuality"),
        name="report_srptQuality",
    ),
    path(
        "product-catalog/gastronomic/",
        views.CatalogPartView.as_view(part="gastronomic", source="srptGastronomic"),
        name="report_srptGastronomic",
    ),
    path(
        "product-catalog/order-form/",
        views.CatalogPartView.as_view(part="order-form", source="srptOrderForm"),
        name="report_srptOrderForm",
    ),
    path(
        "product-catalog/ship-via/",
        views.CatalogPartView.as_view(part="ship-via", source="srptShipVia"),
        name="report_srptShipVia",
    ),
]
