from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.decorators import business_required
from accounts.models import Notification


@login_required
@business_required
def notifications_list(request):
    """Список уведомлений."""
    notifications = Notification.objects.filter(
        business=request.business,
        user=request.user
    )[:50]

    data = [{
        'id': n.id,
        'type': n.type,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
    } for n in notifications]

    unread_count = Notification.objects.filter(
        business=request.business,
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'notifications': data,
        'unread_count': unread_count,
    })


@login_required
@business_required
@require_POST
def notification_mark_read(request, notification_id):
    """Пометить уведомление как прочитанное."""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            business=request.business,
            user=request.user
        )
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return JsonResponse({'ok': True})
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Не найдено'}, status=404)


@login_required
@business_required
@require_POST
def notifications_mark_all_read(request):
    """Пометить все уведомления как прочитанные."""
    count = Notification.objects.filter(
        business=request.business,
        user=request.user,
        is_read=False
    ).update(is_read=True)
    return JsonResponse({'ok': True, 'count': count})


def generate_notifications(business, user=None):
    """Генерация уведомлений на основе данных бизнеса."""
    from inventory.models import Product, Supply, Sale
    from django.db.models import Sum, F
    from django.utils import timezone
    from datetime import timedelta

    users = [user] if user else business.members.all()

    # Low stock
    low_products = Product.objects.filter(status='low')[:5]
    for product in low_products:
        key = f'low_stock_{product.id}'
        for u in users:
            if not Notification.objects.filter(business=business, user=u, key=key).exists():
                Notification.objects.create(
                    business=business,
                    user=u,
                    type='low_stock',
                    title=f'Низкий остаток: {product.name}',
                    message=f'Осталось {product.quantity} шт.',
                    key=key,
                )

    # Out of stock
    out_products = Product.objects.filter(status='out')[:5]
    for product in out_products:
        key = f'out_of_stock_{product.id}'
        for u in users:
            if not Notification.objects.filter(business=business, user=u, key=key).exists():
                Notification.objects.create(
                    business=business,
                    user=u,
                    type='out_of_stock',
                    title=f'Нет в наличии: {product.name}',
                    message='Товар закончился на складе',
                    key=key,
                )

    # Recent sales
    recent_sales = Sale.objects.filter(status='completed').order_by('-created_at')[:3]
    for sale in recent_sales:
        key = f'sale_{sale.id}'
        for u in users:
            if not Notification.objects.filter(business=business, user=u, key=key).exists():
                Notification.objects.create(
                    business=business,
                    user=u,
                    type='sale',
                    title=f'Продажа: {sale.product.name if sale.product else "Товар"}',
                    message=f'{sale.quantity} шт. на сумму {sale.total:,.0f} ₽',
                    key=key,
                )

    # Revenue summary (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    revenue = Sale.objects.filter(
        status='completed',
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    if revenue > 0:
        key = f'revenue_{timezone.now().strftime("%Y%m")}'
        for u in users:
            if not Notification.objects.filter(business=business, user=u, key=key).exists():
                Notification.objects.create(
                    business=business,
                    user=u,
                    type='revenue',
                    title=f'Выручка за месяц: {revenue:,.0f} ₽',
                    message='Обновлено автоматически',
                    key=key,
                )
