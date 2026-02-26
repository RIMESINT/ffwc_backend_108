# admin.py
from django.contrib import admin
from django import forms

from app_water_watch_mobile.models import (
    WaterWatchWaterLevelStationForMobileUser,
    WaterWatchRFLevelStationForMobileUser,
)

# Import the related models from their apps
from app_user_mobile.models import (
    MobileAuthUser,
)
from data_load.models import (
    Station, 
    RainfallStation,
)





#####################################################################################
#####################################################################################
### API endpoints for managing water level inputs from mobile users.
#####################################################################################
#####################################################################################
class MobileUserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Show mobile number and pk in dropdown label
        return f"{obj.mobile_number} (id:{obj.pk})"


class StationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Show station_id and station name in dropdown label
        return f"{obj.station_id} — {obj.name}"


class WaterWatchForm(forms.ModelForm):
    mobile_user = MobileUserChoiceField(
        queryset=MobileAuthUser.objects.all().order_by('mobile_number'),
        required=True,
        label="Mobile user"
    )
    water_level_station = StationChoiceField(
        queryset=Station.objects.all().order_by('station_id'),
        required=True,
        label="Water level station"
    )

    class Meta:
        model = WaterWatchWaterLevelStationForMobileUser
        fields = '__all__'


@admin.register(WaterWatchWaterLevelStationForMobileUser)
class WaterWatchAdmin(admin.ModelAdmin):
    form = WaterWatchForm

    list_display = (
        'id',
        'get_mobile_number',
        'get_station_display',
        'is_active',
        'created_at',
        'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = (
        'mobile_user__mobile_number',
        'mobile_user__id',
        'water_level_station__station_id',
        'water_level_station__name',
    )
    ordering = ('-created_at',)
    list_select_related = ('mobile_user', 'water_level_station')
    readonly_fields = ('created_at', 'updated_at')
    # If you prefer the dropdown fields ordered differently, change field order here:
    fields = ('mobile_user', 'water_level_station', 'is_active', 'created_at', 'updated_at')

    def get_mobile_number(self, obj):
        return obj.mobile_user.mobile_number
    get_mobile_number.short_description = 'Mobile number'
    get_mobile_number.admin_order_field = 'mobile_user__mobile_number'

    def get_station_display(self, obj):
        return f"{obj.water_level_station.station_id} — {obj.water_level_station.name}"
    get_station_display.short_description = 'Station'
    get_station_display.admin_order_field = 'water_level_station__station_id'
    
    
    

#####################################################################################
#####################################################################################
### API endpoints for managing Rainfall level inputs from mobile users.
#####################################################################################
#####################################################################################
class RFMobileUserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Show mobile number and pk in dropdown label
        return f"{obj.mobile_number} (id:{obj.pk})"


class RFStationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Show station_id and station name in dropdown label
        return f"{obj.station_id} — {obj.name}"


class RFWaterWatchForm(forms.ModelForm):
    mobile_user = RFMobileUserChoiceField(
        queryset=MobileAuthUser.objects.all().order_by('mobile_number'),
        required=True,
        label="Mobile user"
    )
    water_level_station = RFStationChoiceField(
        queryset=RainfallStation.objects.all().order_by('station_id'),
        required=True,
        label="Rainfall level station"
    )

    class Meta:
        model = WaterWatchRFLevelStationForMobileUser
        fields = '__all__'


@admin.register(WaterWatchRFLevelStationForMobileUser)
class RFWaterWatchAdmin(admin.ModelAdmin):
    form = RFWaterWatchForm

    list_display = (
        'id',
        'get_mobile_number',
        'get_station_display',
        'is_active',
        'created_at',
        'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = (
        'mobile_user__mobile_number',
        'mobile_user__id',
        'water_level_station__station_id',
        'water_level_station__name',
    )
    ordering = ('-created_at',)
    list_select_related = ('mobile_user', 'water_level_station')
    readonly_fields = ('created_at', 'updated_at')
    # If you prefer the dropdown fields ordered differently, change field order here:
    fields = ('mobile_user', 'water_level_station', 'is_active', 'created_at', 'updated_at')

    def get_mobile_number(self, obj):
        return obj.mobile_user.mobile_number
    get_mobile_number.short_description = 'Mobile number'
    get_mobile_number.admin_order_field = 'mobile_user__mobile_number'

    def get_station_display(self, obj):
        return f"{obj.water_level_station.station_id} — {obj.water_level_station.name}"
    get_station_display.short_description = 'Station'
    get_station_display.admin_order_field = 'water_level_station__station_id'