from datetime import timedelta

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

from ffwc_django_project import settings

# from app_bulletin.models import (
#     AgrometBulletin, AgrometBulletinSourceDestinationDetails
# )
# from user_authentication.models import (
#     GeoData, GeoLevel
# )

# from app_bulletin.pdf_conversion.am_bulletin_pdf.forecast_data_fetch import ForcastDataFetch
# from app_bulletin.pdf_conversion.am_bulletin_pdf.observe_data_fetch import ObserveDataFetch






from celery import shared_task
from django.core.mail import send_mail

# from app_bulletin.pdf_conversion.am_bulletin_pdf.views import PDFGenerator
from mixins.mail_configuration.mail_conf import MailSendForDissiminationEmail
from ffwc_django_project import settings



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

from ffwc_django_project.settings import MEDIA_URL, BASE_DIR, MEDIA_ROOT


APP_DISSEMINATION_STATUS = APP_DISSEMINATION['dissemination_status']
# GEO_DATA_BHUTAN = GEO_DATA["BHUTAN"]["country_id"]









class CountryWiseBulletinFormatSend:
    

    # def bhutan_format_bulletin_send(email_details):
    #     """
    #         #######################################################
    #         ### Bhutan Format Bulletin send
    #         #######################################################
    #     """

    #     recipient_list = list(email_details.total_emails)
    #     print(" ################################### recipient_list: ", recipient_list)
        
    #     pdf_generator = PDFGenerator()

    #     bulletin_id = email_details.am_bulletin.id

    #     bulletin_obj = AgrometBulletin.objects.filter(pk=bulletin_id)[0]
    #     location_obj = GeoData.objects.filter(pk=bulletin_obj.locations[0])[0]
    #     forecast_end_date = bulletin_obj.forecast_date + timedelta(days=4)
    #     observe_end_date = bulletin_obj.forecast_date - timedelta(days=4)

    #     ####################################################
    #     ### fetching forecast data
    #     ###################################################
    #     forecast_data = ForcastDataFetch.level_wise_forecast_data_date_wise_all_loc_bhutan(
    #         bulletin_id=bulletin_id, level=bulletin_obj.level.id, 
    #         source=bulletin_obj.source.name, country=bulletin_obj.country.id, 
    #         fdate=bulletin_obj.forecast_date,    #.strftime('%Y%m%d'), 
    #         specific_location_list=bulletin_obj.locations[0]
    #     )
    #     # print("forecast_data: ", forecast_data)

    #     forecast_rf_data_obj = forecast_data["rf_data_obj"]
    #     forecast_tmax_data_obj = forecast_data["tmax_data_obj"]
    #     forecast_tmin_data_obj = forecast_data["tmin_data_obj"]
    #     forecast_rh_data_obj = forecast_data["rh_data_obj"]
    #     forecast_windspd_data_obj = forecast_data["windspd_data_obj"] 


    #     ####################################################
    #     ### fetching observe data
    #     ###################################################
    #     observe_data = ObserveDataFetch.level_wise_observe_data_date_wise_all_loc_bhutan(
    #         bulletin_id=bulletin_id, level=bulletin_obj.level.id, 
    #         source=bulletin_obj.observe_data_source.name, country=bulletin_obj.country.id, 
    #         fdate=bulletin_obj.forecast_date,    #.strftime('%Y%m%d'), 
    #         observe_end_date=observe_end_date,
    #         specific_location_list=bulletin_obj.locations[0]
    #     )
    #     # print("forecast_data: ", forecast_data)

    #     observe_rf_data_obj = observe_data["rf_data_obj"]
    #     observe_tmax_data_obj = observe_data["tmax_data_obj"]
    #     observe_tmin_data_obj = observe_data["tmin_data_obj"]
    #     observe_rh_data_obj = observe_data["rh_data_obj"]
    #     observe_windspd_data_obj = observe_data["windspd_data_obj"] 

    #     # print("observe_rf_data_obj: ", len(observe_rf_data_obj))
    #     # for a in observe_rf_data_obj:
    #     #     print("########### observe_date: ", a.observe_date, " --- rf: ", a.val_avg)

    #     context = {
    #         "bulletin_obj": bulletin_obj, 
    #         "location_obj": location_obj, 
    #         "forecast_end_date": forecast_end_date, 
    #         "observe_end_date": observe_end_date,

    #         "forecast_rf_data_obj": forecast_rf_data_obj,
    #         "forecast_tmax_data_obj": forecast_tmax_data_obj,
    #         "forecast_tmin_data_obj": forecast_tmin_data_obj,
    #         "forecast_rh_data_obj": forecast_rh_data_obj,
    #         "forecast_windspd_data_obj": forecast_windspd_data_obj,

    #         "observe_rf_data_obj": observe_rf_data_obj,
    #         "observe_tmax_data_obj": observe_tmax_data_obj,
    #         "observe_tmin_data_obj": observe_tmin_data_obj,
    #         "observe_rh_data_obj": observe_rh_data_obj,
    #         "observe_windspd_data_obj": observe_windspd_data_obj,
    #     }

    #     result = pdf_generator.generate_pdf_and_send_email(
    #         template_name='bhutan/bhutan_bulletin_new.html',
    #         context=context,  
    #     )
    #     # print("PDF Generation Result:", result)
    #     pdf_data = result['pdf_file']

    #     # recipient_list = ['shifullah@rimes.int']

    #     # Send Email with PDF
    #     mail_conf_dict = {
    #         "subject": email_details.subject,
    #         "message": email_details.message,
    #         "email_from": settings.EMAIL_HOST_USER,
    #         "recipient_list": recipient_list,
    #         "attachment_data": pdf_data,
    #         "attachment_filename": bulletin_obj.details+".pdf",
    #     }
    #     MailSendForDissiminationEmail.agromet_bulletin_mail(mail_conf_dict=mail_conf_dict)
        
    #     updated_rows = EmailsDisseminationQueue.objects.filter(pk=email_details.id).update(
    #         status = DisseminationStatus.objects.filter(pk=APP_DISSEMINATION_STATUS["Sent"])[0]
    #     )
        
    ########################################################################
    ########################################################################
    ########################################################################\
    ### Send email for TL 
    ########################################################################
    ########################################################################
    ########################################################################
    # def tl_format_bulletin_send(email_details):
    #     """
    #         #######################################################
    #         ### Bhutan Format Bulletin send
    #         #######################################################
    #     """

    #     recipient_list = list(email_details.total_emails)
    #     print(" ################################### recipient_list: ", recipient_list)
        
    #     pdf_generator = PDFGenerator()

    #     bulletin_id = email_details.am_bulletin.id

    #     bulletin_obj = AgrometBulletin.objects.filter(pk=bulletin_id)[0]
    #     location_obj = GeoData.objects.filter(pk=bulletin_obj.locations[0])[0]
    #     forecast_end_date = bulletin_obj.forecast_date + timedelta(days=4)
    #     observe_end_date = bulletin_obj.forecast_date - timedelta(days=4)

    #     ####################################################
    #     ### fetching forecast data
    #     ###################################################
    #     forecast_data = ForcastDataFetch.level_wise_forecast_data_date_wise_all_loc_bhutan(
    #         bulletin_id=bulletin_id, level=bulletin_obj.level.id, 
    #         source=bulletin_obj.source.name, country=bulletin_obj.country.id, 
    #         fdate=bulletin_obj.forecast_date,    #.strftime('%Y%m%d'), 
    #         specific_location_list=bulletin_obj.locations[0]
    #     )
    #     # print("forecast_data: ", forecast_data)

    #     forecast_rf_data_obj = forecast_data["rf_data_obj"]
    #     forecast_tmax_data_obj = forecast_data["tmax_data_obj"]
    #     forecast_tmin_data_obj = forecast_data["tmin_data_obj"]
    #     forecast_rh_data_obj = forecast_data["rh_data_obj"]
    #     forecast_windspd_data_obj = forecast_data["windspd_data_obj"] 


    #     ####################################################
    #     ### fetching observe data
    #     ###################################################
    #     observe_data = ObserveDataFetch.level_wise_observe_data_date_wise_all_loc_bhutan(
    #         bulletin_id=bulletin_id, level=bulletin_obj.level.id, 
    #         source=bulletin_obj.observe_data_source.name, country=bulletin_obj.country.id, 
    #         fdate=bulletin_obj.forecast_date,    #.strftime('%Y%m%d'), 
    #         observe_end_date=observe_end_date,
    #         specific_location_list=bulletin_obj.locations[0]
    #     )
    #     # print("forecast_data: ", forecast_data)

    #     observe_rf_data_obj = observe_data["rf_data_obj"]
    #     observe_tmax_data_obj = observe_data["tmax_data_obj"]
    #     observe_tmin_data_obj = observe_data["tmin_data_obj"]
    #     observe_rh_data_obj = observe_data["rh_data_obj"]
    #     observe_windspd_data_obj = observe_data["windspd_data_obj"] 

    #     # print("observe_rf_data_obj: ", len(observe_rf_data_obj))
    #     # for a in observe_rf_data_obj:
    #     #     print("########### observe_date: ", a.observe_date, " --- rf: ", a.val_avg)

    #     context = {
    #         "bulletin_obj": bulletin_obj, 
    #         "location_obj": location_obj, 
    #         "forecast_end_date": forecast_end_date, 
    #         "observe_end_date": observe_end_date,

    #         "forecast_rf_data_obj": forecast_rf_data_obj,
    #         "forecast_tmax_data_obj": forecast_tmax_data_obj,
    #         "forecast_tmin_data_obj": forecast_tmin_data_obj,
    #         "forecast_rh_data_obj": forecast_rh_data_obj,
    #         "forecast_windspd_data_obj": forecast_windspd_data_obj,

    #         "observe_rf_data_obj": observe_rf_data_obj,
    #         "observe_tmax_data_obj": observe_tmax_data_obj,
    #         "observe_tmin_data_obj": observe_tmin_data_obj,
    #         "observe_rh_data_obj": observe_rh_data_obj,
    #         "observe_windspd_data_obj": observe_windspd_data_obj,
    #     }

    #     result = pdf_generator.generate_pdf_and_send_email(
    #         template_name='tl/bhutan_bulletin_new.html',
    #         context=context,  
    #     )
    #     # print("PDF Generation Result:", result)
    #     pdf_data = result['pdf_file']

    #     # recipient_list = ['shifullah@rimes.int']

    #     # Send Email with PDF
    #     mail_conf_dict = {
    #         "subject": email_details.subject,
    #         "message": email_details.message,
    #         "email_from": settings.EMAIL_HOST_USER,
    #         "recipient_list": recipient_list,
    #         "attachment_data": pdf_data,
    #         "attachment_filename": bulletin_obj.details+".pdf",
    #     }
    #     MailSendForDissiminationEmail.agromet_bulletin_mail(mail_conf_dict=mail_conf_dict)
        
    #     updated_rows = EmailsDisseminationQueue.objects.filter(pk=email_details.id).update(
    #         status = DisseminationStatus.objects.filter(pk=APP_DISSEMINATION_STATUS["Sent"])[0]
    #     )
        
        
    ########################################################################
    ########################################################################
    ########################################################################\
    ### Send email for FFWC 
    ########################################################################
    ########################################################################
    ########################################################################
    def ffwc_format_bulletin_send(email_details):
        """
            #######################################################
            ### Bhutan Format Bulletin send
            #######################################################
        """

        recipient_list = list(email_details.total_emails)
        print(" ################################### recipient_list: ", recipient_list)
        
        pdf_data = str(BASE_DIR) + str(MEDIA_URL) + str(email_details.attached_file_path)
        # pdf_file_path = os.path.join(settings.BASE_DIR, settings.MEDIA_URL[1:], email_details.attached_file_path)
        print(" ################################### pdf_data file path: ", pdf_data)
        
        # Read the file content as bytes
        with open(pdf_data, 'rb') as pdf_file:
            attachment_data = pdf_file.read()
            # attachment_filename = os.path.basename(pdf_data)

        # recipient_list = ['shifullah@rimes.int']

        # Send Email with PDF
        mail_conf_dict = {
            "subject": email_details.subject,
            "context": email_details.message,
            # "message": email_details.message,
            "email_from": settings.EMAIL_HOST_USER,
            "recipient_list": recipient_list,
            "attachment_data": attachment_data,
            "attachment_filename": email_details.attached_file_name,
        }
        mail_status = MailSendForDissiminationEmail.agromet_bulletin_mail(mail_conf_dict=mail_conf_dict)
        
        if mail_status==True:
            updated_rows = EmailsDisseminationQueue.objects.filter(pk=email_details.id).update(
                status = DisseminationStatus.objects.filter(pk=APP_DISSEMINATION_STATUS["Sent"])[0]
            )
        
