from rest_framework import serializers
from datetime import datetime
from . import models as models
from .models import RainfallObservation
from django.db.models import Max, Sum, Subquery,OuterRef,Prefetch

from data_load.models import (
    Station,
)

class lastUpdateDateSerializer(serializers.ModelSerializer):

    class Meta:
        model=models.FfwcLastUpdateDate
        fields='__all__'


class FloodAlertDisclaimerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FloodAlertDisclaimer
        fields = ['id', 'message', 'is_active']


class MessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Messages
        fields = ['id', 'message', 'is_active']

class ScrollerMessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ScrollerMessages
        fields = ['id', 'message', 'is_active']

class SecondScrollerMessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SecondScrollerMessages
        fields = ['id', 'message', 'is_active']


class BasinSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Basin
        fields = ['id', 'name', 'name_bn']

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Unit
        fields = ['id', 'name']

"""
    ##############################################################################
    #### Added by: Sajib bhai
    ##############################################################################
"""
# serializers.py
from rest_framework import serializers
from .models import StationSummaryViewMobileV1

class StationSummaryViewMobileV1Serializer(serializers.ModelSerializer):
    class Meta:
        model = StationSummaryViewMobileV1
        fields = [
            'id', 'station_id', 'station_code', 'bwdb_id', 'name', 'name_bn',
            'ffdata_header', 'ffdata_header_1', 'river', 'river_bn', 'river_chainage',
            'danger_level', 'pmdl', 'highest_water_level', 'highest_water_level_date',
            'gauge_shift', 'gauge_factor', 'effective_date', 'latitude', 'longitude',
            'h_division', 'h_division_bn', 'division', 'division_bn', 'district', 'district_bn',
            'upazilla', 'upazilla_bn', 'union', 'union_bn',
            'five_days_forecast', 'ten_days_forecast', 'monsoon_station', 'pre_monsoon_station',
            'dry_period_station', 'sms_id', 'msi_date', 'msi_year', 'order_up_down', 'forecast_observation',
            'status', 'station_order', 'medium_range_station', 'jason_2_satellite_station', 'experimental',
            'basin_id', 'unit_id', 'extended_range_station', 'station_serial_no',
            'last_observation_date', 'last_water_level', 'previous_observation_date', 'previous_water_level',
            'water_level_24_hours_ago_observation_date', 'water_level_24_hours_ago',
            'status_name', 'station_flood_status', 'level_difference', 'difference_water_level_24_hours',
        ]
        read_only_fields = fields


# class StationV2MobileSerializer(serializers.ModelSerializer):
#     web_id = serializers.IntegerField(source='station_id', allow_null=True)
#     st_id = serializers.CharField(source='station_code', allow_null=True)
#     station = serializers.CharField(source='name')
#     station_bn = serializers.CharField(source='name_bn', allow_null=True)

#     # model fields with same name -> DO NOT set `source=...`
#     station_serial_no = serializers.IntegerField(allow_null=True)
#     dl = serializers.FloatField(source='danger_level', allow_null=True)
#     pmdl = serializers.SerializerMethodField()
#     rhwl = serializers.FloatField(source='highest_water_level', allow_null=True)
#     date_of_rhwl = serializers.DateField(source='highest_water_level_date', allow_null=True)
#     gauge_shift_pwd_msl = serializers.FloatField(source='gauge_shift', allow_null=True)

#     # basin nested names keep source because they are nested attributes
#     basin = serializers.CharField(source='basin.name', allow_null=True)
#     basin_bn = serializers.CharField(source='basin.name_bn', allow_null=True)

#     # location/admin fields (no redundant source)
#     h_division = serializers.CharField(allow_null=True)
#     h_division_bn = serializers.CharField(allow_null=True)
#     division = serializers.CharField()
#     division_bn = serializers.CharField(allow_null=True)
#     district = serializers.CharField()
#     district_bn = serializers.CharField(allow_null=True)
#     upazilla = serializers.CharField(allow_null=True)
#     upazilla_bn = serializers.CharField(allow_null=True)
#     union = serializers.CharField(allow_null=True)
#     union_bn = serializers.CharField(allow_null=True)
#     river = serializers.CharField()
#     river_bn = serializers.CharField(allow_null=True)

#     # boolean -> 0/1 fields
#     five_days_forecast = serializers.SerializerMethodField()
#     ten_days_forecast = serializers.SerializerMethodField()
#     monsoon_station = serializers.SerializerMethodField()
#     pre_monsoon_station = serializers.SerializerMethodField()
#     dry_period_station = serializers.SerializerMethodField()

#     # single nested key containing the annotated waterlevel fields (and extras)
#     waterlevel_info = serializers.SerializerMethodField()

#     def get_pmdl(self, obj):
#         return str(obj.pmdl) if obj.pmdl is not None else "-"

#     def get_five_days_forecast(self, obj):
#         return 1 if obj.five_days_forecast else 0

#     def get_ten_days_forecast(self, obj):
#         return 1 if obj.ten_days_forecast else 0

#     def get_monsoon_station(self, obj):
#         return 1 if obj.monsoon_station else 0

#     def get_pre_monsoon_station(self, obj):
#         return 1 if obj.pre_monsoon_station else 0

#     def get_dry_period_station(self, obj):
#         return 1 if obj.dry_period_station else 0

#     def get_waterlevel_info(self, obj):
#         """
#             Builds:
#             - last_water_level
#             - last_observation_date
#             - previous_water_level
#             - previous_observation_date
#             - level_difference
#             - status_name
#             - water_level_24_hours_ago
#             - water_level_24_hours_ago_observation_date
#             - difference_water_level_24_hours
#             - station_flood_status (annotated in queryset)
#         """

#         # Simple format helpers using DRF fields (keeps consistent formatting)
#         float_field = serializers.FloatField(allow_null=True)
#         datetime_field = serializers.DateTimeField(allow_null=True)
#         char_field = serializers.CharField(allow_null=True)

#         def fmt_float(val):
#             if val is None:
#                 return None
#             try:
#                 return float_field.to_representation(val)
#             except Exception:
#                 return val

#         def fmt_datetime(val):
#             if val is None:
#                 return None
#             try:
#                 return datetime_field.to_representation(val)
#             except Exception:
#                 return str(val)

#         def fmt_str(val):
#             if val is None:
#                 return None
#             try:
#                 return char_field.to_representation(val)
#             except Exception:
#                 return str(val)

