"""URLs of the Products and Inventory area, mounted at /inventory/ by the overlay.

The contract names one URL per kept form, form_<id> (docs/contracts.md#feature-app-
contract); the area keeps no report. The other routes are the product page's actions
and the category maintenance screens.
"""

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="form_frmProductList"),
    path("export.xlsx", views.ProductExportView.as_view(), name="product_export"),
    path("products/new/", views.ProductCreateView.as_view(), name="product_create"),
    path(
        "products/<int:pk>/",
        views.ProductDetailView.as_view(),
        name="form_frmProductDetail",
    ),
    path(
        "products/<int:pk>/edit/",
        views.ProductUpdateView.as_view(),
        name="product_update",
    ),
    path(
        "products/<int:pk>/delete/",
        views.ProductDeleteView.as_view(),
        name="product_delete",
    ),
    path(
        "products/<int:pk>/reorder/",
        views.ProductReorderView.as_view(),
        name="product_reorder",
    ),
    path(
        "products/<int:pk>/orders/",
        views.ProductOrdersView.as_view(),
        name="form_sfrmProductDetail_Orders",
    ),
    path(
        "products/<int:pk>/purchase-orders/",
        views.ProductPurchaseOrdersView.as_view(),
        name="form_sfrmProductDetail_PurchaseOrders",
    ),
    path(
        "products/<int:pk>/stock-takes/",
        views.StockTakeView.as_view(),
        name="form_sfrmProductDetail_StockTake",
    ),
    path(
        "products/<int:pk>/vendors/",
        views.VendorsView.as_view(),
        name="form_sfrmProductDetail_Vendors",
    ),
    path(
        "products/<int:pk>/vendors/<int:link>/remove/",
        views.VendorRemoveView.as_view(),
        name="product_vendor_remove",
    ),
    path(
        "categories/",
        views.CategoryListView.as_view(),
        name="form_sfrmProductCategories",
    ),
    path(
        "categories/new/",
        views.CategoryCreateView.as_view(),
        name="category_create",
    ),
    path(
        "categories/<int:pk>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category_update",
    ),
    path(
        "categories/<int:pk>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
]
