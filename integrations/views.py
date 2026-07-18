from django.contrib.auth.decorators import login_required
from accounts.decorators import business_required


@login_required
@business_required
def exchange_rate(request):
    """Получить текущий курс USD/RUB — прокси к analytics.exchange."""
    from analytics.exchange import exchange_rate_api
    return exchange_rate_api(request)
