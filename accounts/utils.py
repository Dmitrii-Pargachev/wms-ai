from django.conf import settings


def get_business_url(slug, path='/dashboard/', request=None):
    """Build a full URL for a business subdomain."""
    if request:
        protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host().split(':')[0]
    else:
        protocol = 'http'
        host = 'wms-ai.ru'

    domain_parts = host.split('.')
    base_domain = '.'.join(domain_parts[-2:])
    return f'{protocol}://{slug}.{base_domain}{path}'