#         # base annotated values (may be None)
#         last_wl = getattr(obj, 'last_water_level', None)
#         last_obs_dt = getattr(obj, 'last_observation_date', None)
#         prev_wl = getattr(obj, 'previous_water_level', None)
#         prev_obs_dt = getattr(obj, 'previous_observation_date', None)
#         diff = getattr(obj, 'level_difference', None)
#         status_name = getattr(obj, 'status_name', None)
#         flood_status = getattr(obj, 'station_flood_status', None)

#         # --- find water level ~24 hours before last_observation_date ---
#         water_level_24 = None
#         water_level_24_dt = None
#         difference_24 = None

#         # Only attempt lookup if we have last_observation_date
#         if last_obs_dt:
#             target_time = last_obs_dt - timedelta(hours=24)

#             # Query the WaterLevelObservation for the observation at or before target_time
#             # use order_by('-observation_date') to choose the nearest previous observation
#             try:
#                 wlo = models.WaterLevelObservation.objects.filter(
#                     station_id=obj.station_id,  # note: station_id is FK to Station.station_id
#                     observation_date__lte=target_time
#                 ).order_by('-observation_date').first()
#             except Exception:
#                 # defensive: in case of any weirdness with FK field naming or DB,
#                 # try filtering by station reference (Station.id)
#                 try:
#                     wlo = models.WaterLevelObservation.objects.filter(
#                         station_id__id=getattr(obj, 'id'),  # fallback
#                         observation_date__lte=target_time
#                     ).order_by('-observation_date').first()
#                 except Exception:
#                     wlo = None

#             if wlo:
#                 # convert Decimal to float via float()
#                 try:
#                     water_level_24 = float(wlo.water_level)
#                 except Exception:
#                     water_level_24 = None
#                 water_level_24_dt = wlo.observation_date

#                 if last_wl is not None and water_level_24 is not None:
#                     try:
#                         difference_24 = float(last_wl) - float(water_level_24)
#                     except Exception:
#                         difference_24 = None

#         info = {
#             'last_water_level': fmt_float(last_wl),
#             'last_observation_date': fmt_datetime(last_obs_dt),
#             'previous_water_level': fmt_float(prev_wl),
#             'previous_observation_date': fmt_datetime(prev_obs_dt),
#             'level_difference': fmt_float(diff),
#             'status_name': fmt_str(status_name),
#             # newly requested fields:
#             'water_level_24_hours_ago': fmt_float(water_level_24),
#             'water_level_24_hours_ago_observation_date': fmt_datetime(water_level_24_dt),
#             'difference_water_level_24_hours': fmt_float(difference_24),
#             'station_flood_status': fmt_str(flood_status),
#         }

#         return info

#     def _replace_none_recursive(self, value):
#         """
#         Recursively replace None with "-" for dicts/lists,
#         otherwise return value unchanged.
#         """
#         if isinstance(value, dict):
#             return {k: self._replace_none_recursive(v) for k, v in value.items()}
#         if isinstance(value, list):
#             return [self._replace_none_recursive(v) for v in value]
#         if value is None:
#             return "-"
#         return value

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)

#         if representation.get('station_serial_no') is None:
#             representation['station_serial_no'] = 0

#         representation = self._replace_none_recursive(representation)
#         return representation

#     class Meta:
#         model = models.Station
#         fields = [
#             'web_id', 'st_id', 'station', 'station_bn', 'station_serial_no',
#             'dl', 'pmdl', 'rhwl', 'date_of_rhwl', 'gauge_shift_pwd_msl',
#             'basin', 'basin_bn',
#             'h_division', 'h_division_bn', 'division', 'division_bn',
#             'district', 'district_bn', 'upazilla', 'upazilla_bn',
#             'union', 'union_bn', 'river', 'river_bn',
#             'five_days_forecast', 'ten_days_forecast', 'monsoon_station',
#             'pre_monsoon_station', 'dry_period_station', 'latitude', 'longitude',
#             # single nested waterlevel object (includes the new fields now)
#             'waterlevel_info',
#         ]
#         read_only_fields = ('web_id',)

