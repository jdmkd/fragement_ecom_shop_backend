from django.contrib import admin
from .models import Cart, CartItem, PriceSnapshot


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_id", "status", "grand_total", "updated_at")
    list_filter = ("status", "is_active", "updated_at")
    search_fields = ("user__email", "session_id")
    readonly_fields = ("grand_total", "created_at", "updated_at")  # secure
    ordering = ("-updated_at",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "variant", "quantity", "line_total", "updated_at")
    list_filter = ("cart", "updated_at")
    search_fields = ("variant__sku", "cart__session_id", "cart__user__email")
    readonly_fields = ("line_total", "created_at", "updated_at")  # secure


@admin.register(PriceSnapshot)
class PriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "amount", "currency", "source", "valid_from", "valid_to")
    list_filter = ("currency", "source")
    search_fields = ("source",)
    readonly_fields = ("created_at", "updated_at")
