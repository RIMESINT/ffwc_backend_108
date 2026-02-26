import json
import os

from datetime import timedelta, datetime as dt

from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.views import View

from rest_framework import status 
from rest_framework.views import APIView
from rest_framework.response import Response 
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework import generics
from rest_framework.exceptions import APIException

from weasyprint import HTML

# import mixins
from mixins.mail_configuration.mail_conf import MailSendForDissiminationEmail

from ffwc_django_project import settings_local

from app_bulletin.models import (
    AgrometBulletin, AgrometBulletinSourceDestinationDetails
)
from user_authentication.models import (
    GeoData, GeoLevel
)
from app_weather_api.models import (
    Source
) 

from app_bulletin.pdf_conversion.am_bulletin_pdf.forecast_data_fetch import ForcastDataFetch
from app_bulletin.pdf_conversion.am_bulletin_pdf.observe_data_fetch import ObserveDataFetch






from celery import shared_task
from django.core.mail import send_mail

from app_bulletin.pdf_conversion.am_bulletin_pdf.views import PDFGenerator
from mixins.mail_configuration.mail_conf import MailSendForDissiminationEmail
from ffwc_django_project import settings_local
from ffwc_django_project.settings import (
    BASE_DIR
)



from app_dissemination.models import (
    DisseminationStatus, EmailsDisseminationQueue, 
)
from app_emails.models import (
    MailingList
)


# from app_bulletin.pdf_conversion.am_bulletin_pdf.views import AgrometBulletinPDFReturnView

#  import project constant
from ffwc_django_project.project_constant import ( 
    APP_DISSEMINATION, GEO_DATA,
)

APP_DISSEMINATION_STATUS = APP_DISSEMINATION['dissemination_status']
GEO_DATA_BHUTAN = GEO_DATA["BHUTAN"]["country_id"]









