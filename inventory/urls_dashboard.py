from django.urls import path
from . import dashboard_views
from inventory import order_views, ai_views

urlpatterns = [
    path('', dashboard_views.dashboard_view, name='dashboard'),
    path('inventory/', dashboard_views.inventory_view, name='inventory'),
    path('supplies/', dashboard_views.supplies_view, name='supplies'),
    path('sales/', dashboard_views.sales_view, name='sales'),
    path('analytics/', dashboard_views.analytics_view, name='analytics'),
    path('reports/', dashboard_views.reports_view, name='reports'),
    path('settings/', dashboard_views.settings_view, name='settings'),
    path('logs/', dashboard_views.logs_view, name='logs'),
    path('constructor/', dashboard_views.constructor_view, name='constructor'),
    path('clients/', dashboard_views.clients_view, name='clients'),
    path('orders/', order_views.orders_view, name='orders'),
    path('ai/', ai_views.ai_generate_view, name='ai_generate'),
]
