from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_str, smart_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'fullname', 'phonenumber', 'is_verified', 'profile_image', 'address'
        )
        read_only_fields = ('is_verified',)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'fullname', 'email', 'phonenumber', 'password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."}) # Here I'm providing a more specific error message based on the field.
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            fullname=validated_data.get('fullname'),
            phonenumber=validated_data.get('phonenumber'),
            password=validated_data['password']
        )
        user.generate_otp()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_or_email = attrs.get('username')
        password = attrs.get('password')

        user = None
        if '@' in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                pass
        
        if user is None:
            try:
                user = User.objects.get(username=username_or_email)
            except User.DoesNotExist:
                pass

        if user is None or not user.check_password(password):
            raise AuthenticationFailed('Invalid credentials, try again')

        if not user.is_active:
            raise AuthenticationFailed('Account is inactive. Please contact support.')
        
        # Set the correct username for the parent serializer's validation
        attrs[self.username_field] = user.username

        if not user.is_verified:
            user.generate_otp()
            current_site = Site.objects.get_current()
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
            raise AuthenticationFailed('Account not verified. Please verify your email with the new OTP sent.')
        
        data = super().validate(attrs)
        data['username'] = user.username
        data['email'] = user.email
        data['fullname'] = user.fullname
        return data


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=6)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."}) # Here I'm providing a more specific error message based on the field.

        if not user.verify_otp(otp):
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."}) # Here I'm providing a more specific error message based on the field.

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    confirm_new_password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"new_password": "New passwords do not match."}) # Here I'm providing a more specific error message based on the field.
        return attrs


class ResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    class Meta:
        fields = ['email']


class ResetPasswordConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    class Meta:
        fields = ['password', 'password2', 'uidb64', 'token']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            password2 = attrs.get('password2')
            uidb64 = attrs.get('uidb64')
            token = attrs.get('token')

            if password != password2:
                raise serializers.ValidationError({"password": "Password fields didn't match."}) # Here I'm providing a more specific error message based on the field.

            id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed('The reset link is invalid or has expired.', 401)

            user.set_password(password)
            user.save()

            return attrs
        except DjangoUnicodeDecodeError:
            raise AuthenticationFailed('The reset link is invalid or has expired.', 401)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            if user.is_verified:
                raise serializers.ValidationError("Account is already verified.")
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email.")
        return value
