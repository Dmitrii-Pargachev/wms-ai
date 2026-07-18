from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """Категория товаров (создаётся пользователем)."""
    business = models.ForeignKey('accounts.Business', on_delete=models.CASCADE,
                                  related_name='categories', verbose_name='Бизнес', null=True, blank=True)
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('URL', max_length=100)
    icon = models.CharField('Иконка', max_length=10, blank=True, default='')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']
        unique_together = [['business', 'slug']]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Поставщик."""
    business = models.ForeignKey('accounts.Business', on_delete=models.CASCADE,
                                  related_name='suppliers', verbose_name='Бизнес', null=True, blank=True)
    name = models.CharField('Название', max_length=200)
    contact = models.TextField('Контакт', blank=True, default='')
    phone = models.CharField('Телефон', max_length=50, blank=True, default='')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']
        unique_together = [['business', 'name']]

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар на складе."""
    STATUS_CHOICES = [
        ('instock', 'В наличии'),
        ('low', 'Мало'),
        ('out', 'Нет в наличии'),
    ]

    business = models.ForeignKey('accounts.Business', on_delete=models.CASCADE,
                                  related_name='products', verbose_name='Бизнес', null=True, blank=True)
    article = models.CharField('Артикул', max_length=50, blank=True, default='')
    name = models.CharField('Название', max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name='Категория', related_name='products')
    country = models.CharField('Страна', max_length=100, blank=True, default='')
    purchase_price = models.DecimalField('Цена закупки', max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField('Цена продажи', max_digits=10, decimal_places=2, default=0)
    quantity = models.IntegerField('Количество', default=0)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='instock')
    custom_fields = models.JSONField('Кастомные поля', default=dict, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.article})" if self.article else self.name

    def update_status(self):
        if self.quantity <= 0:
            self.status = 'out'
        elif self.quantity < 10:
            self.status = 'low'
        else:
            self.status = 'instock'
        self.save(update_fields=['status', 'quantity'])

    def recalculate_quantity(self):
        from django.db.models import Sum
        received = self.supplies.filter(status='received').aggregate(
            total=Sum('quantity')
        )['total'] or 0
        sold = self.sales.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        self.quantity = received - sold
        self.update_status()
        return self.quantity


class Supply(models.Model):
    """Поставка товара."""
    STATUS_CHOICES = [
        ('pending', 'Ожидается'),
        ('received', 'Получено'),
        ('cancelled', 'Отменено'),
    ]

    business = models.ForeignKey('accounts.Business', on_delete=models.CASCADE,
                                  related_name='supplies', verbose_name='Бизнес', null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE,
                                  verbose_name='Поставщик', related_name='supplies')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                 verbose_name='Товар', related_name='supplies')
    serial_number = models.CharField('Серийный номер', max_length=50)
    quantity = models.IntegerField('Количество', default=1)
    purchase_price = models.DecimalField('Цена закупки', max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField('Цена продажи', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='received')
    arrival_date = models.DateField('Дата поступления', default=timezone.now)
    buyer = models.CharField('Покупатель', max_length=200, blank=True, default='')
    sale_date = models.DateField('Дата продажи', null=True, blank=True)
    payment_status = models.CharField('Статус оплаты', max_length=50, blank=True, default='')
    custom_fields = models.JSONField('Кастомные поля', default=dict, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.serial_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.recalculate_quantity()


class Sale(models.Model):
    """Продажа товара."""
    STATUS_CHOICES = [
        ('completed', 'Завершена'),
        ('pending', 'Заказ в работе'),
        ('cancelled', 'Отменена'),
    ]

    business = models.ForeignKey('accounts.Business', on_delete=models.CASCADE,
                                  related_name='sales', verbose_name='Бизнес', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                 verbose_name='Товар', related_name='sales')
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name='Поставка', related_name='sales')
    serial_number = models.CharField('Серийный номер', max_length=50, blank=True, default='')
    customer_name = models.CharField('Клиент', max_length=200, blank=True, default='')
    customer_contact = models.CharField('Контакт клиента', max_length=200, blank=True, default='')
    quantity = models.IntegerField('Количество', default=1)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='completed')
    date = models.DateField('Дата продажи', default=timezone.now)
    employee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='Сотрудник', related_name='sales')
    custom_fields = models.JSONField('Кастомные поля', default=dict, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Продажа'
        verbose_name_plural = 'Продажи'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.customer_name}"

    @property
    def total(self):
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.supply and self.supply.status == 'received':
            self.supply.status = 'sold'
            self.supply.sale_date = self.date
            self.supply.save(update_fields=['status', 'sale_date'])
        self.product.recalculate_quantity()


class Order(models.Model):
    """Заказ с публичного сайта."""
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В работе'),
        ('completed', 'Выполнен'),
    ]

    business = models.ForeignKey('accounts.Business', on_delete=models.CASCADE,
                                 related_name='orders', verbose_name='Бизнес')
    customer_name = models.CharField('Имя клиента', max_length=200)
    customer_phone = models.CharField('Телефон клиента', max_length=20)
    customer_email = models.EmailField('Email клиента', blank=True, default='')
    comment = models.TextField('Комментарий', blank=True, default='')
    items = models.JSONField('Товары', default=list)
    total = models.DecimalField('Сумма', max_digits=12, decimal_places=2, default=0)
    status = models.CharField('Статус', max_length=15, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} — {self.customer_name} ({self.total} ₽)"

    def deduct_stock(self):
        from django.utils import timezone as tz
        for item in self.items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)
            if not product_id:
                continue
            try:
                product = Product.objects.get(id=product_id, business=self.business)
                product.quantity = max(0, product.quantity - quantity)
                product.update_status()
                Sale.objects.create(
                    business=self.business,
                    product=product,
                    customer_name=self.customer_name,
                    customer_contact=self.customer_phone,
                    quantity=quantity,
                    price=price,
                    status='pending',
                    date=tz.now().date(),
                    custom_fields={'order_id': self.id},
                )
            except Product.DoesNotExist:
                continue

    def complete_sales(self):
        Sale.objects.filter(
            business=self.business,
            custom_fields__order_id=self.id,
            status='pending'
        ).update(status='completed')
