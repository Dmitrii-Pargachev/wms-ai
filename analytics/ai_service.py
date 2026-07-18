"""
AI Service for WMS-AI
Интеграция с polza.ai для аналитики и советов.
"""

import json
import logging
from typing import Optional
from django.conf import settings
from tenants.manager import get_tenant_manager

logger = logging.getLogger('analytics.ai')


class AIService:
    """Сервис AI-советов для бизнеса."""

    def __init__(self, business_slug: str):
        self.slug = business_slug
        self.tenant_manager = get_tenant_manager()
        self.config = self.tenant_manager.get_business_config(business_slug)

        # Get API config
        self.api_key = self.config.get('POLZA_API_KEY', settings.POLZA_API_KEY)
        self.api_url = self.config.get('POLZA_API_URL', settings.POLZA_API_URL)
        self.model = self.config.get('POLZA_MODEL', 'gpt-4')

    def is_configured(self) -> bool:
        """Проверить, настроен ли AI."""
        return bool(self.api_key and self.api_url)

    def _call_api(self, messages: list, max_tokens: int = 1000) -> Optional[str]:
        """Вызов API polza.ai."""
        if not self.is_configured():
            return None

        try:
            import requests

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }

            data = {
                'model': self.model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': 0.7,
            }

            response = requests.post(
                f'{self.api_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f'AI API error: {response.status_code} - {response.text}')
                return None

        except Exception as e:
            logger.error(f'AI API exception: {e}')
            return None

    def analyze_sales(self, sales_data: dict) -> Optional[str]:
        """Анализ продаж и рекомендации."""
        prompt = f"""Ты аналитик для малого бизнеса. Проанализируй данные продаж и дай рекомендации.

Данные за последний месяц:
- Выручка: {sales_data.get('revenue', 0):,.0f} руб.
- Количество продаж: {sales_data.get('count', 0)}
- Средний чек: {sales_data.get('avg_check', 0):,.0f} руб.

Топ товаров:
{json.dumps(sales_data.get('top_products', []), ensure_ascii=False, indent=2)}

Дай 3-5 кратких рекомендаций на русском языке:
1. Что продавать больше
2. Как увеличить средний чек
3. Какие товары продвигать

Ответ кратко, 3-5 предложений."""

        messages = [
            {'role': 'system', 'content': 'Ты полезный аналитик для малого бизнеса.'},
            {'role': 'user', 'content': prompt},
        ]

        return self._call_api(messages, max_tokens=500)

    def forecast_stock(self, products_data: list) -> Optional[str]:
        """Прогноз остатков."""
        prompt = f"""Проанализируй остатки товаров и спрогнозируй, какие товары закончатся в ближайшие 2 недели.

Товары:
{json.dumps(products_data[:10], ensure_ascii=False, indent=2)}

Дай список товаров, которые нужно дозаказать, с приоритетом (высокий/средний/низкий).
Ответ кратко на русском языке."""

        messages = [
            {'role': 'system', 'content': 'Ты аналитик склада для малого бизнеса.'},
            {'role': 'user', 'content': prompt},
        ]

        return self._call_api(messages, max_tokens=500)

    def generate_report(self, report_data: dict, report_type: str = 'sales') -> Optional[str]:
        """Генерация текстового отчёта."""
        if report_type == 'sales':
            prompt = f"""Составь краткий отчёт по продажам на основе данных:

{json.dumps(report_data, ensure_ascii=False, indent=2)}

Отчёт должен включать:
1. Общую оценку
2. Динамику
3. Рекомендации

Ответ на русском языке, 5-7 предложений."""
        else:
            prompt = f"""Составь краткий отчёт по остаткам на складе:

{json.dumps(report_data, ensure_ascii=False, indent=2)}

Ответ на русском языке, 5-7 предложений."""

        messages = [
            {'role': 'system', 'content': 'Ты бизнес-аналитик.'},
            {'role': 'user', 'content': prompt},
        ]

        return self._call_api(messages, max_tokens=800)

    def chat(self, message: str, context: dict = None) -> Optional[str]:
        """Чат с AI по вопросам бизнеса."""
        system_prompt = """Ты полезный помощник для владельца малого бизнеса.
Отвечай на русском языке. Будь конкретным и практичным.
Если данных недостаточно, скажи об этом."""

        user_prompt = message
        if context:
            user_prompt += f"\n\nКонтекст бизнеса:\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]

        return self._call_api(messages, max_tokens=1000)


def get_ai_service(business_slug: str) -> AIService:
    """Получить экземпляр AIService для бизнеса."""
    return AIService(business_slug)
