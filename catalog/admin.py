from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Category, Brand, Product, ProductAttribute, ProductAttributeValue,
    ProductVariant, ProductImage
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class DeletedListFilter(admin.SimpleListFilter):
    title = _('Deleted')
    parameter_name = 'deleted'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Deleted')),
            ('no', _('Active')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(deleted_at__isnull=False)
        if self.value() == 'no':
            return queryset.filter(deleted_at__isnull=True)
        return queryset


class SoftDeleteAdmin(admin.ModelAdmin):
    exclude = ('deleted_at',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_filter = (DeletedListFilter, 'is_active')


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ('name', 'parent', 'is_active', 'is_featured', 'created_at', 'deleted_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(SoftDeleteAdmin):
    list_display = ('name', 'slug', 'is_active', 'website_url', 'created_at', 'deleted_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(SoftDeleteAdmin):
    list_display = ('sku', 'name', 'brand', 'price', 'discount_price', 'is_listed', 'is_featured', 'is_active')
    search_fields = ('sku', 'name', 'brand__name')
    list_filter = ('is_listed', 'is_featured', 'is_active', DeletedListFilter)
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('categories',)
    
    inlines = [ProductVariantInline, ProductImageInline]

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('attribute', 'value', 'sort_order', 'is_active')
    search_fields = ('value',)
    list_filter = ('attribute', 'is_active')


@admin.register(ProductVariant)
class ProductVariantAdmin(SoftDeleteAdmin):
    list_display = ('sku', 'name', 'product', 'price', 'stock_quantity', 'is_default', 'is_active')
    search_fields = ('sku', 'name', 'product__name')
    list_filter = ('is_default', 'is_active', DeletedListFilter)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'is_primary', 'sort_order')
    list_filter = ('is_primary',)
