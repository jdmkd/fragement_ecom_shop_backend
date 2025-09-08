from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, InventoryViewSet, InventoryTransactionViewSet

router = DefaultRouter()
router.register(r"warehouses", WarehouseViewSet, basename="warehouse")
router.register(r"inventories", InventoryViewSet, basename="inventory")
router.register(r"transactions", InventoryTransactionViewSet, basename="inventorytransaction")

urlpatterns = [
    path("", include(router.urls)),
]
