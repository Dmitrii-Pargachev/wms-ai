from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PriceHistory(models.Model):
    """История изменений цен."""
    PRICE_TYPES = [
        ('purchase', 'Закупка'),
        ('sale', 'Продажа'),
    ]

    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE,
                                 verbose_name='Товар', related_name='price_history')
    price_type = models.CharField('Тип цены', max_length=10, choices=PRICE_TYPES)
    old_price = models.DecimalField('Старая цена', max_digits=10, decimal_places=2)
    new_price = models.DecimalField('Новая цена', max_digits=10, decimal_places=2)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name='Кто изменил')
    created_at = models.DateTimeField('Дата изменения', auto_now_add=True)

    class Meta:
        verbose_name = 'История цен'
        verbose_name_plural = 'История цен'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name}: {self.old_price} → {self.new_price}"

    @property
    def difference(self):
        return self.new_price - self.old_price

    @property
    def percent_change(self):
        if self.old_price == 0:
            return 0
        return round((self.new_price - self.old_price) / self.old_price * 100, 1)


class StockAlert(models.Model):
    """Оповещение о низком остатке."""
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE,
                                 verbose_name='Товар', related_name='stock_alerts')
    threshold = models.IntegerField('Порог', default=5)
    is_active = models.BooleanField('Активно', default=True)
    last_notified = models.DateTimeField('Последнее уведомление', null=True, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Оповещение о остатках'
        verbose_name_plural = 'Оповещения о остатках'

    def __str__(self):
        return f"{self.product.name} < {self.threshold}"
