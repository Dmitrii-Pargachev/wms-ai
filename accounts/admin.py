from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Business, BusinessMembership


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'business_type', 'owner', 'phone', 'city', 'is_active', 'created_at']
    list_filter = ['business_type', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'owner__username', 'phone', 'city', 'email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Основное', {'fields': ('name', 'slug', 'business_type', 'owner', 'is_active')}),
        ('Контакты', {'fields': ('phone', 'email', 'city', 'address')}),
        ('Подробности', {'fields': ('industry', 'employees', 'warehouse_area', 'description')}),
        ('Системное', {'fields': ('settings', 'created_at', 'updated_at')}),
    )


@admin.register(BusinessMembership)
class BusinessMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'business', 'role', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'business__name']


class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active']


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
