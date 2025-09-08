from datetime import datetime
import uuid
from rest_framework import generics, permissions, status

from accounts.models import Address
from .serializers import (
    AddressSerializer, UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer, OTPVerificationSerializer,
    ChangePasswordSerializer, ResetPasswordEmailSerializer, ResetPasswordConfirmSerializer, ResendOTPSerializer
)
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import smart_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator

User = get_user_model()

def get_standard_response(
    success=False,
    data=None,
    message="Success",
    special_code="",
    errors=None,
    pagination=None,
    status_code=status.HTTP_200_OK,
    request_id=None
):
    """
    Standard API Response for consistency across endpoints.
    - If success=False => data=None, errors is required.
    - If success=True  => errors=None.
    """

    if not success:
        data = None
        if errors is None:
            errors = {"detail": ["An unknown error occurred."]}
    else:
        errors = None

    if request_id is None:
        request_id = str(uuid.uuid4())

    return Response({
        "success": success,
        "status": status_code,
        "message": message,
        "special_code": special_code,
        "data": data,
        "errors": errors,
        "meta": {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pagination": pagination
        }
    }, status=status_code)        


class RegisterView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send OTP email
        current_site = get_current_site(request)
        mail_subject = 'Activate your account.'
        message = render_to_string('accounts/otp_email.html', {
            'user': user,
            'domain': current_site.domain,
            'otp': user.otp,
        })
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False
        )

        headers = self.get_success_headers(serializer.data)
        return get_standard_response(
            success=True,
            data=serializer.data,
            message="Registration successful. Please check your email for OTP verification.",
            special_code="registration_successful",
            status_code=status.HTTP_201_CREATED
        )


class OTPVerificationView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = OTPVerificationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        return get_standard_response(
            success=True,
            data=UserSerializer(user).data,
            message="Account verified successfully.",
            special_code="account_verified_successful",
            status_code=status.HTTP_200_OK
        )


class LoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            error_detail = getattr(e, "detail", None)

            # Defaults
            code = "data_error"
            message = str(e)
            errors = {"detail": [str(e)]}

            if isinstance(error_detail, dict):
                # Extract our custom structured error
                code = error_detail.get("code", "data_error")
                message = error_detail.get("message", str(e))
                errors = error_detail

            return get_standard_response(
                success=False,
                message=message,
                special_code=code,
                status_code=status.HTTP_400_BAD_REQUEST,
                errors=errors,
            )
        
        return get_standard_response(
            success=True,
            data=serializer.validated_data,
            message="Login successful.",
            special_code="login_successful",
            status_code=status.HTTP_200_OK
        )


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return get_standard_response(
                success=True,
                message="Old password is not correct.",
                special_code="password_not_matched",
                status_code=status.HTTP_400_BAD_REQUEST,
                data=None,
                errors={"old_password": ["Old password is incorrect."]}
            )
        
        user.set_password(new_password)
        user.save()

        return get_standard_response(
            success=True,
            message="Password changed successfully.",
            special_code="password_changed_successfully",
            status_code=status.HTTP_200_OK,
            data=None,
        )


class RequestPasswordResetEmailView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordEmailSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)

            current_site = get_current_site(request)
            relative_link = f"/reset-password-confirm/{uidb64}/{token}/"  # Frontend URL
            absurl = f"http://{current_site.domain}{relative_link}"

            mail_subject = 'Reset your password.'
            message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': uidb64,
                'token': token,
                'absurl': absurl,
            })
            send_mail(
                mail_subject, 
                message, 
                settings.EMAIL_HOST_USER, 
                [user.email], 
                fail_silently=False
            )
        
        return get_standard_response(
            success=True,
            message="Password reset email sent. Please check your inbox.",
            special_code="password_reset_email_sent",
            status_code=status.HTTP_200_OK,
            data=None,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return get_standard_response(
            success=True,
            message="Password reset successful.",
            special_code="password_reset_successful",
            status_code=status.HTTP_200_OK,
            data=None,
        )


class ResendOTPView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResendOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email=email)  # User existence already checked in serializer
        
        user.generate_otp()

        current_site = get_current_site(request)
        mail_subject = 'Verify your account.'
        message = render_to_string('accounts/otp_email.html', {
            'user': user,
            'domain': current_site.domain,
            'otp': user.otp,
        })
        send_mail(
            mail_subject, 
            message, 
            settings.EMAIL_HOST_USER, 
            [user.email], 
            fail_silently=False
        )

        return get_standard_response(
            success=True,
            message="New OTP sent successfully. Please check your email.",
            special_code="new_otp_sent",
            status_code=status.HTTP_200_OK,
            data=None,
        )


class UserDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return get_standard_response(
            success=True,
            message="User data fetched successfully.",
            status_code=status.HTTP_200_OK,
            data=serializer.data,
        )


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)