class CountryWiseBulletinGenerate:
    

    def bhutan_format_bulletin_save(data):
        """
            #######################################################
            ### Bhutan Format Bulletin Save
            #######################################################
        """

        pdf_generator = PDFGenerator()

        bulletin_id = None 

        # bulletin_obj = json.dumps(data, indent=4)
        # bulletin_obj = json.loads(data)
        bulletin_obj = data 
        
        forecast_date_parts = data['forecast_date'].split("-")
        adv_year = forecast_date_parts[0] 
        adv_month = forecast_date_parts[1] 
        adv_date = forecast_date_parts[2] 
        
        forecast_date = dt.strptime(data['forecast_date'], "%Y-%m-%d").date()

        location_obj = GeoData.objects.filter(pk=data["locations"][0])[0]

        country = GeoData.objects.filter(pk=data['country'])[0]
        level = GeoLevel.objects.filter(pk=data['level'])[0]
        source = Source.objects.filter(pk=data['source'])[0]
        observe_data_source = Source.objects.filter(pk=data['observe_data_source'])[0] 

        forecast_end_date = forecast_date + timedelta(days=4)
        observe_end_date = forecast_date - timedelta(days=4)

        ####################################################
        ### fetching forecast data
        ###################################################
        forecast_data = ForcastDataFetch.level_wise_forecast_data_date_wise_all_loc_bhutan(
            bulletin_id=bulletin_id, level=level.id, 
            source=source.name, country=country.id, 
            fdate=forecast_date,    #.strftime('%Y%m%d'), 
            specific_location_list=data["locations"][0]
        )
        # print("forecast_data: ", forecast_data)

        forecast_rf_data_obj = forecast_data["rf_data_obj"]
        forecast_tmax_data_obj = forecast_data["tmax_data_obj"]
        forecast_tmin_data_obj = forecast_data["tmin_data_obj"]
        forecast_rh_data_obj = forecast_data["rh_data_obj"]
        forecast_windspd_data_obj = forecast_data["windspd_data_obj"] 


        ####################################################
        ### fetching observe data
        ###################################################
        observe_data = ObserveDataFetch.level_wise_observe_data_date_wise_all_loc_bhutan(
            bulletin_id=bulletin_id, level=level.id, 
            source=observe_data_source.name, country=country.id, 
            fdate=forecast_date,    #.strftime('%Y%m%d'), 
            observe_end_date=observe_end_date,
            specific_location_list=data["locations"][0]
        )
        # print("forecast_data: ", forecast_data)

        observe_rf_data_obj = observe_data["rf_data_obj"]
        observe_tmax_data_obj = observe_data["tmax_data_obj"]
        observe_tmin_data_obj = observe_data["tmin_data_obj"]
        observe_rh_data_obj = observe_data["rh_data_obj"]
        observe_windspd_data_obj = observe_data["windspd_data_obj"] 

        # print("observe_rf_data_obj: ", len(observe_rf_data_obj))
        # for a in observe_rf_data_obj:
        #     print("########### observe_date: ", a.observe_date, " --- rf: ", a.val_avg)

        context = {
            "bulletin_obj": bulletin_obj, 
            "location_obj": location_obj, 
            "forecast_date": forecast_date,
            "forecast_end_date": forecast_end_date, 
            "observe_end_date": observe_end_date,

            "forecast_rf_data_obj": forecast_rf_data_obj,
            "forecast_tmax_data_obj": forecast_tmax_data_obj,
            "forecast_tmin_data_obj": forecast_tmin_data_obj,
            "forecast_rh_data_obj": forecast_rh_data_obj,
            "forecast_windspd_data_obj": forecast_windspd_data_obj,

            "observe_rf_data_obj": observe_rf_data_obj,
            "observe_tmax_data_obj": observe_tmax_data_obj,
            "observe_tmin_data_obj": observe_tmin_data_obj,
            "observe_rh_data_obj": observe_rh_data_obj,
            "observe_windspd_data_obj": observe_windspd_data_obj,
        }

        result = pdf_generator.generate_pdf_and_send_email(
            template_name='bhutan/bhutan_bulletin_create_update.html',
            context=context,  
        )
        # print("PDF Generation Result:", result)
        pdf_data = result['pdf_file']


        file_name = str(data['details'])
        # file_name = "bulletin_pdf"
        media_directory = "/media/assets/bulletin/pdf_archive/"+str(country.name)+"/"+str(adv_year)+"/"+str(location_obj.name)+"/"+str(adv_month)+"/"+str(adv_date)+"/"
        file_path = str(BASE_DIR)+media_directory
        
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        
        with open(f"{file_path}/{file_name}.pdf", 'wb') as f:
            f.write(pdf_data)

        return {
            "pdf_file_path": media_directory+file_name+".pdf", 
            "advisory_year": adv_year, 
            "advisory_month": adv_month, 
            "advisory_day": adv_date, 
        }

    def bhutan_format_bulletin_update(data, bulletin_obj_qs):
        """
            #######################################################
            ### Bhutan Format Bulletin Update
            #######################################################
        """

        pdf_generator = PDFGenerator()

        bulletin_id = None 

        # bulletin_obj = json.dumps(data, indent=4)
        # bulletin_obj = json.loads(data)
        bulletin_obj = data 
        
        forecast_date_parts = data['forecast_date'].split("-")
        adv_year = forecast_date_parts[0] 
        adv_month = forecast_date_parts[1] 
        adv_date = forecast_date_parts[2] 
        
        forecast_date = dt.strptime(data['forecast_date'], "%Y-%m-%d").date()

        location_obj = GeoData.objects.filter(pk=bulletin_obj_qs.locations[0])[0]

        country = GeoData.objects.filter(pk=bulletin_obj_qs.country.id)[0]
        level = GeoLevel.objects.filter(pk=bulletin_obj_qs.level.id)[0]
        source = Source.objects.filter(pk=bulletin_obj_qs.source.id)[0]
        observe_data_source = Source.objects.filter(pk=bulletin_obj_qs.observe_data_source.id)[0] 

        forecast_end_date = forecast_date + timedelta(days=4)
        observe_end_date = forecast_date - timedelta(days=4)

        ####################################################
        ### fetching forecast data
        ###################################################
        forecast_data = ForcastDataFetch.level_wise_forecast_data_date_wise_all_loc_bhutan(
            bulletin_id=bulletin_id, level=level.id, 
            source=source.name, country=country.id, 
            fdate=forecast_date,    #.strftime('%Y%m%d'), 
            specific_location_list=bulletin_obj_qs.locations[0]
        )
        # print("forecast_data: ", forecast_data)

        forecast_rf_data_obj = forecast_data["rf_data_obj"]
        forecast_tmax_data_obj = forecast_data["tmax_data_obj"]
        forecast_tmin_data_obj = forecast_data["tmin_data_obj"]
        forecast_rh_data_obj = forecast_data["rh_data_obj"]
        forecast_windspd_data_obj = forecast_data["windspd_data_obj"] 


        ####################################################
        ### fetching observe data
        ###################################################
        observe_data = ObserveDataFetch.level_wise_observe_data_date_wise_all_loc_bhutan(
            bulletin_id=bulletin_id, level=level.id, 
            source=observe_data_source.name, country=country.id, 
            fdate=forecast_date,    #.strftime('%Y%m%d'), 
            observe_end_date=observe_end_date,
            specific_location_list=bulletin_obj_qs.locations[0]
        )
        # print("forecast_data: ", forecast_data)

        observe_rf_data_obj = observe_data["rf_data_obj"]
        observe_tmax_data_obj = observe_data["tmax_data_obj"]
        observe_tmin_data_obj = observe_data["tmin_data_obj"]
        observe_rh_data_obj = observe_data["rh_data_obj"]
        observe_windspd_data_obj = observe_data["windspd_data_obj"] 

        # print("observe_rf_data_obj: ", len(observe_rf_data_obj))
        # for a in observe_rf_data_obj:
        #     print("########### observe_date: ", a.observe_date, " --- rf: ", a.val_avg)

        context = {
            "bulletin_obj": bulletin_obj, 
            "location_obj": location_obj, 
            "forecast_date": forecast_date,
            "forecast_end_date": forecast_end_date, 
            "observe_end_date": observe_end_date,

            "forecast_rf_data_obj": forecast_rf_data_obj,
            "forecast_tmax_data_obj": forecast_tmax_data_obj,
            "forecast_tmin_data_obj": forecast_tmin_data_obj,
            "forecast_rh_data_obj": forecast_rh_data_obj,
            "forecast_windspd_data_obj": forecast_windspd_data_obj,

            "observe_rf_data_obj": observe_rf_data_obj,
            "observe_tmax_data_obj": observe_tmax_data_obj,
            "observe_tmin_data_obj": observe_tmin_data_obj,
            "observe_rh_data_obj": observe_rh_data_obj,
            "observe_windspd_data_obj": observe_windspd_data_obj,
        }

        result = pdf_generator.generate_pdf_and_send_email(
            template_name='bhutan/bhutan_bulletin_create_update.html',
            context=context,  
        )
        # print("PDF Generation Result:", result)
        pdf_data = result['pdf_file']


        file_name = str(data['details'])
        # file_name = "bulletin_pdf"
        media_directory = "/media/assets/bulletin/pdf_archive/"+str(country.name)+"/"+str(adv_year)+"/"+str(location_obj.name)+"/"+str(adv_month)+"/"+str(adv_date)+"/"
        file_path = str(BASE_DIR)+media_directory
        
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        
        with open(f"{file_path}/{file_name}.pdf", 'wb') as f:
            f.write(pdf_data)

        return {
            "pdf_file_path": media_directory+file_name+".pdf", 
            "advisory_year": adv_year, 
            "advisory_month": adv_month, 
            "advisory_day": adv_date, 
        }

        
        
