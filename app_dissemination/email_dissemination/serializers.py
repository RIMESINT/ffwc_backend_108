import ast

from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator

# import models
from app_dissemination.models import (
    DisseminationStatus,
    EmailsDisseminationQueue
)
from app_emails.models import (
    MailingList
)
from app_subscriptions.models import (
    EmailsSubscription
)
# from data_load.models import (
#     AuthUser
# ) 
from django.contrib.auth.models import User, Group



#  import project constant
from ffwc_django_project.project_constant import (
    GEO_DATA, SESAME_USERS, DIRECTORY,
    APP_DISSEMINATION
)

from ffwc_django_project.settings import MEDIA_URL, BASE_DIR, MEDIA_ROOT
#  import mixins
from mixins.utility_upload.file_upload import document_upload


APP_DISSEMINATION_STATUS = APP_DISSEMINATION['dissemination_status']










class DisseminationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisseminationStatus
        fields = ['id', 'name']

class MailingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MailingList
        fields = ['id', 'name', 'emails'] 

# class MailingList2Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = MailingList
#         fields = ['id', 'group_name', 'emails', 'country'] 

# class CropCountryResponseSerializer(serializers.ModelSerializer): 

#     class Meta:
#         # model = GeoData
#         fields = ['id', 'name', 'unique_key', 'unique_value']

# class LevelSerializer(serializers.Serializer):
#     id = serializers.IntegerField()
#     name = serializers.CharField()
#     ordering = serializers.IntegerField()

# class SourceSerializer(serializers.Serializer):
#     id = serializers.IntegerField()
#     name = serializers.CharField()

    
# class AMBulletinLVResponseSerializer(serializers.ModelSerializer):     
#     country = CropCountryResponseSerializer() 
#     level = LevelSerializer() 
#     source = SourceSerializer() 
#     unique_id = serializers.SerializerMethodField('get_unique_id')

#     class Meta:
#         model = AgrometBulletin 
#         fields = [
#             'id', 'unique_id', 'details', 'forecast_date', #'plot_path',
#             'country', 'level', 'source',
#             'forecast_highlight', 'observed_highlight', 
#             'next_week_forecast', 'glossary'
#         ]  

#     def get_unique_id(self, AgrometBulletin):
#         unique_id = str(AgrometBulletin.country.unique_value) +":"+ str(AgrometBulletin.forecast_date)
#         # print("####### Date: ", AgrometBulletin.country.unique_value)
#         return unique_id 




class CropLAVCustomReqSerializer(serializers.Serializer):

    # crop_type_id = serializers.IntegerField(validators=[MinValueValidator(1)])
    # country_id = serializers.IntegerField(validators=[MinValueValidator(1)])  
    page_size = serializers.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)], required=False)
    
class CropResponseSerializer(serializers.Serializer): 
    id = serializers.IntegerField() 
    subject = serializers.CharField()
    message = serializers.CharField()
    # am_bulletin = AMBulletinLVResponseSerializer()  
    # attached_file_name = serializers.CharField()
    # attached_file_path = serializers.CharField()
    attached_file_path = serializers.SerializerMethodField('get_crop_icon')
    email_group = serializers.ListField(child=serializers.IntegerField(), required=False, allow_null=True) 
    total_emails = serializers.JSONField(required=False)
    # email_group_2 = serializers.ListField(child=serializers.IntegerField(), required=False, allow_null=True) 
    # description = serializers.CharField()
    # country = CropCountryResponseSerializer() 
    # status = serializers.PrimaryKeyRelatedField(queryset=DisseminationStatus.objects.all(), required=False, allow_null=True)
    status = DisseminationStatusSerializer(read_only=True)
    updated_at = serializers.DateTimeField()

    # class Meta:
    #    model = EmailsDisseminationQueue
    #     # fields = '__all__'
    #     fields = [
    #         'id', 'name', 'description', 'attached_file', 'country', 
    #         'crop_type', 'updated_at', #'crop_varieties'
    #     ]

    def get_crop_icon(self, EmailsDisseminationQueue):
        if (EmailsDisseminationQueue.attached_file_path == None) or (EmailsDisseminationQueue.attached_file_path == ''): 
            attached_file_path = ""
        else: 
            attached_file_path = str(MEDIA_URL)+str(EmailsDisseminationQueue.attached_file_path)
        return attached_file_path

    def to_representation(self, instance):
        """
        Convert `email_group` IDs to MailingList details.
        """
        ret = super().to_representation(instance)
        
        email_group_ids = ret.pop('email_group', [])
        ret['email_group'] = MailingListSerializer(MailingList.objects.filter(id__in=email_group_ids), many=True).data

        # email_group_ids_2 = ret.pop('email_group', [])
        # ret['email_group_2'] = MailingList2Serializer(MailingList.objects.filter(id__in=email_group_ids_2), many=True).data
        
        return ret







