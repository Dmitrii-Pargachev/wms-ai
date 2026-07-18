import json
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from accounts.decorators import business_required
from accounts.models import TableSchema, FieldSchema
from accounts.dynamic_models import DynamicModelService


@login_required
@business_required
def tables_list(request):
    """Список пользовательских таблиц."""
    tables = TableSchema.objects.filter(business=request.business).order_by('name')
    data = [{
        'id': t.id,
        'name': t.name,
        'icon': t.icon,
        'db_table_name': t.db_table_name,
        'fields_count': t.fields.count(),
        'created_at': t.created_at.strftime('%d.%m.%Y'),
    } for t in tables]
    return JsonResponse({'tables': data})


@csrf_exempt
@login_required
@business_required
@require_POST
def table_create(request):
    """Создать таблицу."""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        icon = data.get('icon', '📋')

        if not name:
            return JsonResponse({'error': 'Введите название'}, status=400)

        # Generate unique db_table_name
        base_name = 'custom_' + name.lower().replace(' ', '_').replace('-', '_')
        db_table_name = base_name
        counter = 1
        while TableSchema.objects.filter(db_table_name=db_table_name).exists():
            db_table_name = f"{base_name}_{counter}"
            counter += 1

        table = TableSchema.objects.create(
            business=request.business,
            name=name,
            icon=icon,
            db_table_name=db_table_name,
        )

        # Create default "name" field
        FieldSchema.objects.create(
            table=table,
            name='name',
            field_type='text',
            required=True,
            position=0,
        )

        # Create SQL table
        service = DynamicModelService(request.db_alias)
        service.create_table(table)

        return JsonResponse({'ok': True, 'id': table.id, 'name': table.name})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
def table_detail(request, table_id):
    """Детали таблицы с полями."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        fields = table.fields.all().order_by('position', 'created_at')
        return JsonResponse({
            'id': table.id,
            'name': table.name,
            'icon': table.icon,
            'db_table_name': table.db_table_name,
            'fields': [{
                'id': f.id,
                'name': f.name,
                'field_type': f.field_type,
                'field_type_display': f.get_field_type_display(),
                'required': f.required,
                'options': f.options,
                'related_table_id': f.related_table_id,
                'position': f.position,
            } for f in fields],
            'created_at': table.created_at.strftime('%d.%m.%Y'),
        })
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)


@csrf_exempt
@login_required
@business_required
@require_POST
def table_delete(request, table_id):
    """Удалить таблицу."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        # Drop SQL table (ignore if doesn't exist)
        try:
            service = DynamicModelService(request.db_alias)
            service.drop_table(table)
        except Exception:
            pass
        # Delete schema
        table.delete()
        return JsonResponse({'ok': True})
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@login_required
@business_required
@require_POST
def field_create(request, table_id):
    """Добавить поле в таблицу."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        data = json.loads(request.body)

        name = data.get('name', '').strip()
        field_type = data.get('field_type', 'text')
        required = data.get('required', False)
        options = data.get('options', [])
        related_table_id = data.get('related_table_id')

        if not name:
            return JsonResponse({'error': 'Введите название поля'}, status=400)

        if FieldSchema.objects.filter(table=table, name=name).exists():
            return JsonResponse({'error': 'Поле с таким именем уже существует'}, status=400)

        # Auto-create SQL table if missing
        service = DynamicModelService(request.db_alias)
        existing = service._get_columns(table.db_table_name)
        if not existing:
            service.create_table(table)

        position = table.fields.count()

        related_table = None
        if related_table_id and field_type == 'relation':
            related_table = TableSchema.objects.get(id=related_table_id, business=request.business)

        field = FieldSchema.objects.create(
            table=table,
            name=name,
            field_type=field_type,
            required=required,
            options=options,
            related_table=related_table,
            position=position,
        )

        # Alter SQL table to add new column
        service.alter_table(table)

        return JsonResponse({'ok': True, 'id': field.id})
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
@require_POST
def field_delete(request, table_id, field_id):
    """Удалить поле."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        field = FieldSchema.objects.get(id=field_id, table=table)
        field.delete()
        return JsonResponse({'ok': True})
    except (TableSchema.DoesNotExist, FieldSchema.DoesNotExist):
        return JsonResponse({'error': 'Не найдено'}, status=404)


