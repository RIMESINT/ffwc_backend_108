from rest_framework import serializers
from .models import IndianStations, IndianWaterLevelObservations

class IndianStationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndianStations
        fields = [
            'id', 'station_name', 'state_name', 'district', 'basin_name', 'river_name',
            'latitude', 'longitude', 'division_name', 'type_of_site', 'distance',
            'within_ganges', 'within_brahmaputra', 'within_meghna', 'station_code',
            'dangerlevel', 'warning_level', 'highest_flow_level'
        ]

# class IndianWaterLevelObservationsSerializer(serializers.ModelSerializer):
#     station_code = serializers.CharField(source='station.station_code', read_only=True)

#     class Meta:
#         model = IndianWaterLevelObservations
#         fields = ['id', 'station', 'station_code', 'data_time', 'waterlevel']

class IndianWaterLevelObservationsSerializer(serializers.ModelSerializer):
    station_code = serializers.CharField(source='station.station_code', read_only=True)

    class Meta:
        model = IndianWaterLevelObservations
        # Changed 'station' to 'station_id' for desired output
        fields = ['id', 'station_id', 'station_code', 'data_time', 'waterlevel']
