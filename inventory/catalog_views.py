import json
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from inventory.models import Product, Category, Order


def catalog_view(request):
    """Public catalog page — served at subdomain root."""
    business = request.business
    if not business:
        from django.shortcuts import redirect
        return redirect('/landing/')

    ctx = {
        'business': business,
        'site_title': business.site_title or business.name,
        'site_description': business.site_description or f'Каталог товаров {business.name}',
        'site_phone': business.site_phone or '',
        'site_email': business.site_email or '',
        'site_address': business.site_address or '',
        'site_work_hours': business.site_work_hours or 'Пн–Пт, 9:00–18:00',
        'colors': _get_colors(business),
    }
    return render(request, 'catalog.html', ctx)


def _get_colors(business):
    """Get color scheme — defaults + user overrides."""
    defaults = {
        'paper': '#F7F3EC',
        'ink': '#241C15',
        'ink_soft': '#5B4F42',
        'tan': '#A97452',
        'cherry': '#B33A2E',
        'sage': '#7C8768',
        'line': '#DCD1BE',
        'card_bg': '#FFFFFF',
    }
    if business.site_color_scheme:
        defaults.update(business.site_color_scheme)
    return defaults


@csrf_exempt
def catalog_products_api(request):
    """Return products as JSON for the catalog frontend."""
    business = request.business
    if not business:
        return JsonResponse({'error': 'No business'}, status=400)

    products = Product.objects.using(request.db_alias).filter(
        quantity__gt=0
    ).select_related('category').order_by('-created_at')

    categories = Category.objects.using(request.db_alias).all().order_by('name')

    data = {
        'products': [_product_to_catalog(p) for p in products],
        'categories': [{'slug': c.slug, 'name': c.name, 'icon': c.icon} for c in categories],
    }
    return JsonResponse(data)


def _product_to_catalog(product):
    """Map Product model to catalog template format."""
    status_map = {'instock': 'in', 'low': 'low', 'out': 'out'}
    cf = product.custom_fields or {}
    return {
        'id': product.id,
        'name': product.name,
        'category': product.category.slug if product.category else 'other',
        'origin': product.country or '',
        'desc': cf.get('description', ''),
        'price': int(product.sale_price),
        'unit': cf.get('unit', 'шт'),
        'stock': status_map.get(product.status, 'out'),
        'roast': cf.get('roast', ''),
        'image': cf.get('image', ''),
    }


@csrf_exempt
@require_POST
def catalog_order_api(request):
    """Create an order from catalog cart."""
    business = request.business
    if not business:
        return JsonResponse({'error': 'No business'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    items = data.get('items', [])
    comment = data.get('comment', '').strip()
    email = data.get('email', '').strip()

    if not name or not phone:
        return JsonResponse({'error': 'Укажите имя и телефон'}, status=400)
    if not items:
        return JsonResponse({'error': 'Корзина пуста'}, status=400)

    total = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)

    order = Order.objects.create(
        business=business,
        customer_name=name,
        customer_phone=phone,
        customer_email=email,
        comment=comment,
        items=items,
        total=Decimal(str(total)),
        status='new',
    )

    return JsonResponse({
        'ok': True,
        'order_id': order.id,
        'total': float(order.total),
    })


@csrf_exempt
@require_POST
def generate_product_card(request, product_id):
    """Generate product card image — placeholder for AI integration."""
    business = request.business
    if not business:
        return JsonResponse({'error': 'No business'}, status=400)

    try:
        product = Product.objects.using(request.db_alias).get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)

    # Placeholder — returns product data for AI to generate image
    # User will connect their AI model to process this
    return JsonResponse({
        'ok': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'price': str(product.sale_price),
            'description': product.custom_fields.get('description', ''),
            'category': product.category.name if product.category else '',
        },
        'message': 'Подключите AI модель для генерации изображения',
        'image_url': product.custom_fields.get('image', ''),
    })