@login_required
@business_required
def rows_list(request, table_id):
    """Список записей таблицы."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        service = DynamicModelService(request.db_alias)

        # Auto-create SQL table if missing
        existing = service._get_columns(table.db_table_name)
        if not existing:
            service.create_table(table)

        filters = {}
        for key in request.GET:
            if key not in ('page', 'per_page', 'sort'):
                filters[key] = request.GET[key]

        sort = request.GET.get('sort', None)
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))

        result = service.query_rows(table.db_table_name, filters, sort, page, per_page)
        return JsonResponse(result)
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger('accounts.dynamic').error(f'rows_list error: {e}', exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@login_required
@business_required
@require_POST
def row_create(request, table_id):
    """Создать запись."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        service = DynamicModelService(request.db_alias)
        data = json.loads(request.body)

        # Auto-create SQL table if missing
        existing = service._get_columns(table.db_table_name)
        if not existing:
            service.create_table(table)

        data.pop('id', None)
        data.pop('created_at', None)
        data.pop('updated_at', None)

        # Fill empty required fields with defaults
        for f in table.fields.filter(required=True):
            if f.name in data and (data[f.name] is None or str(data[f.name]).strip() == ''):
                data[f.name] = '-'

        row_id = service.insert_row(table.db_table_name, data)
        return JsonResponse({'ok': True, 'id': row_id})
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger('accounts.dynamic').error(f'row_create error: {e}', exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@login_required
@business_required
@require_POST
def row_update(request, table_id, row_id):
    """Обновить запись."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        service = DynamicModelService(request.db_alias)
        data = json.loads(request.body)

        data.pop('id', None)
        data.pop('created_at', None)
        data.pop('updated_at', None)

        service.update_row(table.db_table_name, row_id, data)
        return JsonResponse({'ok': True})
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@login_required
@business_required
@require_POST
def row_delete(request, table_id, row_id):
    """Удалить запись."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        service = DynamicModelService(request.db_alias)
        service.delete_row(table.db_table_name, row_id)
        return JsonResponse({'ok': True})
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@business_required
@require_POST
def rows_import(request, table_id):
    """Импорт CSV данных."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        service = DynamicModelService(request.db_alias)

        csv_file = request.FILES.get('file')
        if not csv_file:
            return JsonResponse({'error': 'Загрузите файл'}, status=400)

        import csv
        import io

        decoded = csv_file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        created = 0
        errors = []
        for i, row in enumerate(reader, 1):
            try:
                valid_fields = {f.name for f in table.fields.all()}
                filtered_row = {k: v for k, v in row.items() if k in valid_fields}
                service.insert_row(table.db_table_name, filtered_row)
                created += 1
            except Exception as e:
                errors.append(f"Строка {i}: {str(e)}")

        return JsonResponse({'ok': True, 'created': created, 'errors': errors})
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)


@login_required
@business_required
def rows_export(request, table_id):
    """Экспорт в CSV."""
    try:
        table = TableSchema.objects.get(id=table_id, business=request.business)
        service = DynamicModelService(request.db_alias)

        result = service.query_rows(table.db_table_name, per_page=10000)

        import csv
        import io

        output = io.StringIO()
        if result['rows']:
            writer = csv.DictWriter(output, fieldnames=result['rows'][0].keys())
            writer.writeheader()
            writer.writerows(result['rows'])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{table.name}.csv"'
        return response
    except TableSchema.DoesNotExist:
        return JsonResponse({'error': 'Таблица не найдена'}, status=404)
