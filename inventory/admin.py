from django.contrib import admin
from .models import Category, Supplier, Product, Supply, Sale


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'created_at']
    search_fields = ['name', 'phone']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'article', 'category', 'purchase_price', 'sale_price', 'quantity', 'status']
    list_filter = ['status', 'category']
    search_fields = ['name', 'article']


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ['product', 'serial_number', 'supplier', 'quantity', 'status', 'arrival_date']
    list_filter = ['status', 'supplier']
    search_fields = ['serial_number', 'product__name']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['product', 'customer_name', 'quantity', 'price', 'date', 'status']
    list_filter = ['status', 'date']
    search_fields = ['customer_name', 'product__name']
