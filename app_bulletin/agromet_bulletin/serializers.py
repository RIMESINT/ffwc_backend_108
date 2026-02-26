from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator

# import models  
from app_bulletin.models import (
    AgrometBulletin
)
from app_visualization.models import (
    Source
) 

# from app_bulletin.agromet_bulletin.helper.country_wise_bulletin_generate import (
#     CountryWiseBulletinGenerate
# )

#  import mixins
# from mixins.utility_upload.file_upload import document_upload









"""
    ##################################################
    ### COMMON SERIALIZERS
    ##################################################
"""  
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

class SourceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class ObservationSourceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


"""
    ##################################################
    ### CROP STAGE SERIALIZERS
    ##################################################
""" 
class AMBulletinLVReqSerializer(serializers.Serializer):         
    page_size = serializers.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)], required=False)    

class AMBulletinLVResponseSerializer(serializers.ModelSerializer):   
    forecast_source = SourceSerializer() 
    observe_data_source = ObservationSourceSerializer() 
    # unique_id = serializers.SerializerMethodField('get_unique_id')

    class Meta:
        model = AgrometBulletin 
        fields = [
            'id', 'bulletin_provider_details', 'bulletin_header_location_detail',
            'bulletin_issue_date_details', 'details', 'forecast_date', #'plot_path', 
            'forecast_highlight', 'observed_highlight', 
            'forecast_source', 'observe_data_source', 
            'next_week_forecast', 'glossary', 'basin_details_list', 
            'rf_stations_list', 
            'station_json_data', 'flash_flood_forecast_json', 'hydrograph_details_json',
            'all_advisory', 'special_advisory',
            'all_advisory_hide_show', 'special_advisory_header_name', 
            'bulletin_header_location_detail', 'pdf_file_path', 
            'advisory_year', 'advisory_month', 'advisory_day'
        ]  

    # def get_unique_id(self, AgrometBulletin):
    #     unique_id = str(AgrometBulletin.country.unique_value) +":"+ str(AgrometBulletin.forecast_date)
    #     # print("####### Date: ", AgrometBulletin.country.unique_value)
    #     return unique_id  


"""
    Serializers for PestFavConConfDetailsView[get]
"""
class AMBulletinMapPathReqSerializer(serializers.Serializer):
    forecast_date = serializers.DateField()
    country = serializers.IntegerField()


"""
    Serializers for PestFavConConfDetailsView[get]
"""
class AMBulletinDetailsDateReqSerializer(serializers.Serializer):
    forecast_date = serializers.DateField()
    country = serializers.IntegerField()




"""
    Serializers for PestFavConConfDetailsView[get]
"""
class AMBulletinDetailsReqSerializer(serializers.Serializer):
    pass

class AMBulletinDetailsResSerializer(serializers.ModelSerializer):    
    forecast_source = SourceSerializer()  
    observe_data_source = ObservationSourceSerializer()  

    class Meta:
        model = AgrometBulletin 
        fields = [
            'id', 'bulletin_provider_details', 'bulletin_header_location_detail',
            'bulletin_issue_date_details', 'details', 'forecast_date', #'plot_path', 
            'forecast_highlight', 'observed_highlight', 
            'forecast_source', 'observe_data_source', 
            'next_week_forecast', 'glossary', 'basin_details_list', 
            'rf_stations_list',  
            'station_json_data', 'flash_flood_forecast_json', 'hydrograph_details_json',
            'all_advisory', 'special_advisory',
            'all_advisory_hide_show', 'special_advisory_header_name', 
            'bulletin_header_location_detail', 'pdf_file_path', 
            'advisory_year', 'advisory_month', 'advisory_day'
        ]  