class StationSerializer(serializers.ModelSerializer):
    # ast_water_level = serializers.DecimalField(
    #     max_digits=10, 
    #     decimal_places=2, 
    #     allow_null=True
    # )
    # last_observation_date = serializers.DateTimeField(allow_null=True)
    # water_level_diff = serializers.FloatField(allow_null=True)
    # status_name = serializers.CharField(allow_null=True)
    
    
    # Rename fields using source where necessary
    web_id = serializers.IntegerField(source='station_id', allow_null=True)
    # station_serial_no = serializers.IntegerField(
    #     source='station_serial_no', 
    #     allow_null=True,
    #     default=0  
    # ) 
    
    st_id = serializers.CharField(source='station_code', allow_null=True)
    station = serializers.CharField(source='name')
    station_bn = serializers.CharField(allow_null=True)  # Remove source='name_bn'
    dl = serializers.FloatField(source='danger_level', allow_null=True)
    pmdl = serializers.SerializerMethodField()
    rhwl = serializers.FloatField(source='highest_water_level', allow_null=True)
    date_of_rhwl = serializers.DateField(source='highest_water_level_date', allow_null=True)
    gauge_shift_pwd_msl = serializers.FloatField(source='gauge_shift', allow_null=True)
    basin = serializers.CharField(source='basin.name', allow_null=True)
    basin_bn = serializers.CharField(source='basin.name_bn', allow_null=True)
    h_division = serializers.CharField(allow_null=True)  # Remove source='h_division'
    h_division_bn = serializers.CharField(allow_null=True)  # Remove source='h_division_bn'
    division = serializers.CharField()  # Remove source='division'
    division_bn = serializers.CharField(allow_null=True)  # Remove source='division_bn'
    district = serializers.CharField()  # Remove source='district'
    district_bn = serializers.CharField(allow_null=True)  # Remove source='district_bn'
    upazilla = serializers.CharField(allow_null=True)  # Remove source='upazilla'
    upazilla_bn = serializers.CharField(allow_null=True)  # Remove source='upazilla_bn'
    union = serializers.CharField(allow_null=True)  # Remove source='union'
    union_bn = serializers.CharField(allow_null=True)  # Remove source='union_bn'
    river = serializers.CharField()  # Remove source='river'
    river_bn = serializers.CharField(allow_null=True)  # Remove source='river_bn'

    # Convert boolean fields to 0/1
    five_days_forecast = serializers.SerializerMethodField()
    ten_days_forecast = serializers.SerializerMethodField()
    monsoon_station = serializers.SerializerMethodField()
    pre_monsoon_station = serializers.SerializerMethodField()
    dry_period_station = serializers.SerializerMethodField()

    def get_pmdl(self, obj):
        return str(obj.pmdl) if obj.pmdl is not None else "-"

    def get_five_days_forecast(self, obj):
        return 1 if obj.five_days_forecast else 0

    def get_ten_days_forecast(self, obj):
        return 1 if obj.ten_days_forecast else 0

    def get_monsoon_station(self, obj):
        return 1 if obj.monsoon_station else 0

    def get_pre_monsoon_station(self, obj):
        return 1 if obj.pre_monsoon_station else 0

    def get_dry_period_station(self, obj):
        return 1.0 if obj.dry_period_station else 0.0

    # def to_representation(self, instance):
    #     # Handle null values by replacing with "-"
    #     representation = super().to_representation(instance)
    #     for field in representation:
    #         if representation[field] is None:
    #             representation[field] = "-"
    #     return representation
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        if representation.get('station_serial_no') is None:
            representation['station_serial_no'] = 0
        
        for key in representation:
            if key == 'station_serial_no':
                continue  
            if representation[key] is None:
                representation[key] = "-"
        
        return representation
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
        
    #     # Handle null values for new fields
    #     new_fields = ['last_water_level', 'last_observation_date', 'water_level_diff', 'status_name']
    #     for field in new_fields:
    #         if representation.get(field) is None:
    #             representation[field] = "-"
        
    #     # Keep your existing null handling logic
    #     if representation.get('station_serial_no') is None:
    #         representation['station_serial_no'] = 0
        
    #     for key in representation:
    #         if key == 'station_serial_no':
    #             continue  
    #         if representation[key] is None:
    #             representation[key] = "-"
        
    #     return representation

    class Meta:
        model = models.Station
        fields = [
            'id', 'web_id', 'station_serial_no', 'st_id', 'station', 'station_bn',
            'ffdata_header', 'ffdata_header_1', 'river', 'river_bn',
            'dl', 'pmdl', 'rhwl', 'date_of_rhwl', 'gauge_shift_pwd_msl',
            'effective_date', 'latitude', 'longitude', 'basin', 'basin_bn',
            'h_division', 'h_division_bn', 'division', 'division_bn',
            'district', 'district_bn', 'upazilla', 'upazilla_bn',
            'union', 'union_bn', 'five_days_forecast', 'ten_days_forecast',
            'monsoon_station', 'pre_monsoon_station', 'dry_period_station',
            'sms_id'
        ]



class StationByNameSerializer(serializers.ModelSerializer):
    # Field mappings using 'source' to match the desired JSON keys
    long = serializers.CharField(source='longitude')
    lat = serializers.CharField(source='latitude')
    dangerlevel = serializers.CharField(source='danger_level', allow_null=True)
    riverhighestwaterlevel = serializers.FloatField(source='highest_water_level', allow_null=True)
    date_of_rhwl = serializers.DateField(source='highest_water_level_date', allow_null=True)
    unit_id = serializers.CharField(source='unit.id', allow_null=True)
    basin = serializers.CharField(source='basin.name', allow_null=True)
    
    # Custom fields that require specific logic
    jason_2_satellite_station = serializers.SerializerMethodField()
    coords = serializers.SerializerMethodField()
    basin_order = serializers.SerializerMethodField()
    rhwl = serializers.FloatField(source='highest_water_level', allow_null=True)
    
    class Meta:
        model = models.Station
        fields = [
            'id', 'coords', 'name', 'river', 'basin_order', 'basin',
            'dangerlevel', 'riverhighestwaterlevel', 'pmdl', 'river_chainage',
            'division', 'district', 'upazilla', 'union', 'long',
            'order_up_down', 'lat', 'forecast_observation', 'status',
            'station_order', 'medium_range_station', 'unit_id',
            'jason_2_satellite_station', 'rhwl', 'date_of_rhwl'
        ]

    def get_jason_2_satellite_station(self, obj):
        # Convert the boolean value from the model to an integer
        return 1 if obj.jason_2_satellite_station else 0

    def get_coords(self, obj):
        return f"{int(obj.latitude)},{int(obj.longitude)}"

    def get_basin_order(self, obj):
        # This value appears to be hardcoded or derived from another model.
        return 1

class StationsEndpointSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='station_id')
    coords = serializers.SerializerMethodField()
    name = serializers.CharField()
    river = serializers.CharField()
    # basin_order = serializers.IntegerField(source='basin.basin_order', allow_null=True)
    basin = serializers.CharField(source='basin.name', allow_null=True)
    dangerlevel = serializers.SerializerMethodField()
    riverhighestwaterlevel = serializers.SerializerMethodField()
    pmdl = serializers.CharField(allow_null=True)
    river_chainage = serializers.CharField(allow_null=True)
    division = serializers.CharField()
    district = serializers.CharField()
    upazilla = serializers.CharField(allow_null=True)
    union = serializers.CharField(allow_null=True)
    long = serializers.SerializerMethodField()
    order_up_down = serializers.IntegerField(allow_null=True)
    lat = serializers.SerializerMethodField()
    forecast_observation = serializers.IntegerField(allow_null=True)
    # status = serializers.IntegerField(source='status', allow_null=False)
    status = serializers.IntegerField(allow_null=False)
    station_order = serializers.IntegerField(allow_null=True)
    medium_range_station = serializers.IntegerField(allow_null=True)
    unit_id = serializers.IntegerField(source='unit.id', allow_null=True)
    jason_2_satellie_station = serializers.IntegerField(source='jason_2_satellite_station', allow_null=True)
    rhwl = serializers.FloatField(source='highest_water_level', allow_null=True)
    date_of_rhwl = serializers.DateField(source='highest_water_level_date', format='%Y-%m-%d', allow_null=True)

    class Meta:
        model = models.Station
        fields = [
            'id', 'coords', 'name', 'river','basin', 'dangerlevel',
            'riverhighestwaterlevel', 'pmdl', 'river_chainage', 'division', 'district',
            'upazilla', 'union', 'long', 'order_up_down', 'lat', 'forecast_observation',
            'status', 'station_order', 'medium_range_station', 'unit_id',
            'jason_2_satellie_station', 'rhwl', 'date_of_rhwl'
        ]

    def get_coords(self, obj):
        if obj.latitude is not None and obj.longitude is not None:
            return f"{obj.latitude},{obj.longitude}"
        return "-"

    def get_dangerlevel(self, obj):
        return f"{obj.danger_level:.2f}" if obj.danger_level is not None else "-"

    def get_riverhighestwaterlevel(self, obj):
        return f"{obj.highest_water_level:.2f}" if obj.highest_water_level is not None else "-"

    def get_long(self, obj):
        return f"{obj.longitude:.6f}" if obj.longitude is not None else "-"

    def get_lat(self, obj):
        return f"{obj.latitude:.6f}" if obj.latitude is not None else "-"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in representation:
            if representation[field] is None:
                representation[field] = "-"
        return representation


