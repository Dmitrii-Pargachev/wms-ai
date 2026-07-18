from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import business_required


@login_required
@business_required
def dashboard_view(request):
    # Generate notifications in background
    try:
        from accounts.notification_views import generate_notifications
        generate_notifications(request.business, request.user)
    except Exception:
        pass

    return render(request, 'dashboard/index.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'dashboard',
    })


@login_required
@business_required
def inventory_view(request):
    return render(request, 'dashboard/inventory.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'inventory',
    })


@login_required
@business_required
def supplies_view(request):
    return render(request, 'dashboard/supplies.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'supplies',
    })


@login_required
@business_required
def sales_view(request):
    return render(request, 'dashboard/sales.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'sales',
    })


@login_required
@business_required
def analytics_view(request):
    return render(request, 'dashboard/analytics.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'analytics',
    })


@login_required
@business_required
def reports_view(request):
    return render(request, 'dashboard/reports.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'reports',
    })


@login_required
@business_required
def settings_view(request):
    return render(request, 'dashboard/settings.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'settings',
    })


@login_required
@business_required
def logs_view(request):
    return render(request, 'dashboard/logs.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'logs',
    })


@login_required
@business_required
def constructor_view(request):
    return render(request, 'dashboard/constructor.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'constructor',
    })


@login_required
@business_required
def clients_view(request):
    return render(request, 'dashboard/clients.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'clients',
    })
