import json
import uuid
from pathlib import Path
from datetime import timedelta, timezone as dt_timezone
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
from django.utils import timezone as django_tz
from accounts.decorators import business_required
from accounts.models import Log
from .models import Category, Supplier, Product, Supply, Sale

# Timezone offsets in hours from UTC
TZ_OFFSETS = {
    'Europe/Kaliningrad': 2,
    'Europe/Moscow': 3,
    'Europe/Samara': 4,
    'Asia/Yekaterinburg': 5,
    'Asia/Omsk': 6,
    'Asia/Krasnoyarsk': 7,
    'Asia/Irkutsk': 8,
    'Asia/Yakutsk': 9,
    'Asia/Vladivostok': 10,
    'Asia/Kamchatka': 12,
}

def _fmt_dt(dt, request, fmt='%d.%m.%Y %H:%M'):
    """Format datetime with user's timezone from cookie."""
    if not dt:
        return ''
    tz_name = request.COOKIES.get('wms_timezone', 'Europe/Moscow')
    offset = TZ_OFFSETS.get(tz_name, 3)
    return (dt + timedelta(hours=offset)).strftime(fmt)


# ============ Categories ============

@login_required
@business_required
def categories_list(request):
    """Список категорий."""
    categories = Category.objects.filter(business=request.business).values('id', 'name', 'slug', 'icon')
    return JsonResponse({'categories': list(categories), 'total': len(categories)})


@login_required
@business_required
@require_POST
def category_create(request):
    """Создать категорию."""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip().lower()
        icon = data.get('icon', '')

        if not name:
            return JsonResponse({'error': 'Введите название'}, status=400)

        if not slug:
            slug = name.lower().replace(' ', '-')

        if Category.objects.filter(business=request.business, slug=slug).exists():
            return JsonResponse({'error': 'Категория с таким URL уже существует'}, status=400)

        category = Category.objects.create(business=request.business, name=name, slug=slug, icon=icon)

        Log.log(request.business, 'settings', f'Создана категория: {icon} {name}', request.user)

        return JsonResponse({'ok': True, 'id': category.id, 'name': category.name})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
@require_POST
def category_delete(request, pk):
    """Удалить категорию."""
    try:
        category = Category.objects.get(pk=pk, business=request.business)
        name = category.name
        category.delete()

        Log.log(request.business, 'settings', f'Удалена категория: {name}', request.user)

        return JsonResponse({'ok': True})
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Категория не найдена'}, status=404)


# ============ Suppliers ============

@login_required
@business_required
def suppliers_list(request):
    """Список поставщиков."""
    search = request.GET.get('search', '')
    suppliers = Supplier.objects.filter(business=request.business)

    if search:
        suppliers = suppliers.filter(
            Q(name__icontains=search) | Q(phone__icontains=search)
        )

    data = list(suppliers.values('id', 'name', 'contact', 'phone'))
    return JsonResponse({'suppliers': data, 'total': len(data)})


@login_required
@business_required
@require_POST
def supplier_create(request):
    """Создать поставщика."""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        contact = data.get('contact', '').strip()
        phone = data.get('phone', '').strip()

        if not name:
            return JsonResponse({'error': 'Введите название'}, status=400)

        if Supplier.objects.filter(business=request.business, name=name).exists():
            return JsonResponse({'error': 'Поставщик с таким названием уже существует'}, status=400)

        supplier = Supplier.objects.create(business=request.business, name=name, contact=contact, phone=phone)

        Log.log(request.business, 'settings', f'Добавлен поставщик: {name}', request.user)

        return JsonResponse({'ok': True, 'id': supplier.id, 'name': supplier.name})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============ Products ============

@login_required
@business_required
def products_list(request):
    """Список товаров с поиском и фильтрами."""
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))

    products = Product.objects.filter(business=request.business).select_related('category')

    if search:
        products = products.filter(
            Q(name__icontains=search) | Q(article__icontains=search)
        )

    if category:
        products = products.filter(category__slug=category)

    if status:
        products = products.filter(status=status)

    total = products.count()
    products = products[(page - 1) * per_page: page * per_page]

    data = []
    for p in products:
        data.append({
            'id': p.id,
            'article': p.article,
            'name': p.name,
            'category': p.category.name if p.category else '',
            'category_slug': p.category.slug if p.category else '',
            'country': p.country,
            'purchase_price': float(p.purchase_price),
            'sale_price': float(p.sale_price),
            'quantity': p.quantity,
            'status': p.status,
            'status_display': p.get_status_display(),
            'created_at': p.created_at.strftime('%d.%m.%Y'),
        })

    return JsonResponse({
        'products': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    })


