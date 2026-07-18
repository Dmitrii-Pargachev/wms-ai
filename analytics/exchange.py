import time
import urllib.request
import json
import ssl
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

_exchange_cache = {'rate': None, 'timestamp': 0}


@login_required
def exchange_rate_api(request):
    now = time.time()
    if _exchange_cache['rate'] and now - _exchange_cache['timestamp'] < 60:
        return JsonResponse({'rate': _exchange_cache['rate'], 'cached': True})

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            'https://api.rapira.net/open/market/rates',
            headers={'Accept': 'application/json', 'User-Agent': 'WMS-AI/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get('data', []):
                if item.get('symbol') == 'USDT/RUB':
                    rate = item.get('close') or item.get('bidPrice')
                    if rate:
                        _exchange_cache['rate'] = round(float(rate), 2)
                        _exchange_cache['timestamp'] = now
                        return JsonResponse({'rate': round(float(rate), 2), 'cached': False, 'source': 'rapira'})
    except Exception:
        pass

    apis = [
        'https://api.exchangerate-api.com/v4/latest/USD',
        'https://open.er-api.com/v6/latest/USD',
    ]

    for api_url in apis:
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'WMS-AI/1.0'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                data = json.loads(resp.read().decode())
                rate = data.get('rates', {}).get('RUB')
                if rate:
                    _exchange_cache['rate'] = round(rate, 2)
                    _exchange_cache['timestamp'] = now
                    return JsonResponse({'rate': round(rate, 2), 'cached': False})
        except Exception:
            continue

    if _exchange_cache['rate']:
        return JsonResponse({'rate': _exchange_cache['rate'], 'cached': True, 'stale': True})

    return JsonResponse({'rate': 85.0, 'fallback': True})
