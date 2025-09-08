from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import Address, User

class AddressInline(admin.TabularInline):
    model = Address
    extra = 0

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('fullname', 'email', 'phonenumber', 'profile_image')}),
        ('OTP Information', {'fields': ('otp', 'otp_expiry')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'is_verified')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'fullname', 'email', 'phonenumber', 'password1', 'password2')
        }),
        # (None, {'fields': ('username', 'fullname', 'email', 'phonenumber', 'password', 'password2', 'is_staff', 'is_active')}),
    )
    list_display = ('username', 'email', 'fullname', 'is_staff', 'is_verified')
    search_fields = ('username', 'email', 'fullname')
    ordering = ('id', ) #'username',
    filter_horizontal = ()

    inlines = [AddressInline]

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'address_type', 
        'address_line1', 
        'city', 
        'state', 
        'country', 
        'postal_code', 
        'is_default'
    )
    list_filter = ('address_type', 'is_default', 'country', 'state')
    search_fields = ('user__username', 'user__email', 'address_line1', 'city', 'postal_code')
    ordering = ('user', 'is_default', 'id')