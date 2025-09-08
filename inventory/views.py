from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Warehouse, Inventory, InventoryTransaction
from .serializers import (
    WarehouseSerializer,
    InventorySerializer,
    InventoryTransactionSerializer,
    InventoryActionSerializer,
)
from core.utils.response_utils import api_response


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.filter(is_active=True)
    serializer_class = WarehouseSerializer
    permission_classes = [IsAdminUser]  # manage warehouses only by admin


class InventoryViewSet(viewsets.ModelViewSet):
    """
    Manage inventory records (one per variant+warehouse).
    - Non-admin users should not change on_hand directly via API in typical setups.
    - We allow retrieval for authenticated users; writing/editing is admin-only.
    """
    queryset = Inventory.objects.select_related("variant", "warehouse").all()
    serializer_class = InventorySerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        # create/update/delete reserved for admins
        return [IsAdminUser()]

    @action(detail=True, methods=["post"], url_path="reserve", permission_classes=[IsAuthenticated])
    def reserve_action(self, request, pk=None):
        """
        Reserve stock temporarily for a cart/order.
        POST body: {"qty": 2, "reference": "cart:123"}
        """
        inv = self.get_object()
        serializer = InventoryActionSerializer(data=request.data)
        # set querysets for nested fields if needed (not necessary usually)
        if not serializer.is_valid():
            return api_response(False, status=400, message="Invalid input", errors=serializer.errors)

        qty = serializer.validated_data["qty"]
        reference = serializer.validated_data.get("reference", None)
        user = request.user if request.user.is_authenticated else None

        try:
            inv = inv.reserve(qty, reference=reference, user=user)
        except Exception as exc:
            return api_response(False, status=400, message=str(exc))

        inv_ser = InventorySerializer(inv, context={"request": request})
        # fetch the latest transactions for this inventory (most recent)
        txn = InventoryTransaction.objects.filter(variant=inv.variant, warehouse=inv.warehouse).order_by("-created_at").first()
        txn_ser = InventoryTransactionSerializer(txn, context={"request": request}) if txn else None

        return api_response(True, status=200, message="Reserved", data={"inventory": inv_ser.data, "transaction": txn_ser.data if txn_ser else None})

    @action(detail=True, methods=["post"], url_path="release", permission_classes=[IsAuthenticated])
    def release_action(self, request, pk=None):
        """
        Release previously reserved stock (e.g., cart abandoned).
        POST body: {"qty": 2, "reference": "cart:123"}
        """
        inv = self.get_object()
        serializer = InventoryActionSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(False, status=400, message="Invalid input", errors=serializer.errors)

        qty = serializer.validated_data["qty"]
        reference = serializer.validated_data.get("reference", None)
        user = request.user if request.user.is_authenticated else None

        try:
            inv = inv.release(qty, reference=reference, user=user)
        except Exception as exc:
            return api_response(False, status=400, message=str(exc))

        txn = InventoryTransaction.objects.filter(variant=inv.variant, warehouse=inv.warehouse).order_by("-created_at").first()
        return api_response(True, status=200, message="Released", data={"inventory": InventorySerializer(inv).data, "transaction": InventoryTransactionSerializer(txn).data if txn else None})

    @action(detail=True, methods=["post"], url_path="allocate", permission_classes=[IsAuthenticated])
    def allocate_action(self, request, pk=None):
        """
        Convert reserved -> allocated (order confirmed).
        POST body: {"qty": 2, "reference": "order:123"}
        """
        inv = self.get_object()
        serializer = InventoryActionSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(False, status=400, message="Invalid input", errors=serializer.errors)

        qty = serializer.validated_data["qty"]
        reference = serializer.validated_data.get("reference", None)
        user = request.user if request.user.is_authenticated else None

        try:
            inv = inv.allocate(qty, reference=reference, user=user)
        except Exception as exc:
            return api_response(False, status=400, message=str(exc))

        txn = InventoryTransaction.objects.filter(variant=inv.variant, warehouse=inv.warehouse).order_by("-created_at").first()
        return api_response(True, status=200, message="Allocated", data={"inventory": InventorySerializer(inv).data, "transaction": InventoryTransactionSerializer(txn).data if txn else None})


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Inventory ledger: read-only for non-admins.
    Admins can view and filter. We intentionally disallow create/update via this endpoint
    for regular clients because inventory operations must go through Inventory model methods.
    """
    queryset = InventoryTransaction.objects.select_related("variant", "warehouse", "created_by").all().order_by("-created_at")
    serializer_class = InventoryTransactionSerializer

    def get_permissions(self):
        # Read-only endpoints accessible to authenticated users, full access for admins
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated()]
        return [IsAdminUser()]

    # Optional: an admin-only create endpoint can be added if you want:
    # def create(self, request, *args, **kwargs):
    #     ...
