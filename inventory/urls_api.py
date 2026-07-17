from django.urls import path, include
from . import api_views
from inventory import catalog_views
from inventory import order_views

urlpatterns = [
    # Categories
    path('categories/', api_views.categories_list, name='api_categories'),
    path('categories/create/', api_views.category_create, name='api_category_create'),
    path('categories/<int:pk>/delete/', api_views.category_delete, name='api_category_delete'),

    # Suppliers
    path('suppliers/', api_views.suppliers_list, name='api_suppliers'),
    path('suppliers/create/', api_views.supplier_create, name='api_supplier_create'),

    # Products
    path('products/', api_views.products_list, name='api_products'),
    path('products/create/', api_views.product_create, name='api_product_create'),
    path('products/<int:pk>/', api_views.product_detail, name='api_product_detail'),
    path('products/<int:pk>/update/', api_views.product_update, name='api_product_update'),
    path('products/<int:pk>/delete/', api_views.product_delete, name='api_product_delete'),

    # Supplies
    path('supplies/', api_views.supplies_list, name='api_supplies'),
    path('supplies/create/', api_views.supply_create, name='api_supply_create'),

    # Sales
    path('sales/', api_views.sales_list, name='api_sales'),
    path('sales/create/', api_views.sale_create, name='api_sale_create'),

    # Search
    path('stock-serials/', api_views.stock_serials, name='api_stock_serials'),
    path('catalog-lookup/', api_views.catalog_lookup, name='api_catalog_lookup'),

    # Custom tables (constructor)
    path('custom/', include('accounts.custom_urls')),

    # Catalog (public)
    path('catalog/products/', catalog_views.catalog_products_api, name='catalog_products'),
    path('catalog/order/', catalog_views.catalog_order_api, name='catalog_order'),

    # Orders
    path('orders/', order_views.orders_api, name='orders_api'),
    path('orders/<int:order_id>/status/', order_views.order_update_status, name='order_update_status'),
]
