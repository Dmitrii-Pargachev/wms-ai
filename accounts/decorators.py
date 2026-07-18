from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse


def business_required(view_func):
    """Декоратор: требует авторизации и выбора бизнеса."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.path.startswith('/api/'):
                return JsonResponse({'error': 'Authentication required'}, status=401)
            return redirect('login')

        if not request.business:
            if request.path.startswith('/api/'):
                return JsonResponse({'error': 'Business not selected'}, status=400)
            return redirect('register')

        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(min_role):
    """
    Декоратор: требует определённую роль в бизнесе.
    Roles: owner > admin > manager > viewer
    """
    ROLE_HIERARCHY = {
        'owner': 4,
        'admin': 3,
        'manager': 2,
        'viewer': 1,
    }

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.path.startswith('/api/'):
                    return JsonResponse({'error': 'Authentication required'}, status=401)
                return redirect('login')

            if not request.business:
                if request.path.startswith('/api/'):
                    return JsonResponse({'error': 'Business not selected'}, status=400)
                return redirect('register')

            user_level = ROLE_HIERARCHY.get(request.tenant_role, 0)
            required_level = ROLE_HIERARCHY.get(min_role, 0)

            if user_level < required_level:
                if request.path.startswith('/api/'):
                    return JsonResponse({'error': 'Insufficient permissions'}, status=403)
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
