from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from core.utils.response_utils import error_response
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def custom_page_not_found_view(request, exception):
    return error_response(
        message="The requested endpoint was not found.",
        error="Not Found",
        status=404,
    )

def custom_server_error_view(request):
    return error_response(
        message="Internal server error.",
        error="Server Error",
        status=500,
    )

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # Application URLs
    path('api/auth/', include('accounts.urls')),
    path('api/catalog/', include('catalog.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/shipping/', include('shipping.urls')),
    path('api/inventory/', include('inventory.urls')),

    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # path("__reload__/", include("django_browser_reload.urls")),
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = custom_page_not_found_view
handler500 = custom_server_error_view