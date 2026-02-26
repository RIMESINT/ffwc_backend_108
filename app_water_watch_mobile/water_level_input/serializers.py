from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from data_load.models import (
    Station
)
from app_user_mobile.models import (
    MobileAuthUser
)
from app_water_watch_mobile.models import (
    WaterLevelInputForMobileUser, 
    WaterWatchWaterLevelStationForMobileUser
)





"""
    - Serializers of StationSerializer for Station model
    - Serializers of MobileAuthUserSerializer for MobileAuthUser model
    - Serializers of WaterWatchWaterLevelStationForMobileUserSerializer for MobileAuthUser model 
    - Returns nested Station and MobileAuthUser details for WaterLevelStationForMobileUserViewSet
"""
class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = [
            "station_id",
            "station_code",
            "name",
            "name_bn",
            "station_serial_no",
            "danger_level",
            "highest_water_level",
        ]

class MobileAuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileAuthUser
        fields = [
            "id",
            "mobile_number",
            "lat",
            "long",
            "fcm_token",
            "device_info",
            "is_verified",
        ]


class WaterWatchWaterLevelStationForMobileUserSerializer(serializers.ModelSerializer):
    water_level_station = StationSerializer(read_only=True)
    mobile_user = MobileAuthUserSerializer(read_only=True)

    class Meta:
        model = WaterWatchWaterLevelStationForMobileUser
        fields = [
            "id",
            "mobile_user",
            "water_level_station",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields




"""
    - Input Serializers of SingleWaterLevelInputSerializer for WaterLevelInputForMobileUser model 
"""
class SingleWaterLevelInputSerializer(serializers.Serializer):
    station_id = serializers.IntegerField()
    observation_date = serializers.DateTimeField()
    water_level = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_station_id(self, value):
        # ensure station exists
        if not Station.objects.filter(station_id=value).exists():
            raise serializers.ValidationError(f"Station with station_id={value} does not exist.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if user is None or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        station_id = attrs['station_id']
        obs_dt = attrs['observation_date']
        water_level = attrs['water_level']

        # check user has access to this station and mapping is active
        allowed = WaterWatchWaterLevelStationForMobileUser.objects.filter(
            mobile_user=user,
            water_level_station__station_id=station_id,
            is_active=True
        ).exists()

        if not allowed:
            raise serializers.ValidationError(f"You don't have permission for station_id={station_id}.")

        # check duplicate exists in DB
        dup_exists = WaterLevelInputForMobileUser.objects.filter(
            station__station_id=station_id,
            observation_date=obs_dt,
            water_level=water_level
        ).exists()

        if dup_exists:
            raise serializers.ValidationError("Duplicate record already exists in database.")

        # attach station object for later use in create
        try:
            station_obj = Station.objects.get(station_id=station_id)
        except Station.DoesNotExist:
            raise serializers.ValidationError("Station not found (race condition).")
        attrs['station_obj'] = station_obj

        return attrs
    
    
    

class WaterLevelInputForMobileUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterLevelInputForMobileUser
        fields = [
            'id',
            'station',
            'observation_date',
            'water_level',
            'is_acepted',
            'created_at',
            'updated_at',
        ]
        
        
        

class WaterLevelUpdateSerializer(serializers.ModelSerializer):
    station_id = serializers.IntegerField(required=True)
    observation_date = serializers.DateTimeField(required=True)
    water_level = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)

    class Meta:
        model = WaterLevelInputForMobileUser
        fields = ['station_id', 'observation_date', 'water_level']

    def validate_station_id(self, value):
        if not Station.objects.filter(station_id=value).exists():
            raise serializers.ValidationError(f"Station with station_id={value} does not exist.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            raise serializers.ValidationError("Authentication required.")

        station_id = attrs.get('station_id')
        obs_dt = attrs.get('observation_date')
        wl = attrs.get('water_level')

        # Check user has access to this station (active mapping)
        allowed = WaterWatchWaterLevelStationForMobileUser.objects.filter(
            mobile_user=user,
            water_level_station__station_id=station_id,
            is_active=True
        ).exists()
        if not allowed:
            raise serializers.ValidationError(f"You don't have permission for station_id={station_id}.")

        # Duplicate check: exclude current instance if present
        qs = WaterLevelInputForMobileUser.objects.filter(
            station__station_id=station_id,
            observation_date=obs_dt,
            water_level=wl
        )
        if getattr(self, 'instance', None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Another record with same station_id, observation_date and water_level already exists.")

        return attrs

