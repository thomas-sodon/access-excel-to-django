"""URLs of the Purchasing and receiving area, mounted at /purchasing/ by the overlay.

One URL per kept form, named form_<file-safe id> (docs/contracts.md#feature-app-
contract): form_frmPurchaseOrderList, form_frmPurchaseOrderDetails,
form_sfrmPurchaseOrderLineItems, form_frmSelectVendorDialog and
form_sfrmCompanyDetail_VendorPurchaseOrders. The area keeps no reports.
"""

from django.urls import path

from . import views

app_name = "purchasing"

urlpatterns = [
    path(
        "",
        views.PurchaseOrderListView.as_view(),
        name="form_frmPurchaseOrderList",
    ),
    path("new/", views.PurchaseOrderCreateView.as_view(), name="create"),
    path(
        "<int:pk>/",
        views.PurchaseOrderDetailView.as_view(),
        name="form_frmPurchaseOrderDetails",
    ),
    path("<int:pk>/edit/", views.PurchaseOrderUpdateView.as_view(), name="update"),
    path("<int:pk>/submit/", views.SubmitView.as_view(), name="submit"),
    path("<int:pk>/approve/", views.ApproveView.as_view(), name="approve"),
    path("<int:pk>/receive/", views.ReceiveView.as_view(), name="receive"),
    path("<int:pk>/close/", views.CloseView.as_view(), name="close"),
    path("<int:pk>/delete/", views.DeleteView.as_view(), name="delete"),
    path(
        "<int:pk>/add-no-stock/",
        views.AddNoStockView.as_view(),
        name="add_no_stock",
    ),
    path("<int:pk>/print/", views.PurchaseOrderPrintView.as_view(), name="print"),
    path(
        "<int:pk>/lines/",
        views.LineItemsView.as_view(),
        name="form_sfrmPurchaseOrderLineItems",
    ),
    path("<int:pk>/lines/add/", views.LineAddView.as_view(), name="line_add"),
    path(
        "<int:pk>/lines/defaults/",
        views.LineDefaultsView.as_view(),
        name="line_defaults",
    ),
    path("lines/<int:pk>/edit/", views.LineUpdateView.as_view(), name="line_update"),
    path(
        "lines/<int:pk>/delete/",
        views.LineDeleteView.as_view(),
        name="line_delete",
    ),
    path(
        "select-vendor/<int:pk>/",
        views.SelectVendorView.as_view(),
        name="form_frmSelectVendorDialog",
    ),
    path(
        "vendor/<int:pk>/",
        views.VendorPurchaseOrdersView.as_view(),
        name="form_sfrmCompanyDetail_VendorPurchaseOrders",
    ),
]
