from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Avg
from django.utils import timezone
from django.template.loader import render_to_string
from accounts.decorators import business_required
from inventory.models import Product, Supply, Sale


@login_required
@business_required
def sales_report(request):
    """Отчёт по продажам."""
    period = request.GET.get('period', 'month')
    now = timezone.now()

    if period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now - timedelta(days=30)
    elif period == 'quarter':
        start = now - timedelta(days=90)
    elif period == 'year':
        start = now - timedelta(days=365)
    else:
        start = now - timedelta(days=30)

    sales = Sale.objects.filter(
        business=request.business,
        status='completed',
        created_at__gte=start
    )

    # Summary
    total_revenue = sales.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    total_count = sales.count()
    avg_check = sales.aggregate(avg=Avg(F('price') * F('quantity')))['avg'] if total_count > 0 else 0

    # By category
    by_category = sales.values('product__category__name').annotate(
        revenue=Sum(F('price') * F('quantity')),
        count=Count('id'),
        avg=Avg(F('price') * F('quantity'))
    ).order_by('-revenue')

    # Top products
    top_products = sales.values('product__name').annotate(
        revenue=Sum(F('price') * F('quantity')),
        count=Count('id')
    ).order_by('-revenue')[:10]

    return JsonResponse({
        'period': period,
        'summary': {
            'revenue': float(total_revenue),
            'count': total_count,
            'avg_check': float(avg_check) if avg_check else 0,
        },
        'by_category': list(by_category),
        'top_products': list(top_products),
    })


@login_required
@business_required
def inventory_report(request):
    """Отчёт по остаткам."""
    products = Product.objects.filter(business=request.business)

    # Summary
    total_products = products.count()
    total_value = products.aggregate(
        total=Sum(F('purchase_price') * F('quantity'))
    )['total'] or 0

    total_sale_value = products.aggregate(
        total=Sum(F('sale_price') * F('quantity'))
    )['total'] or 0

    # By status
    by_status = {
        'instock': products.filter(status='instock').count(),
        'low': products.filter(status='low').count(),
        'out': products.filter(status='out').count(),
    }

    # By category
    by_category = products.values('category__name').annotate(
        count=Count('id'),
        total_qty=Sum('quantity'),
        value=Sum(F('purchase_price') * F('quantity'))
    ).order_by('-value')

    # Low stock items
    low_stock = products.filter(status__in=['low', 'out']).values(
        'name', 'article', 'quantity', 'status'
    )[:20]

    return JsonResponse({
        'summary': {
            'total_products': total_products,
            'total_value': float(total_value),
            'total_sale_value': float(total_sale_value),
            'potential_profit': float(total_sale_value - total_value),
        },
        'by_status': by_status,
        'by_category': list(by_category),
        'low_stock': list(low_stock),
    })


