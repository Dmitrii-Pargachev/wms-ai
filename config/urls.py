from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import redirect
from accounts.views import verify_email_view

def health_check(request):
    return JsonResponse({'status': 'ok', 'version': '2.1', 'verify_email': 'enabled'})

def dashboard_redirect(request, path=''):
    """Redirect /dashboard/* to /system/*"""
    return redirect(f'/system/{path}')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('verify-email/<str:token>/', verify_email_view, name='verify_email_direct'),
    path('', include('accounts.urls')),
    # /system/ prefix — WMS dashboard
    path('system/', include('inventory.urls_dashboard')),
    # Backward compat: /dashboard/* → /system/*
    path('dashboard/<path:path>', dashboard_redirect),
    path('dashboard/', dashboard_redirect),
    # API
    path('api/', include('inventory.urls_api')),
    path('api/analytics/', include('analytics.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/integrations/', include('integrations.urls')),
    # /new/ prefix URLs (production behind Nginx)
    path('new/', include('accounts.urls')),
    path('new/verify-email/<str:token>/', verify_email_view, name='verify_email_new'),
    path('new/system/', include('inventory.urls_dashboard')),
    path('new/api/', include('inventory.urls_api')),
    path('new/api/analytics/', include('analytics.urls')),
    path('new/api/reports/', include('reports.urls')),
    path('new/api/integrations/', include('integrations.urls')),
]
