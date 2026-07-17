import json
import threading
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Business, BusinessMembership, EmailVerification, Log
from .decorators import business_required
from .email_utils import send_verification_email, send_welcome_email
from .utils import get_business_url
from tenants.manager import get_tenant_manager


def landing_view(request):
    return render(request, 'landing.html')


def verify_email_view(request, token):
    # Find verification record in database
    try:
        verification = EmailVerification.objects.get(token=token, is_used=False)
    except EmailVerification.DoesNotExist:
        return render(request, 'email_verified.html', {'success': False, 'message': 'Ссылка недействительна или уже использована.'})

    reg_data = verification.data

    # Check if user already exists (in case of retry)
    email = reg_data.get('email', '')
    if User.objects.filter(email=email).exists():
        user = User.objects.filter(email=email).first()
        if user.is_active:
            login(request, user)
            membership = BusinessMembership.objects.filter(user=user).first()
            if membership:
                return redirect(get_business_url(membership.business.slug, '/dashboard/', request))
        return redirect('login')

    # Mark as used
    verification.is_used = True
    verification.save(update_fields=['is_used'])

    user = None
    business = None
    try:
        # Create user
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        user = User(
            username=username,
            email=email,
            password=reg_data['password'],  # Already hashed via make_password
            first_name=reg_data.get('first_name', ''),
            last_name=reg_data.get('last_name', ''),
        )
        user.save()

        # Create business
        business = Business.objects.create(
            name=reg_data['biz_name'],
            slug=reg_data['biz_slug'],
            business_type=reg_data.get('biz_type', 'retail'),
            owner=user,
            phone=reg_data.get('biz_phone', ''),
            description=reg_data.get('biz_description', ''),
        )
        BusinessMembership.objects.create(
            business=business,
            user=user,
            role='owner',
        )

        # Setup tenant DB
        tenant_manager = get_tenant_manager()
        tenant_manager.setup_business(reg_data['biz_slug'], reg_data['biz_name'], reg_data.get('biz_type', 'retail'))

        # Login and redirect
        login(request, user)

        # Send welcome email in background
        login_url = get_business_url(business.slug, '/login/', request)
        def send_welcome():
            try:
                send_welcome_email(email, reg_data.get('first_name', ''), reg_data['biz_name'], login_url)
            except Exception:
                pass
        threading.Thread(target=send_welcome, daemon=True).start()

        return redirect(get_business_url(business.slug, '/dashboard/', request))

    except Exception as e:
        import logging
        logger = logging.getLogger('accounts')
        logger.error(f'Verify email failed for {email}: {e}')
        # Clean up partial objects
        if business and business.pk:
            business.delete()
        if user and user.pk:
            user.delete()
        return render(request, 'email_verified.html', {
            'success': False,
            'message': 'Произошла ошибка при создании аккаунта. Попробуйте зарегистрироваться заново.',
        })


def login_view(request):
    business = getattr(request, 'business', None)

    # If already authenticated, redirect to their business
    if request.user.is_authenticated:
        if business:
            membership = BusinessMembership.objects.filter(user=request.user, business=business).first()
            if membership:
                return redirect(get_business_url(business.slug, '/dashboard/', request))
            logout(request)
        else:
            membership = BusinessMembership.objects.filter(user=request.user).first()
            if membership:
                return redirect(get_business_url(membership.business.slug, '/dashboard/', request))
            logout(request)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Find user by email
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'Аккаунт не найден'})

        # Check if user is active
        if not user_obj.is_active:
            return render(request, 'login.html', {'error': 'Ваш аккаунт был отключён администратором. Обратитесь к администратору.'})

        user = authenticate(request, username=user_obj.username, password=password)
        if user is not None:
            if business:
                membership = BusinessMembership.objects.filter(user=user, business=business).first()
                if not membership:
                    return render(request, 'login.html', {'error': 'Этот аккаунт не зарегистрирован в этом бизнесе'})
                login(request, user)
                Log.log(business, 'auth', f'Вход в систему: {user.username}', user)
                return redirect(get_business_url(business.slug, '/dashboard/', request))
            else:
                login(request, user)
                membership = BusinessMembership.objects.filter(user=user).first()
                if membership:
                    Log.log(membership.business, 'auth', f'Вход в систему: {user.username}', user)
                    return redirect(get_business_url(membership.business.slug, '/dashboard/', request))
                return render(request, 'login.html', {'error': 'У вас пока нет бизнеса. Зарегистрируйтесь.'})

        return render(request, 'login.html', {'error': 'Неверный пароль'})

    return render(request, 'login.html')


