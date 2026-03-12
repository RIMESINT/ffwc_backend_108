# serializers.py
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework import status
from app_water_watch_mobile.models import (
    WaterLevelInputForMobileUser,
)
from data_load.models import (
    Station,
)
from app_user_mobile.models import (
    MobileAuthUser,
)
from utils.exceptions import CustomValidationError
from data_load.models import WaterLevelObservation


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
            'is_acepted',
            'is_approved',
            'is_rejected',
        ]
        read_only_fields = ['created_at', 'updated_at']

class WaterLevelInputApproveRejectSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterLevelInputForMobileUser
        fields = [
            'id',
            'is_approved',
            'is_rejected',
            'observation_date',
            'water_level',
            'station'
        ]
        read_only_fields = ['id', 'observation_date', 'water_level', 'station']    

    def validate(self, attrs):
        if attrs.get('is_approved') and attrs.get('is_rejected'):
            raise CustomValidationError(
                "Approve and reject cannot be both True",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        # Only execute this logic if the record is being approved
        if attrs.get('is_approved'):
            # self.instance contains the existing WaterLevelInputForMobileUser record
            station = self.instance.station
            observation_date = self.instance.observation_date
            water_level = self.instance.water_level
        return attrs