from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator

#  import models
from app_visualization.models import (
    Source, 
    SystemState,
)

# import MEDIA URL 











### -------------------------------------------------------------------------------- ###
### Serializer for SourceViewSet
### -------------------------------------------------------------------------------- ###

class ForcastStateDDReqSerializer(serializers.Serializer): 
    parameter = serializers.IntegerField()  
    source = serializers.IntegerField()  
    forecast_date = serializers.CharField()  
    # basin_details = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)

class ForcastDDResponseSerializer(serializers.ModelSerializer):
    parameter = serializers.IntegerField()  
    source = serializers.IntegerField()  
    forecast_date = serializers.IntegerField()  
    basin_details = serializers.ListField(child=serializers.IntegerField())

    # class Meta:
    #     model = SystemState
    #     fields = ['id', 'name', 'source', 'last_update', 'updated_at']

