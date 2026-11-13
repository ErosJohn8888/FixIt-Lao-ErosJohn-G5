from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("reports/", views.ReportView.as_view(), name="reports"),
    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customers/add/", views.CustomerCreateView.as_view(), name="customer_add"),
    path(
        "customers/<int:pk>/edit/",
        views.CustomerUpdateView.as_view(),
        name="customer_edit",
    ),
    path(
        "customers/<int:pk>/delete/",
        views.CustomerDeleteView.as_view(),
        name="customer_delete",
    ),
    path("devices/", views.DeviceListView.as_view(), name="device_list"),
    path("devices/add/", views.DeviceCreateView.as_view(), name="device_add"),
    path(
        "devices/<int:pk>/edit/",
        views.DeviceUpdateView.as_view(),
        name="device_edit",
    ),
    path(
        "devices/<int:pk>/delete/",
        views.DeviceDeleteView.as_view(),
        name="device_delete",
    ),
    path("repairs/", views.RepairListView.as_view(), name="repair_list"),
    path("repairs/add/", views.RepairCreateView.as_view(), name="repair_add"),
    path(
        "repairs/<int:pk>/",
        views.RepairDetailView.as_view(),
        name="repair_detail",
    ),
    path(
        "repairs/<int:pk>/edit/",
        views.RepairUpdateView.as_view(),
        name="repair_edit",
    ),
    path(
        "repairs/<int:pk>/delete/",
        views.RepairDeleteView.as_view(),
        name="repair_delete",
    ),
    path(
        "repairs/<int:repair_id>/diagnoses/add/",
        views.DiagnosisCreateView.as_view(),
        name="diagnosis_add",
    ),
    path(
        "diagnoses/<int:pk>/edit/",
        views.DiagnosisUpdateView.as_view(),
        name="diagnosis_edit",
    ),
    path(
        "diagnoses/<int:pk>/delete/",
        views.DiagnosisDeleteView.as_view(),
        name="diagnosis_delete",
    ),
    path(
        "repairs/<int:repair_id>/work/add/",
        views.RepairDetailCreateView.as_view(),
        name="work_add",
    ),
    path(
        "work/<int:pk>/edit/",
        views.RepairDetailUpdateView.as_view(),
        name="work_edit",
    ),
    path(
        "work/<int:pk>/delete/",
        views.RepairDetailDeleteView.as_view(),
        name="work_delete",
    ),
    path(
        "repairs/<int:repair_id>/parts/add/",
        views.RepairPartCreateView.as_view(),
        name="repair_part_add",
    ),
    path(
        "repair-parts/<int:pk>/edit/",
        views.RepairPartUpdateView.as_view(),
        name="repair_part_edit",
    ),
    path(
        "repair-parts/<int:pk>/delete/",
        views.RepairPartDeleteView.as_view(),
        name="repair_part_delete",
    ),
    path(
        "repairs/<int:repair_id>/payments/add/",
        views.PaymentCreateView.as_view(),
        name="payment_add",
    ),
    path(
        "payments/<int:pk>/edit/",
        views.PaymentUpdateView.as_view(),
        name="payment_edit",
    ),
    path(
        "payments/<int:pk>/delete/",
        views.PaymentDeleteView.as_view(),
        name="payment_delete",
    ),
    path(
        "repairs/<int:repair_id>/pickup/add/",
        views.PickupCreateView.as_view(),
        name="pickup_add",
    ),
    path(
        "pickups/<int:pk>/edit/",
        views.PickupUpdateView.as_view(),
        name="pickup_edit",
    ),
    path(
        "pickups/<int:pk>/delete/",
        views.PickupDeleteView.as_view(),
        name="pickup_delete",
    ),
    path("parts/", views.PartListView.as_view(), name="part_list"),
    path("parts/add/", views.PartCreateView.as_view(), name="part_add"),
    path("parts/<int:pk>/edit/", views.PartUpdateView.as_view(), name="part_edit"),
    path(
        "parts/<int:pk>/delete/",
        views.PartDeleteView.as_view(),
        name="part_delete",
    ),
]
