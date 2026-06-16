import pandas as pd

from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator

#  import models
from app_visualization.models import (
    Source, Parameter,
    SystemState, BasinDetails,
    RainfallObservation,
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
        fields = ['id', 'name', 'last_update', 'updated_at']

class SourceDDReqSerializer(serializers.Serializer):  
    observe_data_source = serializers.IntegerField()
    # pass

# class SourceDDResponseSerializer(serializers.ModelSerializer): 
class SourceDDResponseSerializer(serializers.Serializer): 
    id = serializers.IntegerField()
    name = serializers.CharField()
    basin = serializers.CharField()
    division = serializers.CharField()
    district = serializers.CharField()
    upazilla = serializers.CharField()
    lat = serializers.CharField() 
    long = serializers.CharField() 
    altitude = serializers.CharField() 
    status = serializers.IntegerField() 
    unit = serializers.CharField() 
    observe_data_source = ObjectDataSourceSerializer() 
    observe_data_source_network = serializers.CharField() 
    basin_details = BasinDetailsSerializer() 
    system_states = serializers.SerializerMethodField('get_system_states')
    accu_rainfall_count = serializers.SerializerMethodField('get_rainfall_observations')
    
    def get_system_states(self, obj):
        system_states = SystemState.objects.filter(source=obj.observe_data_source)
        return SystemStateSerializer(system_states, many=True).data

    def get_rainfall_observations(self, obj):
        # Fetch all rainfall observations related to this station (obj)
        # rainfall_observations = RainfallObservation.objects.filter(st=obj)
        # print(" $$$$$$$$$$$$$ obj: ", obj.id)
        # return RainfallObservationSerializer(rainfall_observations, many=True).data
        
        try: 
            queryset = RainfallObservation.objects.filter(st__id=obj.id) 

            data = list(queryset.values())
            df = pd.DataFrame(data)
            # print(df)
            # print(" &&&&&&&&&&& Column name: ", df.columns)
            if df.empty:
                return -1.0

            # df['rf_date'] = pd.to_datetime(df['rf_date'])
            df['date'] = df['rf_date'].dt.date
            df = df.sort_values(
                by=['date', 'rf_date'], ascending=[False, True], 
                # inplace=True
            )

            df = df.drop_duplicates(subset=['date', 'rf_date'])
            df.reset_index(drop=True, inplace=True)
            
            last_row_each_day = df.groupby('date').tail(1)
            last_row_each_day.reset_index(drop=True, inplace=True)
            # print(last_row_each_day)
            # df = last_row_each_day.head(int(req_data["day"]))
            df = last_row_each_day.head(7)
            # print(df)
            
            # df['rainFall'] = pd.to_numeric(df['rainFall'], errors='coerce')
            total_rainfall = df['rainFall'].sum()
            # print("Total Rainfall:", total_rainfall)
            
            return total_rainfall
        except Exception as e:
                return 0.0



"""
    Serializers for PestFavConConfDetailsView[get]
"""
class RFObsReqSerializer(serializers.Serializer):
    day = serializers.IntegerField()
    # pass

class RFObsDetailsResSerializer(serializers.Serializer):     
    rf_id = serializers.IntegerField()
    rf_date = serializers.DateTimeField()   
    rainFall = serializers.DecimalField(max_digits=10, decimal_places=2)
    st = SourceDDResponseSerializer() 

    # class Meta:
    #     model = AgrometBulletin 
    #     fields = [
    #         'id', 'bulletin_provider_details', 
    #         'forecast_highlight', 'observed_highlight', 
    #         'forecast_source', 'observe_data_source', 
    #         'next_week_forecast', 'glossary', 'basin_details_list', 
    #         'rf_stations_list', 
    #     ]  
    