"""
    Serializers for Ideal Param Conf Add Req Serializer
"""
class AMBulletinAddReqSerializer(serializers.ModelSerializer):

    def save(self, user, data):

        forecast_source = Source.objects.filter(pk=data['forecast_source'])[0]
        observe_data_source = Source.objects.filter(pk=data['observe_data_source'])[0]


        # path_details = None
        # if country.id == GEO_DATA_BHUTAN:
        #     path_details = CountryWiseBulletinGenerate.bhutan_format_bulletin_save(
        #         data=data
        #     )
        # else:
        path_details = {
            "pdf_file_path": None, 
            "advisory_year": None, 
            "advisory_month": None, 
            "advisory_day": None, 
        }


        # print(" ######## inside serializer ########### ")
        csip_conf = AgrometBulletin( 
            forecast_date = data['forecast_date'],   
            bulletin_provider_details = data['bulletin_provider_details'],   
            bulletin_header_location_detail = data['bulletin_header_location_detail'],   
            bulletin_issue_date_details = data['bulletin_issue_date_details'],   
            details = data['details'],   
            forecast_highlight = data['forecast_highlight'],   
            observed_highlight = data['observed_highlight'],   
            next_week_forecast = data['next_week_forecast'],   
            glossary = data['glossary'],   
            forecast_source = forecast_source,
            observe_data_source = observe_data_source,
            basin_details_list = data["basin_details_list"],
            rf_stations_list = data["rf_stations_list"],
            
            station_json_data = data["station_json_data"],
            flash_flood_forecast_json = data["flash_flood_forecast_json"],
            hydrograph_details_json = data["hydrograph_details_json"],
                        
            all_advisory = data['all_advisory'],
            all_advisory_hide_show = data['all_advisory_hide_show'],
            special_advisory = data['special_advisory'],
            special_advisory_header_name = data['special_advisory_header_name'],

            pdf_file_path = path_details['pdf_file_path'] if path_details['pdf_file_path'] is not None else None,
            advisory_year = path_details['advisory_year'] if path_details['advisory_year'] is not None else None, 
            advisory_month = path_details['advisory_month'] if path_details['advisory_month'] is not None else None, 
            advisory_day = path_details['advisory_day'] if path_details['advisory_day'] is not None else None, 
            
            # created_by = user,
            # updated_by = user 
        )  
        csip_conf.save()
        return csip_conf  

    class Meta:
        model = AgrometBulletin
        fields = [
            'forecast_date', "bulletin_provider_details",
            "bulletin_header_location_detail", "bulletin_issue_date_details",
            'details',
        ]  


"""
    Serializers for PestDetailsView[put]
"""
class AMBulletinUpdateReqSerializer(serializers.ModelSerializer):

    def update(self, user, id, data, files):  
        
        # bulletin_obj_qs = AgrometBulletin.objects.filter(pk=id)[0]
        forecast_source = Source.objects.filter(pk=data['forecast_source'])[0]
        observe_data_source = Source.objects.filter(pk=data['observe_data_source'])[0]


        # path_details = None
        # if country.id == GEO_DATA_BHUTAN:
        #     path_details = CountryWiseBulletinGenerate.bhutan_format_bulletin_update(
        #         data=data, bulletin_obj_qs=bulletin_obj_qs
        #     )
        # else:
        path_details = {
            "pdf_file_path": None, 
            "advisory_year": None, 
            "advisory_month": None, 
            "advisory_day": None, 
        }


        
        csip_conf = AgrometBulletin.objects.filter(pk=id).update(
            forecast_date = data['forecast_date'],   
            bulletin_provider_details = data['bulletin_provider_details'],   
            bulletin_header_location_detail = data['bulletin_header_location_detail'],   
            bulletin_issue_date_details = data['bulletin_issue_date_details'],   
            details = data['details'],   
            forecast_highlight = data['forecast_highlight'],   
            observed_highlight = data['observed_highlight'],   
            next_week_forecast = data['next_week_forecast'],   
            glossary = data['glossary'],   
            forecast_source = forecast_source,
            observe_data_source = observe_data_source,
            basin_details_list = data["basin_details_list"],
            rf_stations_list = data["rf_stations_list"],
            
            station_json_data = data["station_json_data"],
            flash_flood_forecast_json = data["flash_flood_forecast_json"],
            hydrograph_details_json = data["hydrograph_details_json"],
            
            all_advisory = data['all_advisory'],
            all_advisory_hide_show = data['all_advisory_hide_show'],
            special_advisory = data['special_advisory'],
            special_advisory_header_name = data['special_advisory_header_name'],

            pdf_file_path = path_details['pdf_file_path'] if path_details['pdf_file_path'] is not None else None,
            advisory_year = path_details['advisory_year'] if path_details['advisory_year'] is not None else None, 
            advisory_month = path_details['advisory_month'] if path_details['advisory_month'] is not None else None, 
            advisory_day = path_details['advisory_day'] if path_details['advisory_day'] is not None else None, 
            
            # updated_by = user  
        )   
        return csip_conf

    class Meta:
        model = AgrometBulletin
        fields = [
            'forecast_date', "bulletin_provider_details",
            "bulletin_header_location_detail", "bulletin_issue_date_details",
            'details', 
        ]  



"""
    Serializers for PestDetailsView[delete]
"""
class AMBulletinDeleteReqSerializer(serializers.Serializer):

    def delete(self, user, id):
        csip_conf = AgrometBulletin.objects.filter(
            pk=id
        ).delete() 
        return csip_conf   





"""
    Serializers for PestDetailsView[put]
"""
class AMBulletinUpdate2ReqSerializer(serializers.ModelSerializer):

    def update(self, user, id, data, files):  
        
        csip_conf = AgrometBulletin.objects.filter(pk=id).update(      
            forecast_highlight = data['forecast_highlight'],   
            observed_highlight = data['observed_highlight'],   
            next_week_forecast = data['next_week_forecast'],   
            glossary = data['glossary'],   
            updated_by = user  
        )   
        return csip_conf

    class Meta:
        model = AgrometBulletin
        fields = [
            'forecast_highlight', 'observed_highlight', 
            'next_week_forecast', 'glossary', 
        ]  