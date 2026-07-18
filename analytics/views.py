import json
from datetime import timedelta
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from accounts.decorators import business_required
from accounts.models import Log
from inventory.models import Product, Supply, Sale
from .models import PriceHistory, StockAlert


@login_required
@business_required
def summary(request):
    """Сводка по складу для дашборда."""
    from inventory.models import Product, Supply, Sale

    products = Product.objects.filter(business=request.business)
    supplies = Supply.objects.filter(business=request.business, status='received')
    sales = Sale.objects.filter(business=request.business, status='completed')

    # Product stats
    total_products = products.count()
    in_stock = products.filter(status='instock').count()
    low_stock = products.filter(status='low').count()
    out_of_stock = products.filter(status='out').count()

    # Supply stats
    total_supplies = supplies.count()
    recent_supplies = supplies.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).count()

    # Sales stats
    total_sales = sales.count()
    recent_sales = sales.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).count()

    # Revenue
    total_revenue = sales.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    recent_revenue = sales.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    # Average check
    avg_check = sales.aggregate(avg=Avg(F('price') * F('quantity')))['avg'] or 0

    return JsonResponse({
        'products': {
            'total': total_products,
            'in_stock': in_stock,
            'low': low_stock,
            'out': out_of_stock,
        },
        'supplies': {
            'total': total_supplies,
            'recent_30d': recent_supplies,
        },
        'sales': {
            'total': total_sales,
            'recent_30d': recent_sales,
        },
        'revenue': {
            'total': float(total_revenue),
            'recent_30d': float(recent_revenue),
            'avg_check': float(avg_check),
        },
    })


@login_required
@business_required
def sales_analytics(request):
    """Аналитика продаж по периодам."""
    period = request.GET.get('period', 'week')

    now = timezone.now()
    if period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now - timedelta(days=30)
    elif period == 'quarter':
        start = now - timedelta(days=90)
    else:
        start = now - timedelta(days=7)

    sales = Sale.objects.filter(
        business=request.business,
        status='completed',
        created_at__gte=start
    )
    daily_sales = []
    from datetime import datetime
    current = start.date()
    end = now.date()

    while current <= end:
        day_sales = sales.filter(date=current)
        revenue = day_sales.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        count = day_sales.count()

        daily_sales.append({
            'date': current.strftime('%d.%m'),
            'revenue': float(revenue),
            'count': count,
        })
        current += timedelta(days=1)

    # Top products
    top_products = sales.values('product__name').annotate(
        total=Sum(F('price') * F('quantity')),
        count=Count('id')
    ).order_by('-total')[:5]

    # Sales by category
    by_category = sales.values('product__category__name').annotate(
        total=Sum(F('price') * F('quantity')),
        count=Count('id')
    ).order_by('-total')

    return JsonResponse({
        'period': period,
        'daily': daily_sales,
        'top_products': list(top_products),
        'by_category': list(by_category),
    })


@login_required
@business_required
def price_history(request):
    """История цен товара."""
    product_id = request.GET.get('product_id')

    if not product_id:
        return JsonResponse({'error': 'product_id required'}, status=400)

    history = PriceHistory.objects.filter(
        product_id=product_id
    ).select_related('changed_by')[:50]

    data = []
    for h in history:
        data.append({
            'id': h.id,
            'price_type': h.price_type,
            'price_type_display': h.get_price_type_display(),
            'old_price': float(h.old_price),
            'new_price': float(h.new_price),
            'difference': float(h.difference),
            'percent_change': h.percent_change,
            'changed_by': h.changed_by.username if h.changed_by else '',
            'created_at': h.created_at.strftime('%d.%m.%Y %H:%M'),
        })

    return JsonResponse({'history': data})


@login_required
@business_required
def stock_alerts(request):
    """Товары с низким остатком."""
    alerts = StockAlert.objects.filter(
        is_active=True
    ).select_related('product')

    data = []
    for alert in alerts:
        product = alert.product
        if product.quantity <= alert.threshold:
            data.append({
                'id': alert.id,
                'product_id': product.id,
                'product_name': product.name,
                'quantity': product.quantity,
                'threshold': alert.threshold,
            })

    return JsonResponse({'alerts': data})


@login_required
@business_required
@require_POST
def stock_alert_create(request):
    """Создать оповещение о низком остатке."""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        threshold = data.get('threshold', 5)

        if not product_id:
            return JsonResponse({'error': 'product_id required'}, status=400)

        from inventory.models import Product
        product = Product.objects.get(pk=product_id, business=request.business)

        alert, created = StockAlert.objects.get_or_create(
            product=product,
            defaults={'threshold': threshold}
        )

        if not created:
            alert.threshold = threshold
            alert.save(update_fields=['threshold'])

        return JsonResponse({'ok': True, 'id': alert.id})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