class ShortRangeStationSerializer(serializers.ModelSerializer):
    # Maps the model's 'station_id' (an IntegerField) to the 'id' key in the output.
    id = serializers.IntegerField(source='station_id', read_only=True)

    # Maps the 'name' field of the related Basin object to the 'basin' key in the output.
    basin = serializers.CharField(source='basin.name', read_only=True)
    # Maps the 'id' field of the related Basin object to the 'basin_order' key in the output.
    basin_order = serializers.IntegerField(source='basin.id', read_only=True)

    # Renames model fields to match the desired output keys.
    dangerlevel = serializers.FloatField(source='danger_level', read_only=True)
    riverhighestwaterlevel = serializers.FloatField(source='highest_water_level', read_only=True)
    date_of_rhwl = serializers.DateField(source='highest_water_level_date', read_only=True)
    long = serializers.FloatField(source='longitude', read_only=True)
    lat = serializers.FloatField(source='latitude', read_only=True)

    # Converts BooleanField values (True/False) to integers (1/0) for the output.
    status = serializers.IntegerField(read_only=True)
    medium_range_station = serializers.IntegerField(read_only=True)
    jason_2_satellie_station = serializers.IntegerField(source='jason_2_satellite_station', read_only=True)

    # Duplicates 'highest_water_level' for the 'rhwl' key in the output as per your desired format.
    rhwl = serializers.FloatField(source='highest_water_level', read_only=True)

    # Custom field 'coords' generated by a method.
    coords = serializers.SerializerMethodField()

    # Maps the primary key of the related Unit object to 'unit_id'.
    unit_id = serializers.PrimaryKeyRelatedField(source='unit', read_only=True)


    class Meta:
        model = models.Station
        # List all fields that should be included in the serialized output.
        fields = [
            'id',  # This 'id' now refers to the 'station_id' from the model
            'coords',
            'name',
            'river',
            'basin_order',
            'basin',
            'dangerlevel',
            'riverhighestwaterlevel',
            'pmdl',
            'river_chainage',
            'division',
            'district',
            'upazilla',
            'union',
            'long',
            'order_up_down',
            'lat',
            'forecast_observation', # This is a CharField, will be serialized as-is
            'status',
            'station_order',
            'medium_range_station',
            'unit_id',
            'jason_2_satellie_station',
            'rhwl',
            'date_of_rhwl',
        ]

    # Method to generate the 'coords' field.
    def get_coords(self, obj):
        # Ensures latitude and longitude exist before attempting to format.
        if obj.latitude is not None and obj.longitude is not None:
            # Formats coordinates as "latitude,longitude" with full float precision.
            # If you need specific precision (e.g., 6 decimal places), use:
            # return f"{obj.latitude:.6f},{obj.longitude:.6f}"
            return f"{obj.latitude},{obj.longitude}"
        return None



class StationByIdResponseSerializer(serializers.ModelSerializer):
    # Maps the model's 'station_id' (an IntegerField) to the 'id' key in the output.
    id = serializers.IntegerField(source='station_id', read_only=True)

    basin = serializers.CharField(source='basin.name', read_only=True)
    basin_order = serializers.IntegerField(source='basin.id', read_only=True)

    dangerlevel = serializers.FloatField(source='danger_level', read_only=True)
    riverhighestwaterlevel = serializers.FloatField(source='highest_water_level', read_only=True)
    date_of_rhwl = serializers.DateField(source='highest_water_level_date', read_only=True)
    long = serializers.FloatField(source='longitude', read_only=True)
    lat = serializers.FloatField(source='latitude', read_only=True)

    # Converts BooleanField values (True/False) to integers (1/0) for the output.
    status = serializers.IntegerField(read_only=True)
    medium_range_station = serializers.IntegerField(read_only=True)
    jason_2_satellie_station = serializers.IntegerField(source='jason_2_satellite_station', read_only=True)

    rhwl = serializers.FloatField(source='highest_water_level', read_only=True)
    coords = serializers.SerializerMethodField()

    # Converts 'forecast_observation' CharField to Integer to match sample output (e.g., 1 instead of "1").
    forecast_observation = serializers.IntegerField(read_only=True)

    # Maps the primary key of the related Unit object to 'unit_id'.
    unit_id = serializers.PrimaryKeyRelatedField(source='unit', read_only=True)


    class Meta:
        model = models.Station
        fields = [
            'id',
            'coords',
            'name',
            'river',
            'basin_order',
            'basin',
            'dangerlevel',
            'riverhighestwaterlevel',
            'pmdl',
            'river_chainage',
            'division',
            'district',
            'upazilla',
            'union',
            'long',
            'order_up_down',
            'lat',
            'forecast_observation',
            'status',
            'station_order',
            'medium_range_station',
            'unit_id',
            'jason_2_satellie_station',
            'rhwl',
            'date_of_rhwl',
        ]

    def get_coords(self, obj):
        if obj.latitude is not None and obj.longitude is not None:
            return f"{int(obj.latitude)},{int(obj.longitude)}"
        return None

class RainfallStationSerializer(serializers.ModelSerializer):
    basin = BasinSerializer(read_only=True)
    
    class Meta:
        model = models.RainfallStation
        fields = [
            'station_id', 'station_code', 'name', 'name_bn', 'basin', 'basin_bn',
            'latitude', 'longitude', 'division', 'division_bn', 'district',
            'district_bn', 'upazilla', 'upazilla_bn', 'header', 'unit', 'status'
        ]

class WaterLevelObservationSerializer(serializers.ModelSerializer):
    station_id = serializers.PrimaryKeyRelatedField(queryset=models.Station.objects.all())
    
    class Meta:
        model = models.WaterLevelObservation
        fields = ['id', 'station_id', 'observation_date', 'water_level']

