
from rest_framework import serializers
from .models import (
    MobileAuthUser, 
    OTP,
)
from django.utils import timezone
from datetime import timedelta





class SendOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=17)
    
    def validate_mobile_number(self, value):
        return value


class VerifyOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=17)
    otp = serializers.CharField(max_length=6)
    
    def validate(self, data):
        mobile_number = data['mobile_number']
        otp = data['otp']
        
        try:
            otp_instance = OTP.objects.get(
                mobile_number=mobile_number, 
                otp=otp
            )
            
            if not otp_instance.is_valid():
                raise serializers.ValidationError("OTP has expired")
                
        except OTP.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP")
            
        return data



class MobileUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileAuthUser
        fields = ('mobile_number', 'lat', 'long', 'fcm_token', 'device_info')
        
        
        
"""
    #######################################################################################
    ### PUT API for updating profile fields of MobileAuthUser
    #######################################################################################
"""
class RelativePathImageField(serializers.ImageField):
    """
    Custom image field that returns relative path instead of absolute URL
    """
    def to_representation(self, value):
        if not value:
            return None
        # Return only the relative path part
        return ("/assets/"+value.name) if value else None
    
    
class UpdateProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = MobileAuthUser
        fields = ['first_name', 'last_name', 'address', 'profile_image']
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
        }
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if value is None or value == '':
                if attr == 'profile_image':
                    setattr(instance, attr, None)
                else:
                    setattr(instance, attr, value)
            else:
                setattr(instance, attr, value)
        
        instance.save()
        return instance

class MobileAuthUserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    profile_image = RelativePathImageField(required=False, allow_null=True)
    
    class Meta:
        model = MobileAuthUser
        fields = [
            'id', 'mobile_number', 'first_name', 'last_name', 'full_name', 
            'address', 'profile_image', 'lat', 'long', 'is_verified', 
            'fcm_token', 'device_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'mobile_number', 'fcm_token', 'device_info', 'is_verified', 'created_at', 'updated_at'
        ]
        
        




from rest_framework import serializers
from app_user_mobile.models import FCMTokenWiseUpdatedLatLon

class FCMTokenLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMTokenWiseUpdatedLatLon
        fields = ['fcm_token', 'lat', 'long']
    
    def validate_fcm_token(self, value):
        """Validate that fcm_token is provided"""
        if not value:
            raise serializers.ValidationError("FCM token is required")
        return value