def register_view(request):
    if request.user.is_authenticated:
        membership = BusinessMembership.objects.filter(user=request.user).first()
        if membership:
            return redirect(get_business_url(membership.business.slug, '/dashboard/', request))
        logout(request)

    if request.method == 'POST':
        # Account fields
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        # Business fields
        biz_name = request.POST.get('biz_name', '').strip()
        biz_slug = request.POST.get('biz_slug', '').strip().lower()
        biz_type = request.POST.get('biz_type', 'retail')
        biz_type_custom = request.POST.get('biz_type_custom', '').strip()
        biz_phone = request.POST.get('biz_phone', '').strip()
        biz_description = request.POST.get('biz_description', '').strip()

        # Use custom type if "other" selected
        if biz_type == 'other' and biz_type_custom:
            biz_type = biz_type_custom

        errors = []
        if not first_name:
            errors.append('Введите имя')
        if not email:
            errors.append('Введите email')
        if not password:
            errors.append('Введите пароль')
        if password and len(password) < 8:
            errors.append('Пароль должен содержать минимум 8 символов')
        if password != password2:
            errors.append('Пароли не совпадают')
        if User.objects.filter(email=email).exists():
            errors.append('Пользователь с таким email уже существует')
        if not biz_name:
            errors.append('Введите название бизнеса')
        if not biz_slug:
            errors.append('Введите URL-адрес бизнеса')
        if Business.objects.filter(slug=biz_slug).exists():
            errors.append('Бизнес с таким URL уже существует')
        if not request.POST.get('consent_personal_data'):
            errors.append('Необходимо дать согласие на обработку персональных данных')

        if errors:
            return render(request, 'register.html', {'errors': errors})

        # Store registration data in database (not session — works on any device)
        from django.contrib.auth.hashers import make_password
        from django.utils import timezone as tz
        token = EmailVerification.generate_token()
        EmailVerification.objects.create(
            token=token,
            data={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'password': make_password(password),
                'biz_name': biz_name,
                'biz_slug': biz_slug,
                'biz_type': biz_type,
                'biz_phone': biz_phone,
                'biz_description': biz_description,
                'consent_personal_data': True,
                'consent_timestamp': tz.now().isoformat(),
                'consent_ip': request.META.get('REMOTE_ADDR', ''),
            },
        )

        # Build verify URL
        verify_url = f'{request.scheme}://{request.get_host()}/verify-email/{token}/'

        # Send verification email in background thread
        def send_email():
            try:
                send_verification_email(email, first_name, verify_url)
            except Exception:
                pass

        thread = threading.Thread(target=send_email, daemon=True)
        thread.start()

        # Show "check your email" page with the link (for testing)
        return render(request, 'verify_pending.html', {
            'email': email,
            'verify_url': verify_url,
        })

    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    # Redirect to main domain, not subdomain
    from django.conf import settings
    host = request.get_host().split(':')[0]
    parts = host.split('.')
    is_subdomain = len(parts) >= 3
    if is_subdomain:
        base_domain = '.'.join(parts[-2:])
        return redirect(f'https://{base_domain}/')
    return redirect('/')


@login_required
def create_business_view(request):
    existing = BusinessMembership.objects.filter(user=request.user).first()
    if existing:
        return redirect(get_business_url(existing.business.slug, '/dashboard/', request))
    # No business — redirect to unified registration
    return redirect('register')


