from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator

#  import models
from app_visualization.models import (
    Source, Parameter,
    SystemState, BasinDetails,
)

# import MEDIA URL 










class ObjectDataSourceSerializer(serializers.ModelSerializer):
    # id = serializers.IntegerField()
    # name = serializers.CharField()
    # name_visualize = serializers.CharField()
    # source_type = serializers.CharField() 
    # source_data_type = serializers.IntegerField()
    # longitude = serializers.DecimalField(max_digits=5, decimal_places=2)
    # zoom_level = serializers.IntegerField()

    class Meta:
        model = Source
        fields = '__all__'


class BasinDetailsSerializer(serializers.ModelSerializer): 

    class Meta:
        model = BasinDetails
        fields = '__all__'
        

### -------------------------------------------------------------------------------- ###
### Serializer for SourceViewSet
### -------------------------------------------------------------------------------- ###
class SystemStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemState
        fields = ['id','name', 'last_update', 'updated_at']

class SourceDDReqSerializer(serializers.Serializer):  
    forecast_data_source = serializers.IntegerField()
    # pass

# class SourceDDResponseSerializer(serializers.ModelSerializer): 
class SourceDDResponseSerializer(serializers.Serializer): 
    id = serializers.IntegerField()
    name = serializers.CharField()
    file_name = serializers.CharField()
    file_path = serializers.CharField()
    station_id = serializers.CharField()
    division = serializers.CharField()
    district = serializers.CharField()
    upazilla = serializers.CharField()
    river_name = serializers.CharField()
    lat = serializers.CharField() 
    long = serializers.CharField() 
    altitude = serializers.CharField() 
    status = serializers.IntegerField() 
    unit = serializers.CharField() 
    forecast_data_source = ObjectDataSourceSerializer()   
    system_states = serializers.SerializerMethodField('get_system_states')
    
    def get_system_states(self, obj):
        system_states = SystemState.objects.filter(source=obj.forecast_data_source)
        return SystemStateSerializer(system_states, many=True).data




"""
    Serializers for PestFavConConfDetailsView[get]
"""
class RFObsReqSerializer(serializers.Serializer):
    day = serializers.IntegerField()
    # pass

class RFObsDetailsResSerializer(serializers.Serializer):  
    # date = serializers.DateField()   
    datetime = serializers.DateTimeField()   
    accu_stream_flow = serializers.DecimalField(max_digits=10, decimal_places=2) 

    # class Meta:
    #     model = AgrometBulletin 
    #     fields = [
    #         'id', 'bulletin_provider_details', 
    #         'forecast_highlight', 'observed_highlight', 
    #         'forecast_source', 'observe_data_source', 
    #         'next_week_forecast', 'glossary', 'basin_details_list', 
    #         'rf_stations_list', 
    #     ]  