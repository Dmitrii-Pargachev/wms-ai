from django.urls import path
from . import views

urlpatterns = [
    path('exchange-rate/', views.exchange_rate, name='api_exchange_rate'),
]