@login_required
def admin_businesses_view(request):
    if not request.user.is_superuser:
        return redirect('login')

    businesses = Business.objects.select_related('owner').all().order_by('-created_at')
    stats = {
        'total': businesses.count(),
        'active': businesses.filter(is_active=True).count(),
        'inactive': businesses.filter(is_active=False).count(),
    }
    return render(request, 'admin_panel.html', {
        'businesses': businesses,
        'stats': stats,
    })


@login_required
@require_POST
def api_toggle_business(request, business_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        business = Business.objects.get(id=business_id)
        business.is_active = not business.is_active
        business.save(update_fields=['is_active'])
        return JsonResponse({'ok': True, 'is_active': business.is_active})
    except Business.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


# API endpoints
@login_required
def api_business_info(request):
    if not request.business:
        return JsonResponse({'error': 'No business selected'}, status=400)

    return JsonResponse({
        'id': request.business.id,
        'name': request.business.name,
        'slug': request.business.slug,
        'business_type': request.business.business_type,
        'role': request.tenant_role,
        'settings': request.business.settings,
    })


@login_required
@require_POST
def api_update_business_settings(request):
    if not request.business:
        return JsonResponse({'error': 'No business selected'}, status=400)

    if request.tenant_role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)

    import json
    try:
        data = json.loads(request.body)
        settings = request.business.settings
        settings.update(data)
        request.business.settings = settings
        request.business.save(update_fields=['settings'])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# Employee management API
@login_required
def api_users_list(request):
    if not request.business:
        return JsonResponse({'error': 'No business'}, status=400)
    if request.tenant_role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)

    memberships = BusinessMembership.objects.filter(
        business=request.business
    ).select_related('user').order_by('-created_at')

    data = []
    for m in memberships:
        data.append({
            'id': m.user.id,
            'membership_id': m.id,
            'username': m.user.username,
            'email': m.user.email,
            'first_name': m.user.first_name,
            'last_name': m.user.last_name,
            'role': m.role,
            'role_display': m.get_role_display(),
            'phone': m.phone,
            'note': m.note,
            'is_active': m.user.is_active,
            'date_joined': m.user.date_joined.strftime('%d.%m.%Y') if m.user.date_joined else '',
        })

    return JsonResponse(data, safe=False)


def api_check_username(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'available': False})
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'available': not exists})


def api_check_slug(request):
    slug = request.GET.get('slug', '').strip()
    if not slug:
        return JsonResponse({'available': False})
    exists = Business.objects.filter(slug=slug).exists()
    return JsonResponse({'available': not exists})


def api_check_business_name(request):
    name = request.GET.get('name', '').strip()
    if not name:
        return JsonResponse({'available': False})
    exists = Business.objects.filter(name__iexact=name).exists()
    return JsonResponse({'available': not exists})


def api_check_email(request):
    email = request.GET.get('email', '').strip()
    if not email:
        return JsonResponse({'available': False})
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'available': not exists})


