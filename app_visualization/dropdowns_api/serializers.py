from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator

#  import models
from app_visualization.models import (
    Source, Parameter,
    SystemState, BasinDetails,
)

# import MEDIA URL 











### -------------------------------------------------------------------------------- ###
### Serializer for SourceViewSet
### -------------------------------------------------------------------------------- ###
class SourceDatatypeDDReqSerializer(serializers.Serializer):  
    # source_type = serializers.CharField()
    pass
 

class SourceDatatypeDDResponseSerializer(serializers.Serializer): 
    id = serializers.IntegerField()
    name = serializers.CharField()
    



class SourceDDReqSerializer(serializers.Serializer):  
    source_type = serializers.CharField()
    source_data_type = serializers.IntegerField()
    # pass

# class SourceDDResponseSerializer(serializers.ModelSerializer): 
class SourceDDResponseSerializer(serializers.Serializer): 
    id = serializers.IntegerField()
    name = serializers.CharField()
    source_type = serializers.CharField() 
    destination_path = serializers.SerializerMethodField('get_des_path') 

    def get_des_path(self, Parameter):
        if Parameter.destination_path is not None:
            # destination_path = str(Parameter.destination_path)+"ECMWF_HRES_VIS/"
            destination_path = str(Parameter.destination_path)
            return destination_path



class SystemStateDDReqSerializer(serializers.Serializer): 
    source = serializers.IntegerField()  

class SystemStateDDResponseSerializer(serializers.ModelSerializer):
    source = SourceDDResponseSerializer()

    class Meta:
        model = SystemState
        fields = ['id', 'name', 'source', 'last_update', 'updated_at']



"""
    Serializer for parameters drop down
"""
class ParametersDDReqSerializer(serializers.Serializer): 
    # source = serializers.IntegerField()  
    pass

class ParametersDDResponseSerializer(serializers.ModelSerializer): 

    class Meta:
        model = Parameter
        fields = '__all__'



"""
    Serializer for basin drop down
"""
class BasinsDDReqSerializer(serializers.Serializer): 
    # source = serializers.IntegerField()  
    pass

class BasinsDDResponseSerializer(serializers.ModelSerializer): 

    class Meta:
        model = BasinDetails
        fields = '__all__'
