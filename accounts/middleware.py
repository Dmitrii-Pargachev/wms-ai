from django.shortcuts import redirect, render
from django.http import Http404, JsonResponse
from django.db import connections
from django.conf import settings
from .models import Business, BusinessMembership
from .utils import get_business_url
from tenants.manager import get_tenant_manager
from tenants.router import get_tenant_router


class TenantMiddleware:

    PUBLIC_PATHS = ['/login', '/register', '/logout', '/create-business', '/landing',
                    '/api/check-username', '/api/check-slug', '/api/check-business-name',
                    '/api/check-email', '/verify-email', '/health', '/privacy']

    def __init__(self, get_response):
        self.get_response = get_response
        self.tenant_manager = get_tenant_manager()
        self.tenant_router = get_tenant_router()

    def __call__(self, request):
        request.business = None
        request.tenant_role = None
        request.tenant_config = {}
        request.db_alias = 'default'

        import re
        path = re.sub(r'/+', '/', request.path).rstrip('/')

        # Static/admin — pass through
        if path.startswith('/static') or path.startswith('/admin'):
            return self.get_response(request)

        host = request.get_host().split(':')[0]
        is_main = host in ('wms-ai.ru', 'localhost', '127.0.0.1')
        parts = host.split('.')
        is_subdomain = len(parts) >= 3

        # === SUBDOMAIN ===
        if is_subdomain:
            slug = parts[0]
            self._setup_tenant(request, slug)

            # Public paths always work on any subdomain
            if path in self.PUBLIC_PATHS or path.startswith('/verify-email/') or path.startswith('/new/verify-email/'):
                try:
                    response = self.get_response(request)
                except Http404:
                    return self._render_landing(request)
                finally:
                    self.tenant_router.set_current_db(None)
                return response

            # Unknown subdomain — landing
            if not request.business:
                return self._render_landing(request, unknown_subdomain=True)

            # ROOT of known subdomain → public catalog (NO AUTH)
            if path == '' or path == '/':
                try:
                    from inventory.catalog_views import catalog_view
                    response = catalog_view(request)
                except Http404:
                    response = self._render_landing(request)
                except Exception as e:
                    import logging
                    logging.getLogger('tenants').error(f'Catalog error: {e}')
                    response = self._render_landing(request)
                finally:
                    self.tenant_router.set_current_db(None)
                return response

            # /dashboard/ → redirect to /system/ (backward compat)
            if path.startswith('/dashboard'):
                new_path = path.replace('/dashboard', '/system', 1)
                return redirect(new_path + ('/' if not new_path.endswith('/') else ''))

            # /system/* — require auth + membership (existing dashboard)
            if path.startswith('/system'):
                if not request.user.is_authenticated:
                    return redirect(f'{settings.LOGIN_URL}?next={request.path}')

                try:
                    membership = BusinessMembership.objects.get(
                        business=request.business, user=request.user
                    )
                    request.tenant_role = membership.role
                except BusinessMembership.DoesNotExist:
                    if request.path.startswith('/api/'):
                        return JsonResponse({'error': 'Access denied'}, status=403)
                    return redirect(f'{settings.LOGIN_URL}')

                # Authenticated + member — serve the dashboard
                try:
                    response = self.get_response(request)
                except Http404:
                    return self._render_landing(request)
                finally:
                    self.tenant_router.set_current_db(None)
                return response

            # Catalog API (public, no auth)
            if path.startswith('/api/catalog') or path.startswith('/api/ai'):
                try:
                    response = self.get_response(request)
                except Http404:
                    return JsonResponse({'error': 'Not found'}, status=404)
                finally:
                    self.tenant_router.set_current_db(None)
                return response

        # === MAIN DOMAIN ===
        elif is_main:
            if path == '':
                if request.user.is_authenticated:
                    membership = BusinessMembership.objects.filter(user=request.user).first()
                    if membership:
                        if host in ('localhost', '127.0.0.1'):
                            self._setup_tenant(request, membership.business.slug)
                            return self.get_response(request)
                        return redirect(get_business_url(membership.business.slug, '/system/', request))
                return self._render_landing(request)

            if path in self.PUBLIC_PATHS or path.startswith('/verify-email/') or path.startswith('/new/verify-email/'):
                try:
                    response = self.get_response(request)
                except Http404:
                    return self._render_landing(request)
                finally:
                    self.tenant_router.set_current_db(None)
                return response

            if request.user.is_authenticated:
                membership = BusinessMembership.objects.filter(user=request.user).first()
                if membership:
                    if host in ('localhost', '127.0.0.1'):
                        self._setup_tenant(request, membership.business.slug)
                        try:
                            response = self.get_response(request)
                        except Http404:
                            return self._render_landing(request)
                        finally:
                            self.tenant_router.set_current_db(None)
                        return response
                    return redirect(get_business_url(membership.business.slug, request.path + '/', request))
                return redirect('/create-business/')

            return self._render_landing(request)

        # Unknown host
        else:
            return self._render_landing(request)

        try:
            response = self.get_response(request)
        except Http404:
            return self._render_landing(request)
        finally:
            self.tenant_router.set_current_db(None)

        return response

    def _render_landing(self, request, unknown_subdomain=False):
        try:
            return render(request, 'landing.html', {'unknown_subdomain': unknown_subdomain})
        except Exception:
            return redirect('/landing/')

    def _setup_tenant(self, request, slug):
        try:
            business = Business.objects.get(slug=slug, is_active=True)
            request.business = business
            db_alias = f'tenant_{slug}'
            db_config = self.tenant_manager.get_database_config(slug)
            if db_alias not in connections.databases:
                connections.databases[db_alias] = db_config
                self._migrate_tenant_db(db_alias)
            self.tenant_router.set_current_db(db_alias)
            request.db_alias = db_alias
            request.tenant_config = self.tenant_manager.get_business_config(slug)
        except Business.DoesNotExist:
            request.business = None

    def _migrate_tenant_db(self, db_alias):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        try:
            call_command('migrate', database=db_alias, verbosity=1, stdout=out)
            import logging
            logger = logging.getLogger('tenants')
            logger.info(f'Migrated tenant DB {db_alias}: {out.getvalue()[-200:]}')
        except Exception as e:
            import logging
            logger = logging.getLogger('tenants')
            logger.error(f'Failed to migrate tenant DB {db_alias}: {e}')
