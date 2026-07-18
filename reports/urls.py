from django.urls import path
from . import views

urlpatterns = [
    path('sales/', views.sales_report, name='api_report_sales'),
    path('inventory/', views.inventory_report, name='api_report_inventory'),
    path('export/sales.html/', views.export_sales_html, name='report_export_sales'),
    path('export/sales.pdf/', views.export_sales_pdf, name='report_export_sales_pdf'),
    path('export/inventory.pdf/', views.export_inventory_pdf, name='report_export_inventory_pdf'),
]