@login_required
@business_required
@require_POST
def product_create(request):
    """Создать товар."""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        article = data.get('article', '').strip()
        category_id = data.get('category_id')
        country = data.get('country', '').strip()
        purchase_price = data.get('purchase_price', 0)
        sale_price = data.get('sale_price', 0)

        if not name:
            return JsonResponse({'error': 'Введите название'}, status=400)

        if article and Product.objects.filter(business=request.business, article=article).exists():
            return JsonResponse({'error': 'Товар с таким артикулом уже существует'}, status=400)

        category = None
        if category_id:
            try:
                category = Category.objects.get(pk=category_id, business=request.business)
            except Category.DoesNotExist:
                pass

        product = Product.objects.create(
            business=request.business,
            name=name,
            article=article,
            category=category,
            country=country,
            purchase_price=purchase_price,
            sale_price=sale_price,
            custom_fields=data.get('custom_fields', {}),
        )

        Log.log(request.business, 'stock', f'Добавлен товар: {name} ({article})', request.user)

        return JsonResponse({'ok': True, 'id': product.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
def product_detail(request, pk):
    """Получить товар по ID."""
    try:
        product = Product.objects.select_related('category').get(pk=pk, business=request.business)
        return JsonResponse({
            'id': product.id,
            'article': product.article,
            'name': product.name,
            'category_id': product.category_id,
            'category': product.category.name if product.category else '',
            'country': product.country,
            'purchase_price': float(product.purchase_price),
            'sale_price': float(product.sale_price),
            'quantity': product.quantity,
            'status': product.status,
            'custom_fields': product.custom_fields,
            'status_display': product.get_status_display(),
            'created_at': _fmt_dt(product.created_at, request),
            'updated_at': _fmt_dt(product.updated_at, request),
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)


@login_required
@business_required
@require_POST
def product_update(request, pk):
    """Обновить товар."""
    try:
        product = Product.objects.get(pk=pk, business=request.business)
        data = json.loads(request.body)

        if 'name' in data:
            product.name = data['name']
        if 'article' in data:
            product.article = data['article']
        if 'category_id' in data:
            try:
                product.category = Category.objects.get(pk=data['category_id'], business=request.business)
            except Category.DoesNotExist:
                product.category = None
        if 'country' in data:
            product.country = data['country']
        if 'purchase_price' in data:
            product.purchase_price = data['purchase_price']
        if 'sale_price' in data:
            product.sale_price = data['sale_price']
        if 'custom_fields' in data:
            product.custom_fields.update(data['custom_fields'])

        product.save()

        Log.log(request.business, 'stock', f'Обновлён товар: {product.name} ({product.article})', request.user)

        return JsonResponse({'ok': True})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)


@login_required
@business_required
@require_POST
def product_delete(request, pk):
    """Удалить товар."""
    try:
        product = Product.objects.get(pk=pk, business=request.business)
        name = product.name
        product.delete()

        Log.log(request.business, 'product', f'Удалён товар: {name}', request.user)

        return JsonResponse({'ok': True})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)


@login_required
@business_required
@require_POST
def product_upload_image(request, pk):
    """Загрузить/заменить фото товара."""
    try:
        product = Product.objects.get(pk=pk, business=request.business)
        f = request.FILES.get('image')
        if not f:
            return JsonResponse({'error': 'Файл не загружен'}, status=400)

        ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else 'jpg'
        if ext not in ('png', 'jpg', 'jpeg', 'webp', 'gif'):
            return JsonResponse({'error': f'Формат .{ext} не поддерживается'}, status=400)

        filename = f'product_{pk}_{uuid.uuid4().hex[:8]}.{ext}'
        img_dir = Path(settings.MEDIA_ROOT) / 'products'
        img_dir.mkdir(parents=True, exist_ok=True)
        filepath = img_dir / filename
        filepath.write_bytes(f.read())

        image_url = f'/media/products/{filename}'
        if not product.custom_fields:
            product.custom_fields = {}
        product.custom_fields['image'] = image_url
        product.save(update_fields=['custom_fields'])

        return JsonResponse({'ok': True, 'image_url': image_url})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
@require_POST
def product_delete_image(request, pk):
    """Удалить фото товара."""
    try:
        product = Product.objects.get(pk=pk, business=request.business)
        if product.custom_fields and product.custom_fields.get('image'):
            # Delete file if local
            img_path = product.custom_fields['image']
            if img_path.startswith('/media/'):
                full_path = Path(settings.BASE_DIR) / img_path.lstrip('/')
                if full_path.exists():
                    full_path.unlink()
            product.custom_fields['image'] = ''
            product.save(update_fields=['custom_fields'])
        return JsonResponse({'ok': True})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)


