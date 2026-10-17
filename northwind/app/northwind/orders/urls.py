"""URLs of the Orders, Invoicing and Shipping area, mounted at /orders/ by the overlay.

Each kept form of the area has a URL named form_<form> and the kept report
report_rptInvoice (docs/contracts.md#feature-app-contract). frmLogin and frmCredentials
are the foundation's sign-in; their URLs here are the landing page after sign-in (the
order list, R-orders-050) and the signed-in user's employee record.
sfrmEmployee_Privileges is the employee's privilege grants.
"""

from django.urls import path

from . import views
from .reports.invoice import InvoiceView

app_name = "orders"

urlpatterns = [
    # Orders
    path("", views.OrderListView.as_view(), name="form_frmOrderList"),
    path("start/", views.StartView.as_view(), name="form_frmLogin"),
    path("new/", views.OrderCreateView.as_view(), name="order_create"),
    path("<int:pk>/", views.OrderDetailView.as_view(), name="form_frmOrderDetails"),
    path("<int:pk>/edit/", views.OrderUpdateView.as_view(), name="order_update"),
    path("<int:pk>/delete/", views.OrderDeleteView.as_view(), name="order_delete"),
    path(
        "<int:pk>/action/<slug:verb>/",
        views.OrderActionView.as_view(),
        name="order_action",
    ),
    path("<int:pk>/invoice/", InvoiceView.as_view(), name="report_rptInvoice"),
    path(
        "<int:pk>/lines/",
        views.OrderLinesView.as_view(),
        name="form_sfrmOrderLineItems",
    ),
    path(
        "<int:pk>/lines/<int:line>/edit/",
        views.OrderLineUpdateView.as_view(),
        name="order_line_update",
    ),
    path(
        "<int:pk>/lines/<int:line>/delete/",
        views.OrderLineDeleteView.as_view(),
        name="order_line_delete",
    ),
    # Companies
    path("companies/", views.CompanyListView.as_view(), name="form_frmCompanyList"),
    path("companies/new/", views.CompanyCreateView.as_view(), name="company_create"),
    path(
        "companies/<int:pk>/",
        views.CompanyDetailView.as_view(),
        name="form_frmCompanyDetail",
    ),
    path(
        "companies/<int:pk>/edit/",
        views.CompanyUpdateView.as_view(),
        name="company_update",
    ),
    path(
        "companies/<int:pk>/delete/",
        views.CompanyDeleteView.as_view(),
        name="company_delete",
    ),
    path(
        "companies/<int:pk>/contacts/",
        views.CompanyContactsView.as_view(),
        name="form_sfrmCompanyDetail_Contacts",
    ),
    path(
        "companies/<int:pk>/customer-orders/",
        views.CompanyOrdersView.as_view(),
        name="form_sfrmCompanyDetail_CustomerOrders",
    ),
    path(
        "companies/<int:pk>/shipper-orders/",
        views.ShipperOrdersView.as_view(),
        name="form_sfrmCompanyDetail_ShipperOrders",
    ),
    path(
        "contacts/<int:pk>/edit/",
        views.ContactUpdateView.as_view(),
        name="contact_update",
    ),
    path(
        "contacts/<int:pk>/delete/",
        views.ContactDeleteView.as_view(),
        name="contact_delete",
    ),
    # Employees
    path("employees/", views.EmployeeListView.as_view(), name="form_frmEmployeeList"),
    path("employees/new/", views.EmployeeCreateView.as_view(), name="employee_create"),
    path(
        "employees/<int:pk>/",
        views.EmployeeDetailView.as_view(),
        name="employee_detail",
    ),
    path(
        "employees/<int:pk>/edit/",
        views.EmployeeUpdateView.as_view(),
        name="employee_update",
    ),
    path(
        "employees/<int:pk>/delete/",
        views.EmployeeDeleteView.as_view(),
        name="employee_delete",
    ),
    path(
        "employees/<int:pk>/recent-orders/",
        views.RecentOrdersView.as_view(),
        name="form_sfrmOrders_MostRecent_ByEmployee",
    ),
    path(
        "employees/<int:pk>/privileges/",
        views.EmployeePrivilegesView.as_view(),
        name="form_sfrmEmployee_Privileges",
    ),
    path(
        "privileges/<int:pk>/revoke/",
        views.PrivilegeRevokeView.as_view(),
        name="privilege_revoke",
    ),
    path("titles/new/", views.TitleCreateView.as_view(), name="form_frmEmployeeTitles"),
    path("credentials/", views.CredentialsView.as_view(), name="form_frmCredentials"),
]
