from django.core.management.base import BaseCommand
from inventory.models import Category, Supplier, Product, Supply, Sale


class Command(BaseCommand):
    help = 'Удалить demo-данные из default БД (оставить только в tenant БД)'

    def handle(self, *args, **options):
        sales = Sale.objects.all().count()
        supplies = Supply.objects.all().count()
        products = Product.objects.all().count()
        suppliers = Supplier.objects.all().count()
        categories = Category.objects.all().count()

        Sale.objects.all().delete()
        Supply.objects.all().delete()
        Product.objects.all().delete()
        Supplier.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'Удалено из default БД: {sales} продаж, {supplies} поставок, '
            f'{products} товаров, {suppliers} поставщиков, {categories} категорий'
        ))
