from django.urls import path
from django.shortcuts import render
from . import views
from . import notification_views

urlpatterns = [
    path('landing/', views.landing_view, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('create-business/', views.create_business_view, name='create_business'),
    path('super-admin/', views.admin_businesses_view, name='admin_businesses'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('privacy/', lambda r: render(r, 'privacy.html'), name='privacy_policy'),
    # API
    path('api/business/', views.api_business_info, name='api_business_info'),
    path('api/business/settings/', views.api_update_business_settings, name='api_business_settings'),
    path('api/business/<int:business_id>/toggle/', views.api_toggle_business, name='api_toggle_business'),
    path('api/users/', views.api_users_list, name='api_users_list'),
    path('api/users/check-username/', views.api_check_username, name='api_check_username'),
    path('api/users/create/', views.api_create_user, name='api_create_user'),
    path('api/users/<int:user_id>/toggle/', views.api_toggle_user, name='api_toggle_user'),
    path('api/users/<int:user_id>/delete/', views.api_delete_user, name='api_delete_user'),
    path('api/members/<int:membership_id>/update/', views.api_update_member, name='api_update_member'),
    path('api/check-slug/', views.api_check_slug, name='api_check_slug'),
    path('api/check-business-name/', views.api_check_business_name, name='api_check_business_name'),
    path('api/check-email/', views.api_check_email, name='api_check_email'),
    path('api/logs/', views.api_logs, name='api_logs'),
    path('api/upload-avatar/', views.upload_avatar_api, name='upload_avatar_api'),
    path('api/settings/site/', views.save_site_settings_api, name='save_site_settings'),
    # Notifications
    path('api/notifications/', notification_views.notifications_list, name='api_notifications_list'),
    path('api/notifications/read-all/', notification_views.notifications_mark_all_read, name='api_notifications_read_all'),
    path('api/notifications/<int:notification_id>/read/', notification_views.notification_mark_read, name='api_notification_read'),
]
