import json
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from accounts.decorators import business_required
from inventory.models import Order


@login_required
@business_required
def orders_view(request):
    """Orders management page."""
    return render(request, 'dashboard/orders.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'orders',
    })


@login_required
@business_required
def orders_api(request):
    """List orders with optional status filter."""
    status = request.GET.get('status', '')
    orders = Order.objects.filter(business=request.business)
    if status:
        orders = orders.filter(status=status)
    orders = orders.order_by('-created_at')[:100]

    data = [{
        'id': o.id,
        'customer_name': o.customer_name,
        'customer_phone': o.customer_phone,
        'customer_email': o.customer_email,
        'comment': o.comment,
        'items': o.items,
        'total': float(o.total),
        'status': o.status,
        'status_display': o.get_status_display(),
        'created_at': o.created_at.strftime('%d.%m.%Y %H:%M'),
    } for o in orders]
    return JsonResponse({'orders': data})


@csrf_exempt
@login_required
@business_required
@require_POST
def order_update_status(request, order_id):
    """Update order status. Deduct stock when moving to 'processing'."""
    try:
        order = Order.objects.get(id=order_id, business=request.business)
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status not in ('new', 'processing', 'completed'):
            return JsonResponse({'error': 'Неверный статус'}, status=400)

        old_status = order.status
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

        # Новый → В работе: списать со склада, создать продажи
        if new_status == 'processing' and old_status == 'new':
            order.deduct_stock()

        # В работе → Выполнен: завершить продажи
        if new_status == 'completed' and old_status == 'processing':
            order.complete_sales()

        return JsonResponse({'ok': True, 'status': order.status})
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Заказ не найден'}, status=404)
