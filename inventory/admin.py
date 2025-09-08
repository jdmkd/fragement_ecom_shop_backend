from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Warehouse, Inventory, InventoryTransaction


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "timezone")
    search_fields = ("code", "name", "address")
    list_filter = ("is_active", "timezone")
    readonly_fields = ("created_at", "updated_at", "deleted_at")


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "warehouse", "on_hand", "reserved", "allocated", "incoming", "status")
    search_fields = ("variant__sku", "variant__name", "warehouse__code", "lot", "batch_number")
    list_filter = ("status","warehouse")
    readonly_fields = ("created_at", "updated_at")
    # autocomplete_fields = ("variant", "warehouse")
    fieldsets = (
        (None, {
            "fields": ("variant", "warehouse", "uom", "status")
        }),
        ("Stock", {
            "fields": ("on_hand", "reserved", "allocated", "incoming", "safety_stock")
        }),
        ("Tracking", {
            "fields": ("lot", "batch_number", "manufactured_date", "expiration_date")
        }),
        ("Meta", {
            "fields": ("metadata", "created_at", "updated_at")
        }),
    )


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction_type", "variant", "warehouse", "quantity_delta", "created_at", "created_by")
    search_fields = ("variant__sku", "variant__name", "reference", "source_document")
    list_filter = ("transaction_type", "warehouse", "created_at")
    # autocomplete_fields = ("variant", "warehouse", "order", "shipment", "return_record", "created_by")
    readonly_fields = ("transaction_type", "variant", "warehouse", "quantity_delta",
                       "resulting_on_hand", "resulting_reserved", "resulting_allocated",
                       "cost_price", "currency", "order", "shipment", "return_record",
                       "reference", "source_document", "notes", "metadata",
                       "created_by", "created_at", "updated_at")
    # We make transaction admin mostly read-only; creation via code recommended.