@require_POST
def price_change(request):
    """Изменить цену товара с логированием."""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        price_type = data.get('price_type')  # 'purchase' or 'sale'
        new_price = data.get('new_price')

        if not product_id or not price_type or new_price is None:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        from inventory.models import Product
        product = Product.objects.get(pk=product_id, business=request.business)

        if price_type == 'purchase':
            old_price = product.purchase_price
            product.purchase_price = new_price
        elif price_type == 'sale':
            old_price = product.sale_price
            product.sale_price = new_price
        else:
            return JsonResponse({'error': 'Invalid price_type'}, status=400)

        product.save()

        # Log price change
        PriceHistory.objects.create(
            product=product,
            price_type=price_type,
            old_price=old_price,
            new_price=new_price,
            changed_by=request.user,
        )

        from accounts.models import Log
        type_label = 'Закупка' if price_type == 'purchase' else 'Продажа'
        Log.log(request.business, 'price', f'Изменение цены ({type_label}): {product.name} ({product.article}) — {int(old_price)}₽ → {int(float(new_price))}₽', request.user)

        return JsonResponse({'ok': True})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============ AI Endpoints ============

@login_required
@business_required
def ai_config(request):
    """Проверить конфигурацию AI."""
    from .ai_service import get_ai_service
    ai = get_ai_service(request.business.slug)
    return JsonResponse({
        'configured': ai.is_configured(),
        'model': ai.model if ai.is_configured() else None,
    })


@login_required
@business_required
@require_POST
def ai_analyze_sales(request):
    """AI-анализ продаж."""
    from .ai_service import get_ai_service

    ai = get_ai_service(request.business.slug)
    if not ai.is_configured():
        return JsonResponse({
            'error': 'AI не настроен. Добавьте POLZA_API_KEY в настройки бизнеса.'
        }, status=400)

    # Gather sales data
    now = timezone.now()
    start = now - timedelta(days=30)

    sales = Sale.objects.filter(business=request.business, status='completed', created_at__gte=start)
    top_products = list(sales.values('product__name').annotate(
        total=Sum(F('price') * F('quantity')),
        count=Count('id')
    ).order_by('-total')[:5])

    sales_data = {
        'revenue': float(sales.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0),
        'count': sales.count(),
        'avg_check': float(sales.aggregate(avg=Avg(F('price') * F('quantity')))['avg'] or 0),
        'top_products': top_products,
    }

    result = ai.analyze_sales(sales_data)
    if result:
        return JsonResponse({'ok': True, 'analysis': result})
    else:
        return JsonResponse({'error': 'AI не ответил. Проверьте настройки.'}, status=500)


@login_required
@business_required
@require_POST
def ai_forecast_stock(request):
    """AI-прогноз остатков."""
    from .ai_service import get_ai_service

    ai = get_ai_service(request.business.slug)
    if not ai.is_configured():
        return JsonResponse({
            'error': 'AI не настроен.'
        }, status=400)

    products = Product.objects.filter(business=request.business).values(
        'name', 'article', 'quantity', 'status', 'category__name'
    )[:20]

    result = ai.forecast_stock(list(products))
    if result:
        return JsonResponse({'ok': True, 'forecast': result})
    else:
        return JsonResponse({'error': 'AI не ответил.'}, status=500)


@login_required
@business_required
@require_POST
def ai_generate_report(request):
    """AI-генерация отчёта."""
    from .ai_service import get_ai_service

    ai = get_ai_service(request.business.slug)
    if not ai.is_configured():
        return JsonResponse({
            'error': 'AI не настроен.'
        }, status=400)

    try:
        data = json.loads(request.body)
        report_type = data.get('type', 'sales')

        now = timezone.now()
        start = now - timedelta(days=30)

        if report_type == 'sales':
            sales = Sale.objects.filter(business=request.business, status='completed', created_at__gte=start)
            report_data = {
                'revenue': float(sales.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0),
                'count': sales.count(),
                'avg_check': float(sales.aggregate(avg=Avg(F('price') * F('quantity')))['avg'] or 0),
            }
        else:
            products = Product.objects.filter(business=request.business)
            report_data = {
                'total': products.count(),
                'total_value': float(products.aggregate(total=Sum(F('purchase_price') * F('quantity')))['total'] or 0),
            }

        result = ai.generate_report(report_data, report_type)
        if result:
            return JsonResponse({'ok': True, 'report': result})
        else:
            return JsonResponse({'error': 'AI не ответил.'}, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
@require_POST
def ai_chat(request):
    """Чат с AI."""
    from .ai_service import get_ai_service

    ai = get_ai_service(request.business.slug)
    if not ai.is_configured():
        return JsonResponse({
            'error': 'AI не настроен.'
        }, status=400)

    try:
        data = json.loads(request.body)
        message = data.get('message', '')

        if not message:
            return JsonResponse({'error': 'Введите сообщение'}, status=400)

        # Context about the business
        products_count = Product.objects.filter(business=request.business).count()
        sales_count = Sale.objects.filter(business=request.business, status='completed').count()

        context = {
            'товаров_на_складе': products_count,
            'продаж_всего': sales_count,
        }

        result = ai.chat(message, context)
        if result:
            return JsonResponse({'ok': True, 'response': result})
        else:
            return JsonResponse({'error': 'AI не ответил.'}, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
