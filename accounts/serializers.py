from django.db.models import Q
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
from accounts.models import Address

User = get_user_model()

class AddressBatchSerializer(serializers.ListSerializer):
    """
    Handles batch creation/updating of addresses and ensures only one default per type in the same request.
    """
    def validate(self, data):
        seen_defaults = {}
        for item in data:
            if item.get('is_default', False):
                address_type = item.get('address_type', 'shipping')
                if seen_defaults.get(address_type):
                    raise serializers.ValidationError(
                        f"Multiple default addresses for {address_type} in the same request."
                    )
                seen_defaults[address_type] = True
        return data


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            'id',
            'user',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'country',
            'postal_code',
            'phone_number',
            'address_type',
            'is_default',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
        # list_serializer_class = AddressBatchSerializer

    def validate(self, attrs):
        user = self.context['request'].user
        address_type = attrs.get('address_type', getattr(self.instance, 'address_type', 'shipping'))
        is_default = attrs.get('is_default', getattr(self.instance, 'is_default', False))

        if is_default:
            qs = Address.objects.filter(user=user, address_type=address_type, is_default=True)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError(
                    f"A default {address_type} address already exists for this user."
                )
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        address_type = validated_data.get('address_type', 'shipping')
        is_default = validated_data.get('is_default', False)

        if is_default:
            # Unset previous defaults automatically
            Address.objects.filter(user=user, address_type=address_type, is_default=True).update(is_default=False)

        return Address.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user = instance.user
        address_type = validated_data.get('address_type', instance.address_type)
        is_default = validated_data.get('is_default', instance.is_default)

        if is_default:
            # Unset previous defaults automatically
            Address.objects.filter(user=user, address_type=address_type).exclude(id=instance.id).update(is_default=False)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'fullname', 'email', 'phonenumber', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class UserSerializer(serializers.ModelSerializer):
    # Now writable nested addresses
    addresses = AddressSerializer(many=True, required=False)

    default_shipping_address = serializers.SerializerMethodField()
    default_billing_address = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'fullname', 'phonenumber', 'is_verified', 'profile_image',
            'addresses', 'default_shipping_address', 'default_billing_address',
        )
        read_only_fields = ('is_verified',)

    def get_default_shipping_address(self, obj):
        address = obj.addresses.filter(address_type='shipping', is_default=True).first()
        if address:
            return AddressSerializer(address).data
        return None

    def get_default_billing_address(self, obj):
        address = obj.addresses.filter(address_type='billing', is_default=True).first()
        if address:
            return AddressSerializer(address).data
        return None

    def create(self, validated_data):
        addresses_data = validated_data.pop('addresses', [])
        user = User.objects.create(**validated_data)

        request = self.context.get('request')

        for address_data in addresses_data:
            serializer = AddressSerializer(data=address_data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user)

        return user

    def update(self, instance, validated_data):
        addresses_data = validated_data.pop('addresses', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        request = self.context.get('request')

        # Handle nested addresses
        for address_data in addresses_data:
            address_id = address_data.get('id', None)
            if address_id:
                # Update existing address
                try:
                    address_instance = Address.objects.get(id=address_id, user=instance)
                except Address.DoesNotExist:
                    continue  # skip invalid IDs
                serializer = AddressSerializer(address_instance, data=address_data, context={'request': request})
                serializer.is_valid(raise_exception=True)
                serializer.save()
            else:
                # Create new address
                serializer = AddressSerializer(data=address_data, context={'request': request})
                serializer.is_valid(raise_exception=True)
                serializer.save(user=instance)

        return instance

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
        username_or_email = attrs.get("username")
        password = attrs.get("password")

        # Try email OR username in one query
        try:
            user = User.objects.get(Q(username=username_or_email) | Q(email=username_or_email))
        except User.DoesNotExist:
            user = None

        # Invalid credentials
        if user is None or not user.check_password(password):
            raise AuthenticationFailed({
                "code": "invalid_credentials",
                "message": "Invalid credentials, try again"
            })

        # Account inactive
        if not user.is_active:
            raise AuthenticationFailed({
                "code": "account_inactive",
                "message": "Account is inactive. Please contact support."
            })

        # Account not verified → send OTP + error
        if not user.is_verified:
            user.generate_otp()
            try:
                current_site = Site.objects.get_current()
                mail_subject = "Verify your account."
                message = render_to_string("accounts/otp_email.html", {
                    "user": user,
                    "domain": current_site.domain,
                    "otp": user.otp,
                })
                send_mail(
                    mail_subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=True 
                )
            except Exception as e:
                # Log error (don’t block login response)
                pass

            raise AuthenticationFailed({
                "code": "account_not_verified",
                "message": "Your account is not verified. Please check your email for OTP."
            })

        # Proceed with default JWT validation
        attrs[self.username_field] = user.username
        data = super().validate(attrs)

        # Extend response payload
        data["username"] = user.username
        data["email"] = user.email
        data["fullname"] = user.fullname

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

