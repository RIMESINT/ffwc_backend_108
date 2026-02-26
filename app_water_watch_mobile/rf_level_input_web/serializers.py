
from rest_framework import serializers
from app_water_watch_mobile.models import (
    RFLevelInputForMobileUser,
)
from data_load.models import (
    RainfallStation,
)
from app_user_mobile.models import (
    MobileAuthUser,
)



class RainfallStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RainfallStation
        fields = ['id', 'station_id', 'station_code', 'name', 'name_bn', 'latitude', 'longitude']

class MobileAuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileAuthUser
        fields = ['id', 'mobile_number', 'first_name', 'last_name']

class RFLevelInputForMobileUserSerializer(serializers.ModelSerializer):
    station_details = RainfallStationSerializer(source='station', read_only=True)
    created_by_details = MobileAuthUserSerializer(source='created_by', read_only=True)
    updated_by_details = MobileAuthUserSerializer(source='updated_by', read_only=True)

    class Meta:
        model = RFLevelInputForMobileUser
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
            'updated_by_details',
            'updated_at',
            'is_acepted'
        ]
        read_only_fields = ['created_at', 'updated_at']