from django.urls import path
from . import custom_views
from . import client_views

urlpatterns = [
    # Clients
    path('clients/', client_views.clients_list, name='api_clients_list'),
    path('clients/create/', client_views.client_create, name='api_client_create'),
    path('clients/<int:client_id>/delete/', client_views.client_delete, name='api_client_delete'),
    # Custom tables
    path('tables/', custom_views.tables_list, name='custom_tables_list'),
    path('tables/create/', custom_views.table_create, name='custom_table_create'),
    path('tables/<int:table_id>/', custom_views.table_detail, name='custom_table_detail'),
    path('tables/<int:table_id>/delete/', custom_views.table_delete, name='custom_table_delete'),
    path('tables/<int:table_id>/fields/create/', custom_views.field_create, name='custom_field_create'),
    path('tables/<int:table_id>/fields/<int:field_id>/delete/', custom_views.field_delete, name='custom_field_delete'),
    path('tables/<int:table_id>/rows/', custom_views.rows_list, name='custom_rows_list'),
    path('tables/<int:table_id>/rows/create/', custom_views.row_create, name='custom_row_create'),
    path('tables/<int:table_id>/rows/<int:row_id>/update/', custom_views.row_update, name='custom_row_update'),
    path('tables/<int:table_id>/rows/<int:row_id>/delete/', custom_views.row_delete, name='custom_row_delete'),
    path('tables/<int:table_id>/import/', custom_views.rows_import, name='custom_rows_import'),
    path('tables/<int:table_id>/export/', custom_views.rows_export, name='custom_rows_export'),
]
