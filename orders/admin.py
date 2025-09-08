from django.contrib import admin
from django.utils.safestring import mark_safe
import json

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["sku", "name", "line_total", "tax_amount", "discount_amount"]

    def has_add_permission(self, request, obj=None):
        # Allow adding only if order is draft
        if obj and obj.status != "draft":
            return False
        return True

    def has_change_permission(self, request, obj=None):
        # Allow editing only if order is draft
        if obj and obj.status != "draft":
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        # Allow deleting only if order is draft
        if obj and obj.status != "draft":
            return False
        return True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "reference",
        "user",
        "status",
        "total",
        "created_at",
        "updated_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["reference", "user__email"]

    inlines = [OrderItemInline]

    readonly_fields = [
        "reference",
        "user",
        "subtotal",
        "tax_total",
        "shipping_total",
        "discount_total",
        "total",
        "placed_at",
        "created_at",
        "updated_at",
        "billing_address_snapshot_pretty",
        "shipping_address_snapshot_pretty",
    ]

    fieldsets = (
        ("Order Info", {
            "fields": (
                "reference",
                "user",
                "status",
                "currency",
                ("subtotal", "tax_total", "shipping_total", "discount_total", "total"),
                "placed_at",
            )
        }),
        ("Addresses", {
            "fields": (
                "billing_address",
                "shipping_address",
                "billing_address_snapshot_pretty",
                "shipping_address_snapshot_pretty",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    # hide the add button in the admin UI
    def has_add_permission(self, request):
      return False

    def billing_address_snapshot_pretty(self, obj):
        if not obj.billing_address_snapshot:
            return "-"
        formatted = json.dumps(obj.billing_address_snapshot, indent=2)
        return mark_safe(f"<pre>{formatted}</pre>")
    billing_address_snapshot_pretty.short_description = "Billing Address Snapshot"

    def shipping_address_snapshot_pretty(self, obj):
        if not obj.shipping_address_snapshot:
            return "-"
        formatted = json.dumps(obj.shipping_address_snapshot, indent=2)
        return mark_safe(f"<pre>{formatted}</pre>")
    shipping_address_snapshot_pretty.short_description = "Shipping Address Snapshot"

    def get_readonly_fields(self, request, obj=None):
        """
        Lock billing/shipping fields for non-draft orders.
        """
        ro_fields = list(self.readonly_fields)
        if obj and obj.status != "draft":
            ro_fields += ["billing_address", "shipping_address"]
        return ro_fields