class ObservedWaterLevelSerializer(serializers.ModelSerializer):

    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)
    station_serial_no = serializers.IntegerField(source='station_id.station_serial_no', allow_null=True)

    wl_date = serializers.DateTimeField(source='observation_date', format='%Y-%m-%dT%H:%M:%SZ')
    waterlevel = serializers.CharField(source='water_level')
    name = serializers.CharField(source='station_id.name', allow_null=True)
    lat = serializers.FloatField(source='station_id.latitude', allow_null=True)
    long = serializers.FloatField(source='station_id.longitude', allow_null=True)
    river = serializers.CharField(source='station_id.river', allow_null=True)
    basin_order = serializers.IntegerField(source='station_id.basin.basin_order', allow_null=True)
    basin = serializers.CharField(source='station_id.basin.name', allow_null=True)
    division = serializers.CharField(source='station_id.division', allow_null=True)
    district = serializers.CharField(source='station_id.district', allow_null=True)
    upazilla = serializers.CharField(source='station_id.upazilla', allow_null=True)
    union = serializers.CharField(source='station_id.union', allow_null=True)
    dangerlevel = serializers.FloatField(source='station_id.danger_level', allow_null=True)
    riverhighestwaterlevel = serializers.FloatField(source='station_id.highest_water_level', allow_null=True)

    class Meta:
        model = models.WaterLevelObservation
        fields = [
            'st_id','station_serial_no', 'name', 'lat', 'long', 'river', 'basin_order', 'basin',
            'division', 'district', 'upazilla', 'union', 'wl_date', 'waterlevel',
            'dangerlevel', 'riverhighestwaterlevel'
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in representation:
            if representation[field] is None:
                representation[field] = "-"
        return representation

class ThreeDaysObservedWaterLevelSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)
    wl_date = serializers.DateTimeField(source='observation_date', format='%Y-%m-%d %H:%M:%SZ')
    waterlevel = serializers.FloatField(source='water_level')

    class Meta:
        model = models.WaterLevelObservation
        fields = ['st_id', 'wl_date', 'waterlevel']

    def to_representation(self, instance):
        try:
            # Verify that the station_id exists in the Station model
            models.Station.objects.get(station_id=instance.station_id.station_id)
            representation = super().to_representation(instance)
            for field in representation:
                if representation[field] is None:
                    representation[field] = "-"
            return representation
        except models.Station.DoesNotExist:
            # Skip records with non-existent stations
            return None

class ExperimentalObservedWaterLevelSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)  # Map to Station.station_id
    wl_date = serializers.DateTimeField(source='observation_date', format='%Y-%m-%dT%H:%M:%SZ')  # Map to observation_date, UTC
    waterlevel = serializers.CharField(source='water_level')  # Map to water_level, as string

    class Meta:
        model = models.WaterLevelObservation
        fields = ['id','st_id', 'wl_date', 'waterlevel']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in representation:
            if representation[field] is None:
                representation[field] = "-"
        return representation

class SevenDaysWaterLevelSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id')
    name = serializers.CharField(source='station_id.name')
    lat = serializers.FloatField(source='station_id.latitude')
    long = serializers.FloatField(source='station_id.longitude')
    river = serializers.CharField(source='station_id.river')
    basin = serializers.CharField(source='station_id.basin.name', allow_null=True)
    division = serializers.CharField(source='station_id.division')
    district = serializers.CharField(source='station_id.district')
    upazilla = serializers.CharField(source='station_id.upazilla', allow_null=True)
    union = serializers.CharField(source='station_id.union', allow_null=True)
    wl_date = serializers.DateTimeField(source='observation_date', format='%Y-%m-%dT%H:%M:%S%z')
    waterlevel = serializers.DecimalField(source='water_level', max_digits=10, decimal_places=2)
    dangerlevel = serializers.FloatField(source='station_id.danger_level', allow_null=True)
    riverhighestwaterlevel = serializers.FloatField(source='station_id.highest_water_level', allow_null=True)

    class Meta:
        model = models.WaterLevelObservation
        fields = [
            'st_id', 'name', 'lat', 'long', 'river', 'basin',
            'division', 'district', 'upazilla', 'union', 'wl_date',
            'waterlevel', 'dangerlevel', 'riverhighestwaterlevel'
        ]

class WaterLevelForecastSerializer(serializers.ModelSerializer):
    station_id = serializers.PrimaryKeyRelatedField(queryset=models.Station.objects.all())
    
    class Meta:
        model = models.WaterLevelForecast
        fields = ['id', 'station_id', 'forecast_date', 'water_level']


class ForecastWaterLevelSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)  # Map to Station.station_id
    fc_date = serializers.DateTimeField(source='forecast_date', format='%Y-%m-%dT%H:%M:%SZ')  # Map to forecast_date, UTC
    waterlevel = serializers.CharField(source='water_level')  # Map to water_level, as string

    class Meta:
        model = models.WaterLevelForecast
        fields = ['st_id', 'fc_date', 'waterlevel']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in representation:
            if representation[field] is None:
                representation[field] = "-"
        return representation


class SevenDaysWaterLevelForecastSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)  # Map to Station.station_id
    fc_date = serializers.DateTimeField(source='forecast_date', format='%Y-%m-%dT%H:%M:%SZ')  # Map to forecast_date, UTC format
    waterlevel = serializers.CharField(source='water_level')  # Map to water_level, return as string

    class Meta:
        model = models.WaterLevelForecast
        fields = ['st_id', 'fc_date', 'waterlevel']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in representation:
            if representation[field] is None:
                representation[field] = "-"
        return representation


class FiveDaysForecastWaterLevelSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)
    fc_date = serializers.DateTimeField(source='forecast_date', format='%Y-%m-%d %H:%M:%SZ')
    waterlevel = serializers.FloatField(source='water_level')

    class Meta:
        model = models.WaterLevelForecast
        fields = ['st_id', 'fc_date', 'waterlevel']

    def to_representation(self, instance):
        try:
            # Verify that the station_id exists in the Station model
            models.Station.objects.get(station_id=instance.station_id.station_id)
            representation = super().to_representation(instance)
            for field in representation:
                if representation[field] is None:
                    representation[field] = "-"
            return representation
        except models.Station.DoesNotExist:
            # Skip records with non-existent stations
            return None

class SevenDaysForecastWaterLevelSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)
    fc_date = serializers.DateTimeField(source='forecast_date', format='%m-%d-%Y')
    waterlevel = serializers.FloatField(source='water_level')

    class Meta:
        model = models.WaterLevelForecast
        fields = ['st_id', 'fc_date', 'waterlevel']

    def to_representation(self, instance):
        try:
            # Verify that the station_id exists in the Station model
            models.Station.objects.get(station_id=instance.station_id.station_id)
            representation = super().to_representation(instance)
            for field in representation:
                if representation[field] is None:
                    representation[field] = "-"
            return representation
        except models.Station.DoesNotExist:
            # Skip records with non-existent stations
            return None

class TenDaysForecastWaterLevelSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id.station_id', allow_null=True)
    fc_date = serializers.DateTimeField(source='forecast_date', format='%m-%d-%Y')
    min = serializers.FloatField(source='waterlevel_min', allow_null=True)
    max = serializers.FloatField(source='waterlevel_max', allow_null=True)
    mean = serializers.FloatField(source='waterlevel_mean', allow_null=True)

    class Meta:
        model = models.WaterLevelForecastsExperimentals
        fields = ['st_id', 'fc_date', 'min', 'max', 'mean']

    def to_representation(self, instance):
        try:
            models.Station.objects.get(station_id=instance.station_id.station_id)
            representation = super().to_representation(instance)
            # Convert DecimalFields to float
            for field in ['min', 'max', 'mean']:
                if representation[field] is not None:
                    representation[field] = float(representation[field])
            return representation
        except Station.DoesNotExist:
            return None


class WaterLevelObservationExperimentalsSerializer(serializers.ModelSerializer):
    wl_id = serializers.IntegerField(source='id')
    st_id = serializers.IntegerField(source='station_id.station_id')
    wl_date = serializers.DateTimeField(source='observation_date')
    waterlevel = serializers.DecimalField(source='water_level', max_digits=10, decimal_places=2)

    class Meta:
        model = models.WaterLevelObservationExperimentals
        fields = ['wl_id', 'st_id', 'wl_date', 'waterlevel']


class WaterLevelForecastsExperimentalsSerializer(serializers.ModelSerializer):
    fc_id = serializers.IntegerField(source='id')
    st_id = serializers.IntegerField(source='station_id.station_id') # Accessing the 'station_id' field of the related Station model
    fc_date = serializers.DateTimeField(source='forecast_date')

    class Meta:
        model = models.WaterLevelForecastsExperimentals
        fields = ['fc_id', 'st_id', 'fc_date', 'waterlevel_min', 'waterlevel_max', 'waterlevel_mean']



class RainfallObservationSerializer(serializers.ModelSerializer):
    station_id = serializers.PrimaryKeyRelatedField(queryset=models.RainfallStation.objects.all())
    
    class Meta:
        model = models.RainfallObservation
        fields = ['id', 'station_id', 'observation_date', 'rainfall']

class FourtyDaysRainfallObservationSerializer(serializers.ModelSerializer):
    st_id = serializers.IntegerField(source='station_id_id')
    rf_date = serializers.DateTimeField(source='observation_date')

    class Meta:
        model = models.RainfallObservation
        fields = ['st_id', 'rf_date', 'rainfall']



class ObservedRainfallSerializer(serializers.Serializer):
    st_id = serializers.IntegerField(source='station_id.station_id')
    name = serializers.CharField(source='station_id.name', allow_null=True)
    basin = serializers.CharField(source='station_id.basin.name', allow_null=True)
    division = serializers.CharField(source='station_id.division', allow_null=True)
    district = serializers.CharField(source='station_id.district', allow_null=True)
    upazilla = serializers.CharField(source='station_id.upazilla', allow_null=True)
    lat = serializers.CharField(source='station_id.latitude', allow_null=True)
    long = serializers.CharField(source='station_id.longitude', allow_null=True)
    status = serializers.SerializerMethodField()
    normal_rainfall = serializers.SerializerMethodField()
    max_rainfall = serializers.SerializerMethodField()
    total_rainfall = serializers.SerializerMethodField()
    latest_date = serializers.DateTimeField(source='observation_date', allow_null=True)

    def get_status(self, obj):
        try:
            return 1 if obj.station_id.status else 0
        except AttributeError:
            return None

    def get_normal_rainfall(self, obj):
        try:
            today = datetime.today()
            month = today.month
            normal_rainfall = models.MonthlyRainfall.objects.filter(
                station_id=obj.station_id.station_id, month_serial=month
            ).values_list('normal_rainfall', flat=True).first()
            return normal_rainfall if normal_rainfall is not None else None
        except AttributeError:
            return None

    def get_max_rainfall(self, obj):
        try:
            today = datetime.today()
            month = today.month
            max_rainfall = models.MonthlyRainfall.objects.filter(
                station_id=obj.station_id.station_id, month_serial=month
            ).values_list('max_rainfall', flat=True).first()
            return max_rainfall if max_rainfall is not None else None
        except AttributeError:
            return None

    def get_total_rainfall(self, obj):
        try:
            total_rainfall = models.RainfallObservation.objects.filter(
                station_id=obj.station_id,
                observation_date=obj.observation_date
            ).aggregate(total_rainfall=Sum('rainfall'))['total_rainfall']
            return total_rainfall if total_rainfall is not None else None
        except AttributeError:
            return None

    class Meta:
        model = models.RainfallObservation
        fields = [
            'st_id', 'name', 'basin', 'division', 'district', 'upazilla',
            'lat', 'long', 'status', 'normal_rainfall', 'max_rainfall',
            'total_rainfall', 'latest_date'
        ]

# class RainfallObservationByDateSerializer(serializers.Serializer):
#     st_id = serializers.IntegerField(source='station_id.station_id')
#     station_id = serializers.CharField(source='station_id.station_code')
#     rf_date = serializers.DateTimeField(source='observation_date')
#     rainfall = serializers.DecimalField(max_digits=8, decimal_places=2)
#     name = serializers.SerializerMethodField()
#     basin = serializers.SerializerMethodField()
#     division = serializers.SerializerMethodField()
#     district = serializers.SerializerMethodField()
#     upazilla = serializers.SerializerMethodField()
#     lat = serializers.SerializerMethodField()
#     long = serializers.SerializerMethodField()
#     status = serializers.SerializerMethodField()
#     normal_rainfall = serializers.SerializerMethodField()
#     max_rainfall = serializers.SerializerMethodField()
#     # total_rainfall = serializers.SerializerMethodField()
#     # latest_date = serializers.SerializerMethodField()

