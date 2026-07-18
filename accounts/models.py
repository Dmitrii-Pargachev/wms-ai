import secrets
from django.db import models
from django.contrib.auth.models import User


class Business(models.Model):
    BUSINESS_TYPES = [
        ('retail', 'Розничная торговля'),
        ('wholesale', 'Оптовая торговля'),
        ('services', 'Услуги'),
        ('production', 'Производство'),
        ('other', 'Другое'),
    ]

    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('URL-идентификатор', unique=True, max_length=100)
    business_type = models.CharField('Тип бизнеса', max_length=20, choices=BUSINESS_TYPES, default='retail')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_businesses', verbose_name='Владелец')
    settings = models.JSONField('Настройки', default=dict, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    phone = models.CharField('Телефон', max_length=20, blank=True, default='')
    email = models.EmailField('Email бизнеса', blank=True, default='')
    city = models.CharField('Город', max_length=100, blank=True, default='')
    address = models.CharField('Адрес', max_length=300, blank=True, default='')
    industry = models.CharField('Отрасль', max_length=100, blank=True, default='')
    employees = models.PositiveIntegerField('Количество сотрудников', null=True, blank=True)
    warehouse_area = models.CharField('Площадь склада', max_length=50, blank=True, default='')
    description = models.TextField('Описание', blank=True, default='')

    # Site settings
    site_title = models.CharField('Заголовок сайта', max_length=200, blank=True, default='')
    site_description = models.TextField('Описание сайта', blank=True, default='')
    site_phone = models.CharField('Телефон сайта', max_length=20, blank=True, default='')
    site_email = models.EmailField('Email сайта', blank=True, default='')
    site_address = models.CharField('Адрес сайта', max_length=300, blank=True, default='')
    site_work_hours = models.CharField('Часы работы', max_length=100, blank=True, default='Пн–Пт, 9:00–18:00')
    site_color_scheme = models.JSONField('Цветовая схема', default=dict, blank=True)

    class Meta:
        verbose_name = 'Бизнес'
        verbose_name_plural = 'Бизнесы'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save(update_fields=['settings'])


class BusinessMembership(models.Model):
    ROLES = [
        ('owner', 'Владелец'),
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('viewer', 'Наблюдатель'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='memberships', verbose_name='Бизнес')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_memberships', verbose_name='Пользователь')
    role = models.CharField('Роль', max_length=20, choices=ROLES, default='viewer')
    phone = models.CharField('Телефон', max_length=20, blank=True, default='')
    note = models.TextField('Заметка', blank=True, default='')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Участник бизнеса'
        verbose_name_plural = 'Участники бизнеса'
        unique_together = ['business', 'user']
        ordering = ['business', 'user']

    def __str__(self):
        return f"{self.user.username} -> {self.name} ({self.role})"

    @property
    def name(self):
        return self.business.name

    def is_admin_or_above(self):
        return self.role in ('owner', 'admin')

    def is_manager_or_above(self):
        return self.role in ('owner', 'admin', 'manager')


class EmailVerification(models.Model):
    """Stores pending registration data. Link works on any device."""
    token = models.CharField('Токен', max_length=64, unique=True, db_index=True)
    data = models.JSONField('Данные регистрации', default=dict)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    is_used = models.BooleanField('Использован', default=False)

    class Meta:
        verbose_name = 'Подтверждение email'
        verbose_name_plural = 'Подтверждения email'

    def __str__(self):
        return f'{self.data.get("email", "?")} — {"использован" if self.is_used else "ожидает"}'

    @staticmethod
    def generate_token():
        return secrets.token_hex(16)


class Log(models.Model):
    """Журнал активности бизнеса."""
    TYPE_CHOICES = [
        ('sale', 'Продажа'),
        ('supply', 'Поставка'),
        ('product', 'Товар'),
        ('price', 'Цена'),
        ('auth', 'Вход'),
        ('user', 'Сотрудник'),
        ('settings', 'Настройки'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='logs', verbose_name='Бизнес')
    type = models.CharField('Тип', max_length=15, choices=TYPE_CHOICES)
    action = models.TextField('Действие')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Журнал'
        verbose_name_plural = 'Журналы'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type}] {self.action}"

    @staticmethod
    def log(business, log_type, action, user=None):
        """Хелпер для создания записи лога."""
        return Log.objects.create(business=business, type=log_type, action=action, user=user)


class TableSchema(models.Model):
    """Определение пользовательской таблицы."""
    ENTITY_TYPES = [
        ('product', 'Товар'),
        ('supply', 'Поставка'),
        ('sale', 'Продажа'),
        ('custom', 'Пользовательская'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='custom_tables', verbose_name='Бизнес')
    entity_type = models.CharField('Тип сущности', max_length=20, choices=ENTITY_TYPES, default='custom')
    name = models.CharField('Название', max_length=100)
    icon = models.CharField('Иконка', max_length=10, default='📋')
    db_table_name = models.CharField('Имя таблицы в БД', max_length=63, unique=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        verbose_name = 'Пользовательская таблица'
        verbose_name_plural = 'Пользовательские таблицы'
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class FieldSchema(models.Model):
    """Определение поля в таблице."""
    FIELD_TYPES = [
        ('text', 'Текст'),
        ('number', 'Число'),
        ('date', 'Дата'),
        ('select', 'Выбор'),
        ('multiselect', 'Мультивыбор'),
        ('boolean', 'Да/Нет'),
        ('email', 'Email'),
        ('phone', 'Телефон'),
        ('url', 'Ссылка'),
        ('file', 'Файл'),
        ('relation', 'Связь'),
    ]

    table = models.ForeignKey(TableSchema, on_delete=models.CASCADE, related_name='fields', verbose_name='Таблица')
    name = models.CharField('Название', max_length=100)
    field_type = models.CharField('Тип', max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField('Обязательное', default=False)
    options = models.JSONField('Варианты', default=list, blank=True)
    related_table = models.ForeignKey(TableSchema, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Связанная таблица')
    position = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Поле таблицы'
        verbose_name_plural = 'Поля таблиц'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.table.name}.{self.name}"


class RelationSchema(models.Model):
    """Связь между таблицами."""
    RELATION_TYPES = [
        ('one_to_many', 'Один-ко-многим'),
        ('many_to_many', 'Многие-ко-многим'),
    ]

    from_table = models.ForeignKey(TableSchema, on_delete=models.CASCADE, related_name='outgoing_relations', verbose_name='Исходная таблица')
    to_table = models.ForeignKey(TableSchema, on_delete=models.CASCADE, related_name='incoming_relations', verbose_name='Целевая таблица')
    from_field = models.CharField('Поле в исходной', max_length=100)
    to_field = models.CharField('Поле в целевой', max_length=100)
    rel_type = models.CharField('Тип связи', max_length=20, choices=RELATION_TYPES)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Связь таблиц'
        verbose_name_plural = 'Связи таблиц'

    def __str__(self):
        return f"{self.from_table.name}.{self.from_field} → {self.to_table.name}.{self.to_field}"


class Client(models.Model):
    """Клиент бизнеса."""
    SOCIAL_CHOICES = [
        ('telegram', 'Telegram'),
        ('max', 'Max'),
        ('whatsapp', 'WhatsApp'),
        ('vk', 'VK'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='clients', verbose_name='Бизнес')
    phone = models.CharField('Телефон', max_length=20)
    social_network = models.CharField('Соцсеть', max_length=10, choices=SOCIAL_CHOICES, default='telegram')
    social_username = models.CharField('Юзернейм', max_length=100, blank=True, default='')
    first_name = models.CharField('Имя', max_length=100)
    last_name = models.CharField('Фамилия', max_length=100, blank=True, default='')
    total_spent = models.DecimalField('Общая сумма покупок', max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-total_spent']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"

    @property
    def status(self):
        if self.total_spent >= 500:
            return 'vip'
        elif self.total_spent >= 200:
            return 'valuable'
        return 'usual'

    @property
    def status_display(self):
        return {'usual': 'Обычный', 'valuable': 'Ценный', 'vip': 'VIP'}[self.status]

    def recalc_total(self):
        from django.db.models import Sum
        from inventory.models import Sale
        total = Sale.objects.filter(
            business=self.business,
            customer_name__icontains=self.first_name,
            status='completed'
        ).aggregate(total=Sum('price'))['total'] or 0
        self.total_spent = total
        self.save(update_fields=['total_spent'])


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.CharField('Аватар', max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f"Profile: {self.user.username}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('low_stock', 'Низкий остаток'),
        ('out_of_stock', 'Нет в наличии'),
        ('sale', 'Продажа'),
        ('supply', 'Поставка'),
        ('revenue', 'Выручка'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    type = models.CharField('Тип', max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField('Заголовок', max_length=200)
    message = models.TextField('Сообщение', blank=True, default='')
    is_read = models.BooleanField('Прочитано', default=False)
    key = models.CharField('Ключ дедупликации', max_length=200, blank=True, default='')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type}: {self.title}"
