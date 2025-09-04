from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static


router = DefaultRouter()

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    path('api/auth/', include('accounts.urls')),
    path('api/catalog/', include('catalog.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/shipping/', include('shipping.urls')),

    # path("__reload__/", include("django_browser_reload.urls")),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

