from django.urls import path
from . import views
from .exchange import exchange_rate_api

urlpatterns = [
    path('summary/', views.summary, name='api_analytics_summary'),
    path('sales/', views.sales_analytics, name='api_analytics_sales'),
    path('price-history/', views.price_history, name='api_price_history'),
    path('stock-alerts/', views.stock_alerts, name='api_stock_alerts'),
    path('stock-alerts/create/', views.stock_alert_create, name='api_stock_alert_create'),
    path('price-change/', views.price_change, name='api_price_change'),
    path('exchange-rate/', exchange_rate_api, name='api_exchange_rate'),
    # AI endpoints
    path('ai/analyze/', views.ai_analyze_sales, name='api_ai_analyze'),
    path('ai/forecast/', views.ai_forecast_stock, name='api_ai_forecast'),
    path('ai/report/', views.ai_generate_report, name='api_ai_report'),
    path('ai/chat/', views.ai_chat, name='api_ai_chat'),
    path('ai/config/', views.ai_config, name='api_ai_config'),
]
