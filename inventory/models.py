from django.db import models
from django.db import transaction
from django.utils import timezone
from core.utils.common import SoftDeleteModel, TimeStampedModel

class Warehouse(TimeStampedModel, SoftDeleteModel):
    # company = models.ForeignKey("accounts.Company", null=True, blank=True, on_delete=models.CASCADE, related_name="warehouses")
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    address = models.TextField(blank=True)
    location_code = models.CharField(max_length=64, blank=True)  # physical location within warehouse
    contact_person = models.CharField(max_length=128, blank=True)

    timezone = models.CharField(max_length=64, default='UTC')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Inventory(TimeStampedModel):
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.CASCADE, related_name='inventory')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='inventories')
    
    # Stock state
    on_hand = models.BigIntegerField(default=0)
    reserved = models.BigIntegerField(default=0)  # reserved for orders
    allocated = models.BigIntegerField(default=0)  # allocated to confirmed orders
    incoming = models.BigIntegerField(default=0)  # POs expected
    safety_stock = models.BigIntegerField(default=0)
    
    # batch/expiry tracking
    lot = models.CharField(max_length=128, null=True, blank=True)  # optional for batch tracking
    batch_number = models.CharField(max_length=64, null=True, blank=True)
    manufactured_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    
    # unit of measure
    uom = models.CharField(max_length=20, default="pcs")
    
    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("ON_HOLD", "On Hold"),
        ("DAMAGED", "Damaged"),
        ("EXPIRING_SOON", "Expiring Soon"),
        ("EXPIRED", "Expired"),
        ("QUARANTINE", "Quarantine"),
        ("RETURNED", "Returned"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AVAILABLE")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = (('variant','warehouse'),)
        indexes = [
            models.Index(fields=['variant','warehouse']), 
            models.Index(fields=["status"]),
            models.Index(fields=['lot']), 
            models.Index(fields=['expiration_date']),
        ]

    def available(self):
        """Available to sell (ATS) = On Hand - Reserved - Allocated"""
        return max(0, self.on_hand - self.reserved - self.allocated)

    def reserve(self, qty, *, reference=None, user=None):
        """Reserve stock temporarily (e.g., for cart / unconfirmed order)."""
        if qty <= 0:
            raise ValueError("qty must be positive")
        
        with transaction.atomic():
            inv = Inventory.objects.select_for_update().get(pk=self.pk)
            if inv.available() < qty:
                raise Exception("Insufficient stock to reserve")
            
            inv.reserved += qty
            inv.save()

            InventoryTransaction.objects.create(
                transaction_type='reservation',
                variant=inv.variant,
                warehouse=inv.warehouse,
                quantity_delta=-qty,
                resulting_on_hand=inv.on_hand,
                resulting_reserved=inv.reserved,
                resulting_allocated=inv.allocated,
                reference=reference,
                created_by=user,
            )
            return inv

    def release(self, qty, *, reference=None, user=None):
        """Release reserved stock (e.g., cart abandoned / order cancelled)."""
        if qty <= 0:
            raise ValueError("qty must be positive")

        with transaction.atomic():
            inv = Inventory.objects.select_for_update().get(pk=self.pk)
            if inv.reserved < qty:
                raise Exception("Not enough reserved stock to release")
            
            inv.reserved -= qty
            inv.save()

            InventoryTransaction.objects.create(
                transaction_type='release',
                variant=inv.variant,
                warehouse=inv.warehouse,
                quantity_delta=qty,
                resulting_on_hand=inv.on_hand,
                resulting_reserved=inv.reserved,
                resulting_allocated=inv.allocated,
                reference=reference,
                created_by=user,
            )
            return inv
        
    def allocate(self, qty, *, reference=None, user=None):
        """
            Move stock from reserved → allocated 
            (e.g., order confirmed/paid).
        """
        if qty <= 0:
            raise ValueError("qty must be positive")
        
        with transaction.atomic():
            inv = Inventory.objects.select_for_update().get(pk=self.pk)
            if inv.reserved < qty:
                raise Exception("Insufficient reserved stock to allocate")
            
            inv.reserved -= qty
            inv.allocated += qty
            inv.save()

            InventoryTransaction.objects.create(
                transaction_type='allocation',
                variant=inv.variant,
                warehouse=inv.warehouse,
                quantity_delta=0,
                resulting_on_hand=inv.on_hand,
                resulting_reserved=inv.reserved,
                resulting_allocated=inv.allocated,
                reference=reference,
                created_by=user
            )
            return inv

class InventoryTransaction(TimeStampedModel):
    TRANSACTION_CHOICES = [
        ("receipt", "Receipt"),           # stock in from purchase/production
        ("sale", "Sale"),                 # stock out to customer
        ("adjustment", "Adjustment"),     # manual correction
        ("allocation", "Allocation"),     # reserved for order
        ("unallocation", "Unallocation"), # release reservation
        ("reservation", "Reservation"),
        ("release", "Release"),
        ("transfer_in", "Transfer In"),
        ("transfer_out", "Transfer Out"),
        ("return", "Return"),             # customer return
    ]

    transaction_type = models.CharField(max_length=32, choices=TRANSACTION_CHOICES)
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    
    # Movement
    quantity_delta = models.BigIntegerField()  # positive or negative
    resulting_on_hand = models.BigIntegerField()
    resulting_reserved = models.BigIntegerField()
    resulting_allocated = models.BigIntegerField(default=0)

    # Cost tracking (only relevant for receipts/purchases)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")

    # References to business documents
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.SET_NULL)
    shipment = models.ForeignKey('shipping.Shipment', null=True, blank=True, on_delete=models.SET_NULL)
    return_record = models.ForeignKey('returns.ReturnRequest', null=True, blank=True, on_delete=models.SET_NULL)
    
    # reference_id = models.UUIDField(null=True, blank=True, db_index=True)
    reference = models.CharField(max_length=255, null=True, blank=True)
    source_document = models.CharField(max_length=100, null=True, blank=True)
    notes = models.CharField(max_length=255, null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=['variant','warehouse','created_at']),
            models.Index(fields=["transaction_type"]),
        ]

    def save(self, *args, **kwargs):
        """Make transaction immutable after creation."""
        if self.pk:
            raise ValueError("InventoryTransaction records cannot be updated once created.")
        super().save(*args, **kwargs)