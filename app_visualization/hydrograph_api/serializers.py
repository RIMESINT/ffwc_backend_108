#########################################################################
#########################################################################
#########################################################################
#########################################################################
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

"""
    Serializers for PestFavConConfDetailsView[get]
"""
class FfwcHydrographV1ReqSerializer(serializers.Serializer):
    place_name = serializers.CharField()
    date = serializers.CharField()
    # pass

class FfwcHydrographV1ResSerializer(serializers.Serializer):  
    hydrograph_path = serializers.CharField()    

    

    

