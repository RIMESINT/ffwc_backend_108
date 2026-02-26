# serializers.py
from rest_framework import serializers
from app_water_watch_mobile.models import (
    WaterLevelInputForMobileUser,
)
from data_load.models import (
    Station,
)
from app_user_mobile.models import (
    MobileAuthUser,
)







class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ['id', 'station_id', 'name', 'river', 'district']


class MobileAuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileAuthUser
        fields = ['id', 'mobile_number', 'first_name', 'last_name']


class WaterLevelInputForMobileUserSerializer(serializers.ModelSerializer):
    station_details = StationSerializer(source='station', read_only=True)
    created_by_details = MobileAuthUserSerializer(source='created_by', read_only=True)
    
    class Meta:
        model = WaterLevelInputForMobileUser
        fields = [
            'id',
            'station',
            'station_details',
            'observation_date',
            'water_level',
            'created_by',
            'created_by_details',
            'created_at',
            'updated_by',
            'updated_at',
            'is_acepted'
        ]
        read_only_fields = ['created_at', 'updated_at']