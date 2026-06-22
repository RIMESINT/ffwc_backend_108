from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator


# import models
from app_subscriptions.models import (
    EmailsSubscription
)
# from data_load.models import (
#     AuthUser
# )
from django.contrib.auth.models import User, Group










"""
    ##################################################
    ### COMMON SERIALIZERS
    ##################################################
""" 
class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField() 
    name = serializers.CharField()  

    class Meta:
        model = User
        fields = ['id', 'name']

class CountrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    unique_key = serializers.CharField()
    unique_value = serializers.CharField() 
    latitude = serializers.DecimalField(max_digits=5, decimal_places=2)
    longitude = serializers.DecimalField(max_digits=5, decimal_places=2)
    zoom_level = serializers.IntegerField()

class LevelSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    ordering = serializers.IntegerField()
    
class LocationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    level_name = serializers.CharField()
    unique_key = serializers.CharField()
    unique_value = serializers.CharField() 

"""
    ##################################################
    ### CROP STAGE SERIALIZERS
    ##################################################
""" 
class DiseaseLVReqSerializer(serializers.Serializer):
    # created_by = serializers.IntegerField()      
    page_size = serializers.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)], required=False)    


class DiseaseLVResponseSerializer(serializers.ModelSerializer):    
    # created_by = UserSerializer() 
    # location = LocationSerializer() 
    # level = LevelSerializer() 
    # country = CountrySerializer() 

    class Meta:
        model = EmailsSubscription 
        fields = [
            'id', 'email',  
        ] 



"""
    Serializers for DiseaseDetailsView[get]
"""
class DiseaseDetailsReqSerializer(serializers.Serializer):
    pass

class DiseaseDetailsResSerializer(serializers.ModelSerializer):   
    # created_by = UserSerializer() 
    # location = LocationSerializer() 
    # level = LevelSerializer() 
    # country = CountrySerializer()

    class Meta:
        model = EmailsSubscription
        fields = [
            'id', 'email',   
        ] 



"""
    Serializers for Ideal Param Conf Add Req Serializer
"""
class DiseaseAddReqItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    infestation_stages = serializers.IntegerField() 
    image = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    file_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)

class DiseaseAddReqSerializer(serializers.Serializer):
    
    email = serializers.EmailField() 
    # country = serializers.IntegerField()
    # level = serializers.IntegerField()
    # location = serializers.IntegerField()

    def save(self, user, data): 
        
        # location = GeoData.objects.filter(
        #     id= data['location']
        #     # id= user.location
        # )
        # if len(location)==0:
        #     location = None
        # else:
        #     location = location[0]
            
        # country = GeoData.objects.filter(
        #     id= data['country']
        # )[0]
        # level = GeoLevel.objects.filter(
        #     id= data['level']
        # )[0]
            
        csip_conf = EmailsSubscription(
            email = data['email'],  
            # country= country, 
            # level= level, 
            # location= location, 
            # created_by = user,
            # updated_by = user 
        )  
        csip_conf.save()
        return csip_conf  

    # class Meta:
    #     model = EmailsSubscription
    #     fields = ['email']



"""
    Serializers for DiseaseDetailsView[put]
"""
class DiseaseUpdateReqSerializer(serializers.ModelSerializer):

    def update(self, user, id, data): 
        # location = GeoData.objects.filter(
        #     id= data['location']
        #     # id= user.location
        # )
        # if len(location)==0:
        #     location = None
        # else:
        #     location = location[0]
            
        # country = GeoData.objects.filter(
        #     id= data['country']
        # )[0]
        # level = GeoLevel.objects.filter(
        #     id= data['level']
        # )[0]
        
        csip_conf = EmailsSubscription.objects.filter(pk=id).update(
            email = data['email'],  
            # country= country, 
            # level= level, 
            # location= location,
            # updated_by = user  
        )   
        return csip_conf

    class Meta:
        model = EmailsSubscription
        fields = [
            'email',   
        ] 



"""
    Serializers for DiseaseDetailsView[delete]
"""
class DiseaseDeleteReqSerializer(serializers.Serializer):

    def delete(self, user, id):
        csip_conf = EmailsSubscription.objects.filter(
            pk=id
        ).delete() 
        return csip_conf   