#     def get_name(self, obj):
#         try:
#             return obj.station_id.name if obj.station_id and obj.station_id.name else None
#         except AttributeError:
#             return None

#     def get_basin(self, obj):
#         try:
#             return obj.station_id.basin.name if obj.station_id and obj.station_id.basin else None
#         except AttributeError:
#             return None

#     def get_division(self, obj):
#         try:
#             return obj.station_id.division if obj.station_id and obj.station_id.division else None
#         except AttributeError:
#             return None

#     def get_district(self, obj):
#         try:
#             return obj.station_id.district if obj.station_id and obj.station_id.district else None
#         except AttributeError:
#             return None

#     def get_upazilla(self, obj):
#         try:
#             return obj.station_id.upazilla if obj.station_id and obj.station_id.upazilla else None
#         except AttributeError:
#             return None

#     def get_lat(self, obj):
#         try:
#             return str(obj.station_id.latitude) if obj.station_id and obj.station_id.latitude is not None else None
#         except AttributeError:
#             return None

#     def get_long(self, obj):
#         try:
#             return str(obj.station_id.longitude) if obj.station_id and obj.station_id.longitude is not None else None
#         except AttributeError:
#             return None

#     def get_status(self, obj):
#         try:
#             return 1 if obj.station_id and obj.station_id.status else 0
#         except AttributeError:
#             return None

#     def get_normal_rainfall(self, obj):
#         try:
#             today = datetime.today()
#             month = today.month
#             normal_rainfall = models.MonthlyRainfall.objects.filter(
#                 station_id=obj.station_id.station_id, month_serial=month
#             ).values_list('normal_rainfall', flat=True).first()
#             return normal_rainfall if normal_rainfall is not None else None
#         except AttributeError:
#             return None

#     def get_max_rainfall(self, obj):
#         try:
#             today = datetime.today()
#             month = today.month
#             max_rainfall = models.MonthlyRainfall.objects.filter(
#                 station_id=obj.station_id.station_id, month_serial=month
#             ).values_list('max_rainfall', flat=True).first()
#             return max_rainfall if max_rainfall is not None else None
#         except AttributeError:
#             return None

#     # def get_total_rainfall(self, obj):
#     #     try:
#     #         total_rainfall = models.RainfallObservation.objects.filter(
#     #             station_id=obj.station_id
#     #         ).aggregate(total_rainfall=Sum('rainfall'))['total_rainfall']
#     #         return total_rainfall if total_rainfall is not None else None
#     #     except AttributeError:
#     #         return None

#     # def get_latest_date(self, obj):
#     #     try:
#     #         latest_entry = models.RainfallObservation.objects.filter(
#     #             station_id=obj.station_id
#     #         ).order_by('-observation_date').first()
#     #         return latest_entry.observation_date if latest_entry else None
#     #     except AttributeError:
#     #         return None

#     class Meta:
#         model = models.RainfallObservation
#         fields = [
#             'st_id', 'station_id', 'rf_date', 'rainfall', 'name', 'basin',
#             'division', 'district', 'upazilla', 'lat', 'long', 'status',
#             'normal_rainfall', 'max_rainfall'
#         ]



class RainfallObservationByDateSerializer(serializers.Serializer):
    st_id = serializers.IntegerField(source='station_id') # Changed source to directly use station_id
    station_id = serializers.CharField(source='station_code') # Changed source to station_code
    rf_date = serializers.DateTimeField() # rf_date will be directly passed
    rainfall = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True) # Allow null for rainfall
    name = serializers.SerializerMethodField()
    basin = serializers.SerializerMethodField()
    division = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    upazilla = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    long = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    normal_rainfall = serializers.SerializerMethodField()
    max_rainfall = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.get('name')

    def get_basin(self, obj):
        return obj.get('basin')

    def get_division(self, obj):
        return obj.get('division')

    def get_district(self, obj):
        return obj.get('district')

    def get_upazilla(self, obj):
        return obj.get('upazilla')

    def get_lat(self, obj):
        return obj.get('lat')

    def get_long(self, obj):
        return obj.get('long')

    def get_status(self, obj):
        return obj.get('status')

    def get_normal_rainfall(self, obj):
        # We'll fetch this in the view to avoid repeated database hits per station
        return obj.get('normal_rainfall')

    def get_max_rainfall(self, obj):
        # We'll fetch this in the view to avoid repeated database hits per station
        return obj.get('max_rainfall')
        
class ThreeDaysObservedRainfallSerializer(serializers.ModelSerializer):
    observation_date = serializers.DateTimeField(format="%d-%m-%Y")
    rainfall = serializers.DecimalField(max_digits=8, decimal_places=2, coerce_to_string=True)

    class Meta:
        model = RainfallObservation
        fields = ['station_id', 'observation_date', 'rainfall']



class ThresholdBasinsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ThresholdBasins
        fields = '__all__' 



class FloodmapsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Floodmaps
        fields = ['id', 'file_name', 'file_date','file']



class MonsoonConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model=models.MonsoonConfig
        fields='__all__'
        
        
        
        

"""
#######################################################################################
### ADDED BY: SHAIF    | DATE: 2025-08-13
### REQUESTED BY: JOBAYER
#######################################################################################
"""
# class rainfallObservationSerializer(serializers.ModelSerializer):

#     name=serializers.SerializerMethodField()
#     basin_order=serializers.SerializerMethodField()
#     basin=serializers.SerializerMethodField()
#     division=serializers.SerializerMethodField()
#     district=serializers.SerializerMethodField()
#     upazilla=serializers.SerializerMethodField()
#     lat=serializers.SerializerMethodField()
#     long=serializers.SerializerMethodField()
#     status=serializers.SerializerMethodField()
#     # unit=serializers.SerializerMethodField()

#     normal_rainfall=serializers.SerializerMethodField()
#     max_rainfall=serializers.SerializerMethodField()
#     latest_date = serializers.SerializerMethodField()  # New field for latest date

#         # "name": "Pateswari (Bhurungmari)",
#         # "basin": "Brahmaputra",
#         # "division": "Rangpur",
#         # "district": "Kurigram",
#         # "upazilla": "Bhurungamari",
#         # "lat": "25.9959",
#         # "long": "89.73",
#         # "status": 1,
#         # "unit": "mm"

#     total_rainfall = serializers.IntegerField()

#     def get_name(self,RainfallObservations):
#         name = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('name', flat=True)[0]
#         return name
    
