import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from accounts.decorators import business_required
from accounts.models import Client, Log


@login_required
@business_required
def clients_list(request):
    """Список клиентов."""
    search = request.GET.get('search', '')
    clients = Client.objects.filter(business=request.business)

    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(social_username__icontains=search)
        )

    data = [{
        'id': c.id,
        'phone': c.phone,
        'social_network': c.social_network,
        'social_username': c.social_username,
        'first_name': c.first_name,
        'last_name': c.last_name,
        'total_spent': float(c.total_spent),
        'status': c.status,
        'status_display': c.status_display,
        'created_at': c.created_at.strftime('%d.%m.%Y') if c.created_at else '',
    } for c in clients[:50]]

    return JsonResponse(data, safe=False)


@login_required
@business_required
@require_POST
def client_create(request):
    """Создать или обновить клиента."""
    try:
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        social_network = data.get('social_network', 'telegram')
        social_username = data.get('social_username', '').strip()

        if not phone or not first_name:
            return JsonResponse({'error': 'Телефон и имя обязательны'}, status=400)

        client, created = Client.objects.get_or_create(
            business=request.business,
            phone=phone,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'social_network': social_network,
                'social_username': social_username,
            }
        )
        if not created:
            client.first_name = first_name
            client.last_name = last_name
            if social_username:
                client.social_network = social_network
                client.social_username = social_username
            client.save()

        Log.log(request.business, 'user', f'Клиент: {first_name} {last_name} ({phone})', request.user)

        return JsonResponse({'ok': True, 'client_id': client.id, 'created': created})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@business_required
@require_POST
def client_delete(request, client_id):
    """Удалить клиента."""
    try:
        client = Client.objects.get(id=client_id, business=request.business)
        name = f'{client.first_name} {client.last_name}'
        client.delete()
        Log.log(request.business, 'user', f'Удалён клиент: {name}', request.user)
        return JsonResponse({'ok': True})
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Клиент не найден'}, status=404)