# ============ Supplies ============

@login_required
@business_required
def supplies_list(request):
    """Список поставок."""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))

    supplies = Supply.objects.filter(business=request.business).select_related('product', 'supplier')

    if search:
        supplies = supplies.filter(
            Q(serial_number__icontains=search) |
            Q(product__name__icontains=search) |
            Q(supplier__name__icontains=search)
        )

    if status:
        supplies = supplies.filter(status=status)

    total = supplies.count()
    supplies = supplies[(page - 1) * per_page: page * per_page]

    data = []
    for s in supplies:
        data.append({
            'id': s.id,
            'serial_number': s.serial_number,
            'product_id': s.product_id,
            'product_name': s.product.name,
            'supplier_id': s.supplier_id,
            'supplier_name': s.supplier.name,
            'quantity': s.quantity,
            'purchase_price': float(s.purchase_price),
            'sale_price': float(s.sale_price),
            'status': s.status,
            'status_display': s.get_status_display(),
            'arrival_date': s.arrival_date.strftime('%d.%m.%Y') if s.arrival_date else '',
            'arrival_time': _fmt_dt(s.created_at, request, '%H:%M'),
            'buyer': s.buyer,
            'custom_fields': s.custom_fields,
            'created_at': _fmt_dt(s.created_at, request),
        })

    return JsonResponse({
        'supplies': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    })


@login_required
@business_required
@require_POST
def supply_create(request):
    """Создать поставку (приёмка товара)."""
    try:
        data = json.loads(request.body)
        article = data.get('article', '').strip()
        product_id = data.get('product_id')
        supplier_id = data.get('supplier_id')
        supplier_name = data.get('supplier_name', '').strip()
        serial_number = data.get('serial_number', '').strip()
        quantity = data.get('quantity', 1)
        purchase_price = data.get('purchase_price', 0) or 0
        if isinstance(purchase_price, str):
            purchase_price = float(purchase_price) if purchase_price.strip() else 0
        sale_price = data.get('sale_price', 0)
        arrival_date = data.get('arrival_date')
        arrival_time = data.get('arrival_time', '')

        if not serial_number:
            return JsonResponse({'error': 'Введите серийный номер'}, status=400)

        if Supply.objects.filter(business=request.business, serial_number=serial_number).exists():
            return JsonResponse({'error': 'Поставка с таким серийным номером уже существует'}, status=400)

        # Найти или создать товар
        product = None
        if product_id:
            product = Product.objects.filter(pk=product_id, business=request.business).first()
        elif article:
            product = Product.objects.filter(business=request.business, article=article).first()
            if not product:
                product = Product.objects.create(
                    business=request.business,
                    article=article,
                    name=data.get('name', article),
                    country=data.get('country', ''),
                    purchase_price=purchase_price,
                    sale_price=float(sale_price) if sale_price else 0,
                )

        if not product:
            return JsonResponse({'error': 'Выберите товар или укажите артикул'}, status=400)

        # Найти или создать поставщика
        supplier = None
        if supplier_id:
            supplier = Supplier.objects.filter(pk=supplier_id, business=request.business).first()
        elif supplier_name:
            supplier, _ = Supplier.objects.get_or_create(business=request.business, name=supplier_name)

        from django.utils import timezone
        from datetime import datetime

        if not arrival_date:
            arrival_date = timezone.now().date()

        supply = Supply.objects.create(
            business=request.business,
            product=product,
            supplier=supplier,
            serial_number=serial_number,
            quantity=quantity,
            purchase_price=purchase_price,
            sale_price=float(product.sale_price) if product.sale_price else 0,
            status='received',
            arrival_date=arrival_date,
            custom_fields=data.get('custom_fields', {}),
        )

        # Пересчитать остатки
        supplied = Supply.objects.filter(product=product, status='received').aggregate(
            total=Sum('quantity')
        )['total'] or 0
        product.quantity = supplied
        product.save(update_fields=['quantity'])

        Log.log(request.business, 'supply', f'Приемка: {product.name} ({serial_number}) от {supplier.name if supplier else "—"}. Закупка: {int(purchase_price)}₽', request.user)

        return JsonResponse({'ok': True, 'id': supply.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============ Sales ============

@login_required
@business_required
def sales_list(request):
    """Список продаж."""
    search = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))

    sales = Sale.objects.filter(business=request.business).select_related('product')

    if search:
        sales = sales.filter(
            Q(customer_name__icontains=search) |
            Q(product__name__icontains=search) |
            Q(serial_number__icontains=search)
        )

    total = sales.count()
    sales = sales[(page - 1) * per_page: page * per_page]

    data = []
    for s in sales:
        data.append({
            'id': s.id,
            'product_id': s.product_id,
            'product_name': s.product.name,
            'serial_number': s.serial_number,
            'customer_name': s.customer_name,
            'quantity': s.quantity,
            'price': float(s.price),
            'total': float(s.total),
            'status': s.status,
            'status_display': s.get_status_display(),
            'date': s.date.strftime('%d.%m.%Y') if s.date else '',
            'custom_fields': s.custom_fields,
            'created_at': _fmt_dt(s.created_at, request),
        })

    return JsonResponse({
        'sales': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    })