#     def get_basin_order(self,RainfallObservations):
#         basin_order = FfwcRainfallStations.objects.filter(id=RainfallObservations['st_id']).values_list('basin_order', flat=True)[0]
#         return basin_order

#     def get_basin(self,RainfallObservations):
#         basin = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('basin', flat=True)[0]
#         return basin

#     def get_division(self,RainfallObservations):
#         division = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('division', flat=True)[0]
#         return division

#     def get_district(self,RainfallObservations):
#         district = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('district', flat=True)[0]
#         return district

#     def get_upazilla(self,RainfallObservations):
#         upazilla = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('upazilla', flat=True)[0]
#         return upazilla

#     def get_lat(self,RainfallObservations):
#         lat = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('lat', flat=True)[0]
#         return lat

#     def get_long(self,RainfallObservations):
#         long = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('long', flat=True)[0]
#         return long

#     def get_status(self,RainfallObservations):
#         status = FfwcRainfallStationsNew.objects.filter(id=RainfallObservations['st_id']).values_list('status', flat=True)[0]
#         return status

#     def get_normal_rainfall(self,RainfallObservations):
#         today = datetime.today()
#         month = today.month
#         normal_rainfall = MonthlyRainfall.objects.filter(
#             station_id=RainfallObservations['st_id'],month_serial=month).values_list('normal_rainfall', flat=True)
#         return normal_rainfall[0] if normal_rainfall else None

#     def get_max_rainfall(self,RainfallObservations):
#         today = datetime.today()
#         month = today.month
#         max_rainfall = MonthlyRainfall.objects.filter(
#             station_id=RainfallObservations['st_id'],month_serial=month).values_list('max_rainfall', flat=True)
#         return max_rainfall[0] if max_rainfall else None
    
#     def get_latest_date(self, rainfall_observation):
#         # Use the RainfallObservations model directly
#         latest_entry = RainfallObservations.objects.filter(st_id=rainfall_observation['st_id']).order_by('-rf_date').first()
#         return latest_entry.rf_date if latest_entry else None  # Return latest date or None

#     def get_latest_date(self, rainfall_observation):
#             today = datetime.now()
#             current_month = today.month
#             current_year = today.year

#             # Find the latest observation for the station within the current month and up to today
#             latest_entry = RainfallObservations.objects.filter(
#                 st_id=rainfall_observation['st_id'],
#                 rf_date__year=current_year,
#                 rf_date__month=current_month,
#                 rf_date__lte=today # Limit to today's date
#             ).order_by('-rf_date').first()
            
#             return latest_entry.rf_date if latest_entry else None

#     class Meta:
#         model = RainfallObservations
#         fields=[
#             'st_id','name','basin_order','basin',
#             'division','district','upazilla','lat','long','status',
#             'normal_rainfall','max_rainfall','total_rainfall','latest_date']




"""
#######################################################################################
### ADDED BY: SHAIF    | DATE: 2025-08-14
### ASSIGNED BY: SAJIB BHAI
#######################################################################################
"""
class FfwcStations2025Serializer(serializers.ModelSerializer):
    web_id = serializers.IntegerField(source='station_id', read_only=True)
    # station_serial_no = serializers.IntegerField(source='station_serial_no')

    class Meta:
        model = Station
        fields = ['web_id', 'station_serial_no']
        
class FfwcStations2025UpdateSerializer(serializers.ModelSerializer):
    # station_id = serializers.IntegerField(source='station_id', read_only=True)
    # station_serial_no = serializers.IntegerField(source='station_serial_no')

    class Meta:
        model = Station
        fields = ['station_id', 'station_serial_no']
        
class FfwcStations2025BulkUpdateSerializer(serializers.ModelSerializer):
    web_id = serializers.IntegerField(source='station_id', read_only=True)
    # station_serial_no = serializers.IntegerField(source='station_serial_no')

    class Meta:
        model = Station
        fields = ['web_id', 'station_serial_no']
        




from data_load.models import BulletinRelatedManue
class BulletinRelatedManueSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulletinRelatedManue
        fields = ['id', 'title', 'title_bn', 'url']




# Adding Flood Alert Serializers

        
class WaterlevelAlertSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = models.WaterlevelAlert
        fields = ['id', 'alert_no', 'alert_type']  



class DistrictFloodAlertSerializer(serializers.ModelSerializer):
    
    alert_type = serializers.PrimaryKeyRelatedField(
        queryset=models.WaterlevelAlert.objects.all()
    )

    class Meta:
        model = models.DistrictFloodAlert
        fields = ['alert_date', 'district_name', 'alert_type']
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=models.DistrictFloodAlert.objects.all(),
                fields=('alert_date', 'district_name'),
                message="Alert for this district and date already exists."
            )
        ]



from data_load.models import EnsModelChoice
class EnsModelChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnsModelChoice 
        fields = ['id', 'station_id', 'date', 'model_name']



from .models import ScheduledTask

class ScheduledTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for the ScheduledTask model.
    """
    class Meta:
        model = ScheduledTask
        # Fields to include in the serialized output
        fields = ['id', 'task_name', 'is_enabled', 'description']


class ScheduledTaskToggleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledTask
        fields = ['id', 'task_name', 'is_enabled', 'description']
        
        read_only_fields = ['id', 'task_name', 'description']


from .models import DistrictFloodAlertAutoUpdate

class DistrictFloodAlertAutoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistrictFloodAlertAutoUpdate
        fields = ['id', 'district_name', 'auto_update']


class DistrictFloodAlertAutoUpdateStatusSerializer(serializers.Serializer):
    auto_update = serializers.BooleanField()
    class Meta:
        fields = ['auto_update']


from .models import JsonEntry
class JsonEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        # For GET requests: take the data from the model's `data` field
        # and add the `id` to it for the final API output.
        representation = instance.data
        representation['id'] = instance.id
        return representation

    def create(self, validated_data):
        # For POST requests: take the entire validated JSON payload
        # and save it directly into the `data` field.
        return JsonEntry.objects.create(data=validated_data)

    def update(self, instance, validated_data):
        # For PATCH/PUT requests: merge the incoming JSON
        # with the existing data in the `data` field.
        instance.data.update(validated_data)
        instance.save()
        return instance

    def get_fields(self):
        fields = super().get_fields()
        request_data = getattr(self, 'initial_data', {})

        # Use the safely retrieved request_data to add fields
        for key, value in request_data.items():
            if key not in fields:
                fields[key] = serializers.JSONField(required=False)
        return fields





