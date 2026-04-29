# admin.py
from django.contrib import admin
from django import forms

from app_water_watch_mobile.models import (
    WaterWatchWaterLevelStationForMobileUser,
    WaterWatchRFLevelStationForMobileUser,
    WaterLevelInputForMobileUser
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



class WaterLevelInputForm(forms.ModelForm):
    station = StationChoiceField(
        queryset=Station.objects.all().order_by('station_id'),
        required=False,
        label="Station"
    )
    created_by = MobileUserChoiceField(
        queryset=MobileAuthUser.objects.all().order_by('mobile_number'),
        required=False,
        label="Created by (Mobile User)"
    )
    updated_by = MobileUserChoiceField(
        queryset=MobileAuthUser.objects.all().order_by('mobile_number'),
        required=False,
        label="Updated by (Mobile User)"
    )

    class Meta:
        model = WaterLevelInputForMobileUser
        fields = '__all__'


@admin.register(WaterLevelInputForMobileUser)
class WaterLevelInputForMobileUserAdmin(admin.ModelAdmin):
    form = WaterLevelInputForm

    list_display = (
        'get_station_display',
        'observation_date',
        'water_level',
        'get_creator_mobile',
        'is_acepted',
        'created_at',
    )
    
    list_filter = ('is_acepted', 'observation_date', 'created_at')
    
    search_fields = (
        'station__station_id',
        'station__name',
        'created_by__mobile_number',
        'water_level',
    )
    
    ordering = ('-observation_date',)
    
    # Use select_related to reduce SQL queries when loading the list view
    list_select_related = ('station', 'created_by', 'updated_by')
    
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Observation Details', {
            'fields': ('station', 'observation_date', 'water_level', 'is_acepted')
        }),
        ('User Metadata', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
        }),
    )

    # Helper methods for list_display
    def get_station_display(self, obj):
        if obj.station:
            return f"{obj.station.station_id} — {obj.station.name}"
        return "—"
    get_station_display.short_description = 'Station'
    get_station_display.admin_order_field = 'station__station_id'

    def get_creator_mobile(self, obj):
        return obj.created_by.mobile_number if obj.created_by else "—"
    get_creator_mobile.short_description = 'Submitted By'
    get_creator_mobile.admin_order_field = 'created_by__mobile_number'