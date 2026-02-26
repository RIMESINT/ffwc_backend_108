from rest_framework import serializers
from app_user_mobile.models import MobileAuthUser




class MobileAuthUserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()  
    
    class Meta:
        model = MobileAuthUser
        fields = [
            'id',
            'mobile_number',
            'first_name', 
            'last_name',
            'full_name',
            'address',
            'email',
            'profile_image',
            'lat',
            'long',
            'fcm_token',
            'device_info',
            'is_verified',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']