import random
from datetime import timedelta, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import Business, BusinessMembership
from inventory.models import Category, Supplier, Product, Supply, Sale
from tenants.manager import get_tenant_manager


class Command(BaseCommand):
    help = 'Создать демо-бизнес Demo Leather с данными'

    def handle(self, *args, **options):
        self.stdout.write('Создаю демо-бизнес...')

        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin.set_password('admin123')
            admin.save()

        business, created = Business.objects.get_or_create(
            slug='demo',
            defaults={
                'name': 'Demo Leather',
                'business_type': 'retail',
                'owner': admin,
                'settings': {'business_name': 'Demo Leather', 'description': 'Уникальные кожаные изделия ручной работы'},
            }
        )
        if created:
            BusinessMembership.objects.create(business=business, user=admin, role='owner')

        tm = get_tenant_manager()
        tm.setup_business('demo', 'Demo Leather', 'retail')

        cats_data = [
            ('wallets', 'Кошельки', '👛'), ('phone-cases', 'Чехлы для телефонов', '📱'),
            ('belts', 'Ремни', '👔'), ('bags', 'Сумки', '👜'),
            ('watches', 'Часы', '⌚'), ('accessories', 'Аксессуары', '🔑'),
        ]
        cats = {}
        for slug, name, icon in cats_data:
            c, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'icon': icon})
            cats[slug] = c

        sups_data = [
            ('Итальянская Кожа', 'Милан, Италия', '+39 02 1234567'),
            ('Cuir Premium', 'Париж, Франция', '+33 1 2345678'),
            ('Ручная Работа Москва', 'Москва, Россия', '+7 495 1234567'),
            ('Heritage Leather Co.', 'Лондон, Великобритания', '+44 20 1234567'),
        ]
        sups = {}
        for name, contact, phone in sups_data:
            s, _ = Supplier.objects.get_or_create(name=name, defaults={'contact': contact, 'phone': phone})
            sups[name] = s
        sup_list = list(sups.values())

        prods_data = [
            ('WL-001', 'Кошелёк Classic Bifold', 'wallets', 4500, 8900, 25, 'Италия'),
            ('WL-002', 'Кошелёк Minimalist Card Holder', 'wallets', 2800, 5500, 40, 'Италия'),
            ('WL-003', 'Кошелёк RFID Safe Wallet', 'wallets', 5200, 9900, 15, 'Франция'),
            ('WL-004', 'Кошелёк Vintage Long Wallet', 'wallets', 6000, 12500, 8, 'Россия'),
            ('WL-005', 'Кошелёк Travel Document Organizer', 'wallets', 7500, 14900, 5, 'Великобритания'),
            ('PC-001', 'Чехол iPhone 15 Pro', 'phone-cases', 2200, 4500, 50, 'Италия'),
            ('PC-002', 'Чехол Samsung S24 Ultra', 'phone-cases', 2000, 4200, 35, 'Италия'),
            ('PC-003', 'Чехол MagSafe Compatible', 'phone-cases', 2500, 5000, 30, 'Франция'),
            ('PC-004', 'Чехол Book Style Case', 'phone-cases', 3000, 6500, 20, 'Россия'),
            ('PC-005', 'Чехол Wallet Case Premium', 'phone-cases', 3500, 7500, 12, 'Великобритания'),
            ('BL-001', 'Ремень Classic Belt', 'belts', 3500, 7500, 30, 'Италия'),
            ('BL-002', 'Ремень Reversible Belt', 'belts', 4000, 8500, 20, 'Франция'),
            ('BL-003', 'Ремень Braided Leather Belt', 'belts', 3800, 7900, 18, 'Россия'),
            ('BL-004', 'Ремень Executive Belt', 'belts', 5000, 10500, 10, 'Великобритания'),
            ('BG-001', 'Сумка Messenger Bag', 'bags', 8000, 16500, 8, 'Италия'),
            ('BG-002', 'Сумка Tote Bag', 'bags', 9500, 19900, 5, 'Франция'),
            ('BG-003', 'Сумка Laptop Sleeve 15"', 'bags', 5500, 11500, 15, 'Россия'),
            ('BG-004', 'Сумка Crossbody Bag', 'bags', 7000, 14500, 10, 'Великобритания'),
            ('WT-001', 'Часы Leather Strap Watch', 'watches', 12000, 24900, 6, 'Швейцария'),
            ('WT-002', 'Часы Minimalist Watch', 'watches', 15000, 29900, 4, 'Швейцария'),
            ('AC-001', 'Брелок Keychain Loop', 'accessories', 800, 1800, 60, 'Италия'),
            ('AC-002', 'Держатель для карт Card Holder', 'accessories', 1500, 3200, 45, 'Италия'),
            ('AC-003', 'Обложка для паспорта', 'accessories', 1800, 3800, 25, 'Россия'),
            ('AC-004', 'Чехол для очков', 'accessories', 2000, 4200, 15, 'Франция'),
            ('AC-005', 'Подставка для телефона', 'accessories', 1200, 2500, 30, 'Россия'),
        ]

        now = timezone.now()
        today = date.today()

        prods = {}
        for article, name, cat, buy, sell, qty, country in prods_data:
            p, _ = Product.objects.get_or_create(
                article=article,
                defaults={
                    'name': name, 'category': cats[cat], 'country': country,
                    'purchase_price': Decimal(str(buy)), 'sale_price': Decimal(str(sell)), 'quantity': 0,
                }
            )
            prods[article] = p

        for article, name, cat, buy, sell, qty, country in prods_data:
            arrival = today - timedelta(days=random.randint(10, 90))
            Supply.objects.get_or_create(
                serial_number=f'SN-{article}-001',
                defaults={
                    'supplier': random.choice(sup_list), 'product': prods[article], 'quantity': qty,
                    'purchase_price': Decimal(str(buy)), 'sale_price': Decimal(str(sell)),
                    'status': 'received', 'arrival_date': arrival,
                }
            )

        customers = [
            ('Алексей', 'Петров'), ('Мария', 'Иванова'), ('Дмитрий', 'Сидоров'),
            ('Елена', 'Козлова'), ('Сергей', 'Морозов'), ('Анна', 'Новикова'),
            ('Павел', 'Волков'), ('Ольга', 'Соколова'), ('Игорь', 'Лебедев'),
            ('Наталья', 'Попова'), ('Виктор', 'Зайцев'), ('Татьяна', 'Михайлова'),
            ('Роман', 'Фёдоров'), ('Ирина', 'Белова'), ('Андрей', 'Кузнецов'),
        ]

        sale_count = 0
        for article, name, cat, buy, sell, qty, country in prods_data:
            product = prods[article]
            qty_sold = random.randint(2, min(qty // 3, 12))
            for i in range(qty_sold):
                c = random.choice(customers)
                sale_date = today - timedelta(days=random.randint(0, 89))
                Sale.objects.create(
                    product=product, serial_number=f'SN-{article}-{i+1:03d}',
                    customer_name=f'{c[0]} {c[1]}', quantity=1, price=Decimal(str(sell)),
                    status='completed', date=sale_date,
                )
                sale_count += 1

        for p in Product.objects.all():
            p.recalculate_quantity()

        total_products = Product.objects.count()
        total_sales = Sale.objects.count()

        self.stdout.write(self.style.SUCCESS(f'Готово! {total_products} товаров, {total_sales} продаж'))
        self.stdout.write(f'Открой: http://demo.wms-ai.ru/login/')
