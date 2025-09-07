from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('fullname', 'email', 'phonenumber', 'profile_image')}),
        ('OTP Information', {'fields': ('otp', 'otp_expiry')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'is_verified')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'fields': ('username', 'fullname', 'email', 'phonenumber', 'password', 'password2')}),
    )
    list_display = ('username', 'email', 'fullname', 'is_staff', 'is_verified')
    search_fields = ('username', 'email', 'fullname')
    ordering = ('username',)
    filter_horizontal = ()