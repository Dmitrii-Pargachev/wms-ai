import json
import uuid
import subprocess
import tempfile
import os
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from accounts.decorators import business_required
from inventory.models import Product

POLZA_API_KEY = 'pza_96xp65ftPNuocVhLlWCn1VBdn662GG23'
POLZA_API_URL = 'https://polza.ai/api/v1/media'
POLZA_MODEL = 'google/gemini-3.1-flash-lite-image'


@login_required
@business_required
def ai_generate_view(request):
    products = Product.objects.filter(business=request.business).order_by('-created_at')[:50]
    return render(request, 'dashboard/ai_generate.html', {
        'business': request.business,
        'role': request.tenant_role,
        'active': 'ai',
        'products': products,
    })


@csrf_exempt
def ai_generate_api(request):
    """Generate image via Polza AI."""
    tmp_path = None
    try:
        # Manual method check — never return HTML
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)

        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Auth required'}, status=401)
        if not getattr(request, 'business', None):
            return JsonResponse({'error': 'Business required'}, status=400)

        body = json.loads(request.body)
        prompt = body.get('prompt', '').strip()
        if not prompt:
            return JsonResponse({'error': 'Введите промпт'}, status=400)

        image_url = body.get('image_url', '').strip()

        payload = {
            'model': POLZA_MODEL,
            'input': {
                'prompt': prompt,
                'aspect_ratio': '1:1',
                'image_resolution': '1K',
            },
        }
        if image_url and image_url.startswith('http'):
            payload['input']['images'] = [{'type': 'url', 'data': image_url}]

        fd, tmp_path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f, ensure_ascii=False)

        cmd = [
            'curl', '-s', '-k', '--max-time', '90',
            '-X', 'POST', POLZA_API_URL,
            '-H', f'Authorization: Bearer {POLZA_API_KEY}',
            '-H', 'Content-Type: application/json',
            '-d', f'@{tmp_path}'
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=100)

        if proc.returncode != 0:
            return JsonResponse({'error': 'API connection failed'})

        result = json.loads(proc.stdout)

        if result.get('status') == 'failed':
            msg = result.get('error', {}).get('message', 'Ошибка генерации')
            return JsonResponse({'error': msg})

        data_list = result.get('data', [])
        url = ''
        if isinstance(data_list, list) and data_list:
            url = data_list[0].get('url', '')

        if not url:
            return JsonResponse({'error': 'API не вернул изображение'})

        return JsonResponse({'ok': True, 'image_url': url})

    except subprocess.TimeoutExpired:
        return JsonResponse({'error': 'Генерация заняла слишком long (>90с)'})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный ответ от API'})
    except Exception as e:
        return JsonResponse({'error': str(e)[:200]})
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@csrf_exempt
def ai_upload_reference(request):
    try:
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Auth required'}, status=401)
        if not getattr(request, 'business', None):
            return JsonResponse({'error': 'Business required'}, status=400)

        f = request.FILES.get('file')
        if not f:
            return JsonResponse({'error': 'Файл не загружен'}, status=400)

        ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else 'png'
        if ext not in ('png', 'jpg', 'jpeg', 'webp', 'gif'):
            return JsonResponse({'error': f'Формат .{ext} не поддерживается'}, status=400)

        filename = f'ai_{uuid.uuid4().hex[:12]}.{ext}'
        ai_dir = Path(settings.MEDIA_ROOT) / request.business.slug / 'ai'
        ai_dir.mkdir(parents=True, exist_ok=True)
        filepath = ai_dir / filename
        filepath.write_bytes(f.read())

        scheme = 'https' if request.is_secure() else 'http'
        url = f'{scheme}://{request.get_host()}/media/{request.business.slug}/ai/{filename}'
        return JsonResponse({'ok': True, 'url': url, 'filename': f.name})
    except Exception as e:
        return JsonResponse({'error': str(e)[:200]})


@csrf_exempt
def ai_apply_to_product(request, product_id):
    try:
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Auth required'}, status=401)

        product = Product.objects.get(id=product_id, business=request.business)
        body = json.loads(request.body)
        image_url = body.get('image_url', '').strip()
        if not image_url:
            return JsonResponse({'error': 'URL пуст'}, status=400)

        if not product.custom_fields:
            product.custom_fields = {}
        product.custom_fields['image'] = image_url
        product.save(update_fields=['custom_fields'])
        return JsonResponse({'ok': True})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)[:200]})
