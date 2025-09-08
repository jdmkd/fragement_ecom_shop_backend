from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from .views import (
    AddressDetailView, AddressListCreateView, RegisterView, OTPVerificationView, LoginView, ChangePasswordView,
    RequestPasswordResetEmailView, PasswordResetConfirmView, ResendOTPView, UserDetailView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify_otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('request-reset-email/', RequestPasswordResetEmailView.as_view(), name='request_reset_email'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('user/', UserDetailView.as_view(), name='user_detail'),
    
    path('user/addresses/', AddressListCreateView.as_view(), name='user_addresses'),
    path('user/addresses/<int:pk>/', AddressDetailView.as_view(), name='user_address_detail'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

]