@login_required
@require_POST
def api_create_user(request):
    if not request.business:
        return JsonResponse({'error': 'No business'}, status=400)
    if request.tenant_role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)

    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        note = data.get('note', '').strip()
        role = data.get('role', 'manager')

        if not username or not password:
            return JsonResponse({'error': 'Логин и пароль обязательны'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Пользователь уже существует'}, status=400)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        BusinessMembership.objects.create(
            business=request.business,
            user=user,
            role=role,
            phone=phone,
            note=note,
        )

        Log.log(request.business, 'auth', f'Создан сотрудник: {username}', request.user)

        return JsonResponse({'ok': True, 'user_id': user.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_toggle_user(request, user_id):
    if not request.business:
        return JsonResponse({'error': 'No business'}, status=400)
    if request.tenant_role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)

    try:
        membership = BusinessMembership.objects.get(
            business=request.business, user_id=user_id
        )
        user = membership.user
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        status = 'активирован' if user.is_active else 'деактивирован'
        Log.log(request.business, 'auth', f'Сотрудник {user.username} {status}', request.user)
        return JsonResponse({'ok': True, 'is_active': user.is_active})
    except BusinessMembership.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_POST
def api_delete_user(request, user_id):
    if not request.business:
        return JsonResponse({'error': 'No business'}, status=400)
    if request.tenant_role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)

    try:
        membership = BusinessMembership.objects.get(
            business=request.business, user_id=user_id
        )
        if membership.role == 'owner':
            return JsonResponse({'error': 'Нельзя удалить владельца'}, status=400)
        username = membership.user.username
        membership.delete()

        Log.log(request.business, 'auth', f'Удалён сотрудник: {username}', request.user)

        return JsonResponse({'ok': True})
    except BusinessMembership.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_POST
def api_update_member(request, membership_id):
    if not request.business:
        return JsonResponse({'error': 'No business'}, status=400)
    if request.tenant_role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)

    try:
        membership = BusinessMembership.objects.get(
            id=membership_id, business=request.business
        )
        data = json.loads(request.body)
        if 'phone' in data:
            membership.phone = data['phone']
        if 'note' in data:
            membership.note = data['note']
        if 'role' in data and membership.role != 'owner':
            membership.role = data['role']
        membership.save()
        return JsonResponse({'ok': True})
    except BusinessMembership.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


# ============ Logs API ============

@login_required
def api_logs(request):
    """Журнал активности бизнеса."""
    if not request.business:
        return JsonResponse({'error': 'No business'}, status=400)

    log_type = request.GET.get('type', '')
    logs = Log.objects.filter(business=request.business).select_related('user')

    if log_type:
        logs = logs.filter(type=log_type)

    logs = logs[:100]

    # Timezone conversion
    from datetime import timedelta
    TZ_OFFSETS = {
        'Europe/Kaliningrad': 2, 'Europe/Moscow': 3, 'Europe/Samara': 4,
        'Asia/Yekaterinburg': 5, 'Asia/Omsk': 6, 'Asia/Krasnoyarsk': 7,
        'Asia/Irkutsk': 8, 'Asia/Yakutsk': 9, 'Asia/Vladivostok': 10, 'Asia/Kamchatka': 12,
    }
    tz_name = request.COOKIES.get('wms_timezone', 'Europe/Moscow')
    offset = TZ_OFFSETS.get(tz_name, 3)

    data = []
    for log in logs:
        dt = log.created_at + timedelta(hours=offset) if log.created_at else None
        data.append({
            'id': log.id,
            'type': log.type,
            'type_display': log.get_type_display(),
            'action': log.action,
            'user': log.user.username if log.user else '',
            'created_at': dt.strftime('%d.%m.%Y %H:%M') if dt else '',
        })

    return JsonResponse(data, safe=False)


@login_required
@require_POST
def upload_avatar_api(request):
    import os
    try:
        file = request.FILES.get('avatar')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'Файл не загружен'}, status=400)

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return JsonResponse({'status': 'error', 'message': 'Допустимые форматы: JPG, PNG, GIF, WebP'}, status=400)

        business = getattr(request, 'business', None)
        avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
        os.makedirs(avatar_dir, exist_ok=True)

        # Include business slug in filename for isolation
        biz_prefix = f'{business.slug}_' if business else ''
        filename = f'{biz_prefix}user_{request.user.id}{ext}'
        filepath = os.path.join(avatar_dir, filename)
        with open(filepath, 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        avatar_path = f'avatars/{filename}'

        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.avatar = avatar_path
        profile.save()

        return JsonResponse({'status': 'ok', 'avatar_url': f'/media/{avatar_path}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@business_required
@require_POST
def save_site_settings_api(request):
    """Save site settings for the business."""
    try:
        data = json.loads(request.body)
        business = request.business
        for field in ['site_title', 'site_description', 'site_phone', 'site_email',
                      'site_address', 'site_work_hours']:
            if field in data:
                setattr(business, field, data[field])
        if 'site_color_scheme' in data:
            business.site_color_scheme = data['site_color_scheme']
        business.save()
        Log.log(business, 'settings', 'Обновлены настройки сайта', request.user)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