@login_required
@business_required
def export_sales_html(request):
    """Экспорт отчёта по продажам в HTML."""
    period = request.GET.get('period', 'month')
    now = timezone.now()

    if period == 'week':
        start = now - timedelta(days=7)
        period_name = 'За неделю'
    elif period == 'month':
        start = now - timedelta(days=30)
        period_name = 'За месяц'
    elif period == 'quarter':
        start = now - timedelta(days=90)
        period_name = 'За квартал'
    else:
        start = now - timedelta(days=30)
        period_name = 'За месяц'

    sales = Sale.objects.filter(
        business=request.business,
        status='completed',
        created_at__gte=start
    ).select_related('product')

    total_revenue = sales.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    total_count = sales.count()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Отчёт по продажам - {period_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            h1 {{ color: #1e293b; }}
            .summary {{ display: flex; gap: 24px; margin: 20px 0; }}
            .summary-card {{ padding: 20px; background: #f1f5f9; border-radius: 8px; }}
            .summary-value {{ font-size: 24px; font-weight: bold; color: #6366f1; }}
            .summary-label {{ font-size: 13px; color: #64748b; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background: #f8fafc; font-weight: 600; }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #94a3b8; }}
        </style>
    </head>
    <body>
        <h1>Отчёт по продажам</h1>
        <p>{period_name} | {now.strftime('%d.%m.%Y')}</p>

        <div class="summary">
            <div class="summary-card">
                <div class="summary-value">{total_revenue:,.0f} ₽</div>
                <div class="summary-label">Выручка</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{total_count}</div>
                <div class="summary-label">Продаж</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{total_revenue / total_count:,.0f} ₽</div>
                <div class="summary-label">Средний чек</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Дата</th>
                    <th>Товар</th>
                    <th>Клиент</th>
                    <th>Кол-во</th>
                    <th>Цена</th>
                    <th>Сумма</th>
                </tr>
            </thead>
            <tbody>
    """

    for sale in sales[:100]:
        html += f"""
                <tr>
                    <td>{sale.date.strftime('%d.%m.%Y') if sale.date else '-'}</td>
                    <td>{sale.product.name}</td>
                    <td>{sale.customer_name or '-'}</td>
                    <td>{sale.quantity}</td>
                    <td>{sale.price:,.0f} ₽</td>
                    <td>{sale.total:,.0f} ₽</td>
                </tr>
        """

    html += """
            </tbody>
        </table>

        <div class="footer">
            WMS-AI | Отчёт сгенерирован автоматически
        </div>
    </body>
    </html>
    """

    return HttpResponse(html, content_type='text/html')


@login_required
@business_required
def export_sales_pdf(request):
    """Экспорт отчёта по продажам в PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import io
    import os

    # Register Cyrillic font
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    ]
    font_registered = False
    for fp in font_paths:
        if os.path.exists(fp):
            pdfmetrics.registerFont(TTFont('DejaVuSans', fp))
            bold_fp = fp.replace('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')
            if os.path.exists(bold_fp):
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_fp))
            else:
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', fp))
            font_registered = True
            break

    font_name = 'DejaVuSans' if font_registered else 'Helvetica'

    period = request.GET.get('period', 'month')
    now = timezone.now()

    if period == 'week':
        start = now - timedelta(days=7)
        period_name = 'За неделю'
    elif period == 'month':
        start = now - timedelta(days=30)
        period_name = 'За месяц'
    elif period == 'quarter':
        start = now - timedelta(days=90)
        period_name = 'За квартал'
    else:
        start = now - timedelta(days=30)
        period_name = 'За месяц'

    sales = Sale.objects.filter(
        business=request.business,
        status='completed',
        created_at__gte=start
    ).select_related('product')

    total_revenue = sales.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    total_count = sales.count()
    avg_check = total_revenue / total_count if total_count > 0 else 0

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=12, fontName=font_name)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontName=font_name)
    elements.append(Paragraph(f'Отчёт по продажам — {period_name}', title_style))
    elements.append(Paragraph(f'Дата: {now.strftime("%d.%m.%Y")}', normal_style))
    elements.append(Spacer(1, 12))

    summary_data = [
        ['Показатель', 'Значение'],
        ['Выручка', f'{total_revenue:,.0f} ₽'],
        ['Количество продаж', str(total_count)],
        ['Средний чек', f'{avg_check:,.0f} ₽'],
    ]
    summary_table = Table(summary_data, colWidths=[120, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    if sales.exists():
        table_data = [['Дата', 'Товар', 'Клиент', 'Кол-во', 'Цена', 'Сумма']]
        for sale in sales[:50]:
            table_data.append([
                sale.date.strftime('%d.%m.%Y') if sale.date else '-',
                sale.product.name[:25] if sale.product else '-',
                (sale.customer_name or '-')[:20],
                str(sale.quantity),
                f'{sale.price:,.0f} ₽',
                f'{sale.total:,.0f} ₽',
            ])
        sales_table = Table(table_data, colWidths=[65, 90, 70, 40, 55, 60])
        sales_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(sales_table)
    else:
        elements.append(Paragraph('Нет продаж за выбранный период', normal_style))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph('WMS·AI — Отчёт сгенерирован автоматически', normal_style))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{period}.pdf"'
    return response


@login_required
@business_required
def export_inventory_pdf(request):
    """Экспорт отчёта по остаткам в PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import io
    import os

    # Register Cyrillic font
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    ]
    font_registered = False
    for fp in font_paths:
        if os.path.exists(fp):
            pdfmetrics.registerFont(TTFont('DejaVuSans', fp))
            bold_fp = fp.replace('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')
            if os.path.exists(bold_fp):
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_fp))
            else:
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', fp))
            font_registered = True
            break

    font_name = 'DejaVuSans' if font_registered else 'Helvetica'

    products = Product.objects.filter(business=request.business)
    now = timezone.now()

    total_products = products.count()
    total_value = products.aggregate(total=Sum(F('purchase_price') * F('quantity')))['total'] or 0
    total_sale_value = products.aggregate(total=Sum(F('sale_price') * F('quantity')))['total'] or 0

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=12, fontName=font_name)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontName=font_name)
    elements.append(Paragraph('Отчёт по остаткам', title_style))
    elements.append(Paragraph(f'Дата: {now.strftime("%d.%m.%Y")}', normal_style))
    elements.append(Spacer(1, 12))

    summary_data = [
        ['Показатель', 'Значение'],
        ['Всего товаров', str(total_products)],
        ['Стоимость закупки', f'{total_value:,.0f} ₽'],
        ['Стоимость продажи', f'{total_sale_value:,.0f} ₽'],
        ['Потенциальная прибыль', f'{(total_sale_value - total_value):,.0f} ₽'],
    ]
    summary_table = Table(summary_data, colWidths=[140, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    if products.exists():
        table_data = [['Товар', 'Артикул', 'Кол-во', 'Закупка', 'Продажа', 'Статус']]
        for p in products[:50]:
            status_display = {'instock': 'В наличии', 'low': 'Мало', 'out': 'Нет'}.get(p.status, p.status)
            table_data.append([
                p.name[:30],
                p.article or '-',
                str(p.quantity),
                f'{p.purchase_price:,.0f} ₽',
                f'{p.sale_price:,.0f} ₽',
                status_display,
            ])
        products_table = Table(table_data, colWidths=[100, 60, 40, 60, 60, 60])
        products_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(products_table)
    else:
        elements.append(Paragraph('Нет товаров на складе', normal_style))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph('WMS·AI — Отчёт сгенерирован автоматически', normal_style))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="inventory_report.pdf"'
    return response