class CropCountryResponseSerializer(serializers.ModelSerializer): 

    class Meta:
        # model = GeoData
        fields = ['id', 'name', 'unique_key', 'unique_value']
        
class DefaultGeoLevelResponseSerializer(serializers.ModelSerializer): 

    class Meta:
        # model = GeoLevel
        fields = ['id', 'name',]
        


"""
    Serializers for CropViewSet[crop_details]
"""
class DefaultGeoLevelDetailsReqSerializer(serializers.Serializer):
    pass

class DefaultGeoLevelDetailsResSerializer(serializers.Serializer):
    id = serializers.IntegerField()  
    country = CropCountryResponseSerializer()  
    level = DefaultGeoLevelResponseSerializer()  

    # class Meta:
    #     model = CountryWiseDefaultLevelSetting
    #     fields = ['id', 'name', 'description', 'attached_file', 'country', 'crop_type']


        

"""
    Serializers for CropDetailsView[put]
"""
class DefaultGeoLevelUpdateReqSerializer(serializers.Serializer):

    def update(self, user, country_id, data):
        # country = GeoData.objects.filter(pk=country_id)[0]
        # level = GeoLevel.objects.filter(pk=data['level'])[0] 

        crop = EmailsDisseminationQueue.objects.filter(country=country_id).update(
            country=country,
            level=level,   
            updated_by=user
        ) 
        return crop  

    # class Meta:
    #     model = EmailsDisseminationQueue 
    #     fields = ['name']


"""
    Serializers for CropDetailsView[delete]
"""
class DefaultGeoLevelTypeDeleteReqSerializer(serializers.Serializer):

    def delete(self, user, country_id):
        crop = EmailsDisseminationQueue.objects.filter(country=country_id).delete() 
        return crop    



"""
    Serializers for AM Bulletin To Queue
"""
class BulletinQueueListSerializer(serializers.Serializer):
    country = serializers.IntegerField()
    level = serializers.IntegerField()
    am_bulletin = serializers.IntegerField()
    email_group = serializers.ListField(child=serializers.IntegerField())
    subject = serializers.CharField()
    message = serializers.CharField()

class DefaultGeoLevelAddReqSerializer(serializers.Serializer):
    bulletin_queue_list = serializers.ListField(
        child=BulletinQueueListSerializer(),
        allow_empty=True,
        required=False
    )

    def save(self, user, data, files):
        
        crop_image_url = None
        saved_file_name_final = None

        if 'am_bulletin_pdf' in files:
            destination_dir = str(BASE_DIR) + str(MEDIA_URL) + DIRECTORY["app_dissemination"]["am_bulletin_pdf"]
            saved_file_name = document_upload(files['am_bulletin_pdf'], files['am_bulletin_pdf'].name, destination_dir) 
            crop_image_url = DIRECTORY["app_dissemination"]["am_bulletin_pdf"] + saved_file_name
            saved_file_name_final = saved_file_name
            # SesameUser.objects.filter(pk=user.id).update(profile_image=crop_image_url)
        # print(" media url: ", crop_image_url)
        # country = GeoData.objects.filter(pk=data['country'])[0]
        # level = GeoLevel.objects.filter(pk=data['level'])[0] 
        # source = Source.objects.filter(pk=data['source'])[0] 
        # am_bulletin = AgrometBulletin.objects.filter(pk=data['am_bulletin'])[0] 
        status = DisseminationStatus.objects.filter(pk=APP_DISSEMINATION_STATUS["Pending"])[0]  

        email_list = []
        email_group = ast.literal_eval(data['email_group'])
        for group_id in email_group:
            if group_id == 1:
                subs_email_list = list(EmailsSubscription.objects.values_list(
                    'email', flat=True
                ))
                # print("subs_email_list: ", subs_email_list)
                if len(subs_email_list)>0:
                    email_list.extend(subs_email_list)
                
            group_emails_obj = MailingList.objects.filter(pk=group_id)[0]
            group_emails = group_emails_obj.emails
            email_list.extend(group_emails)
            # print("email_list: ", email_list)
        final_email_set = set(email_list)
        final_email_list = list(final_email_set)
        # print("final_email_list: ", final_email_list)

        edq = EmailsDisseminationQueue( 
            subject = data['subject'],
            message = data['message'],
            attached_file_path=crop_image_url,
            attached_file_name=saved_file_name_final,
            email_group = email_group,
            total_emails = final_email_list, 
            status= status, 
            created_by=user.id,
            updated_by=user.id 
        )  
        # print(" $$$$$$$$$$$ edq: ", edq)
        edq.save()
        return edq   
    
    # class Meta:
    #     model = EmailsDisseminationQueue 
    #     fields = ['name']#, 'country', 'crop_type']