@login_required
@business_required
@require_POST
def sale_create(request):
    """Создать продажу."""
    try:
        data = json.loads(request.body)
        supply_id = data.get('supply_id')
        product_id = data.get('product_id')
        serial_number = data.get('serial_number', '').strip()
        customer_name = data.get('customer_name', '').strip()
        quantity = data.get('quantity', 1)
        price = data.get('price', 0)

        if not customer_name:
            return JsonResponse({'error': 'Укажите клиента'}, status=400)

        if not product_id:
            return JsonResponse({'error': 'Выберите товар'}, status=400)

        # Найти товар
        product = Product.objects.filter(pk=product_id, business=request.business).first()
        if not product:
            return JsonResponse({'error': 'Товар не найден'}, status=404)

        # Найти поставку (опционально)
        supply = None
        if supply_id:
            supply = Supply.objects.filter(id=supply_id, business=request.business, status='received').first()
        elif serial_number:
            supply = Supply.objects.filter(
                business=request.business,
                serial_number=serial_number,
                status='received',
            ).first()

        from django.utils import timezone

        # Сформировать серийный номер
        sn = serial_number or (supply.serial_number if supply else f'SALE-{product.id}-{int(timezone.now().timestamp())}')

        sale = Sale.objects.create(
            business=request.business,
            product=product,
            supply=supply,
            serial_number=sn,
            customer_name=customer_name,
            quantity=quantity,
            price=price,
            status='completed',
            date=timezone.now().date(),
            employee=request.user,
            custom_fields=data.get('custom_fields', {}),
        )

        # Обновить статус поставки (если есть)
        if supply:
            supply.status = 'sold'
            supply.buyer = customer_name
            supply.sale_date = timezone.now().strftime('%d.%m.%Y')
            supply.sale_price = price
            supply.save(update_fields=['status', 'buyer', 'sale_date', 'sale_price'])

        # Пересчитать остатки
        supplied = Supply.objects.filter(product=product, status='received').aggregate(
            total=Sum('quantity')
        )['total'] or 0
        product.quantity = supplied
        product.save(update_fields=['quantity'])

        Log.log(request.business, 'sale', f'Продажа: {product.name} → {customer_name}. {int(price)}₽ x{quantity}', request.user)

        return JsonResponse({'ok': True, 'id': sale.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============ Search (for modals) ============

@login_required
@business_required
def stock_serials(request):
    """Поиск товаров на складе по серийному номеру."""
    q = request.GET.get('q', '')
    if not q:
        return JsonResponse({'items': []})

    supplies = Supply.objects.filter(
        business=request.business,
        status='received',
        serial_number__icontains=q
    ).select_related('product', 'supplier')[:20]

    data = []
    for s in supplies:
        data.append({
            'id': s.id,
            'serial_number': s.serial_number,
            'product_id': s.product_id,
            'product_name': s.product.name,
            'supplier_name': s.supplier.name,
            'sale_price': float(s.sale_price),
        })

    return JsonResponse({'items': data})


@login_required
@business_required
def catalog_lookup(request):
    """Поиск по каталогу товаров (для модалки приёмки)."""
    q = request.GET.get('q', '')
    if not q:
        return JsonResponse({'items': []})

    products = Product.objects.filter(
        Q(name__icontains=q) | Q(article__icontains=q),
        business=request.business,
    )[:20]

    data = []
    for p in products:
        data.append({
            'id': p.id,
            'name': p.name,
            'article': p.article,
            'category': p.category.name if p.category else '',
            'sale_price': float(p.sale_price),
        })

    return JsonResponse({'items': data})
