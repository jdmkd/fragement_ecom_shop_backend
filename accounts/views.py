from rest_framework import generics, status
from .serializers import (
    UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer, OTPVerificationSerializer,
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

def get_standard_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    return Response({
        "data": data,
        "message": message,
        "status": status_code
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
            data=serializer.data,
            message="Registration successful. Please check your email for OTP verification.",
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
            data=UserSerializer(user).data,
            message="Account verified successfully.",
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
            return get_standard_response(
                data=None,
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return get_standard_response(
            data=serializer.validated_data,
            message="Login successful.",
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
                data=None,
                message="Old password is not correct.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()

        return get_standard_response(
            data=None,
            message="Password changed successfully.",
            status_code=status.HTTP_200_OK
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
            data=None,
            message="Password reset email sent. Please check your inbox.",
            status_code=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return get_standard_response(
            data=None,
            message="Password reset successful.",
            status_code=status.HTTP_200_OK
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
            data=None,
            message="New OTP sent successfully. Please check your email.",
            status_code=status.HTTP_200_OK
        )


class UserDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return get_standard_response(
            data=serializer.data,
            message="User data fetched successfully.",
            status_code=status.HTTP_200_OK
        )

