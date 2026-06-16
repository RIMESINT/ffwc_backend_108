# from datetime import timedelta

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

# from ffwc_django_project import settings



# from app_bulletin.pdf_conversion.am_bulletin_pdf.forecast_data_fetch import ForcastDataFetch
# from app_bulletin.pdf_conversion.am_bulletin_pdf.observe_data_fetch import ObserveDataFetch






from celery import shared_task
from django.core.mail import send_mail

# from app_bulletin.pdf_conversion.am_bulletin_pdf.views import PDFGenerator
from app_dissemination.healper_files.email_task_queqe_dissimination import (
    CountryWiseBulletinFormatSend
)
from mixins.mail_configuration.mail_conf import MailSendForDissiminationEmail
# from ffwc_django_project import settings



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
GEO_DATA_TL = GEO_DATA["TL"]["country_id"]










"""
    #######################################################################
    #######################################################################
    Dummy task
    #######################################################################
    #######################################################################
"""
# from celery import shared_task
from datetime import datetime #timedelta

# @shared_task
# def my_periodic_task():
#     """
#         Testing task
#     """
#     import logging
#     # Your task logic goes here
#     print("Running periodic task at: ", datetime.now())
#     # logging.debug("Running periodic task at: ", datetime.now())
#     # logging.info("Running periodic task at: ", datetime.now())
#     logging.warning('This is a warning message')
#     # logging.error("Running periodic task at: ", datetime.now())
#     # logging.critical("Running periodic task at: ", datetime.now())









@shared_task(bind=True, max_retries=20, default_retry_delay=100) # 600 ses = 10 minutes
def send_new_insertion_bulletin_email_task(self, email_id):
    """
        #######################################################
        ### New row Insert in DB then email sending task will 
        ### execute as queue
        #######################################################
    """
    try:
        have_to_send_email_obj = EmailsDisseminationQueue.objects.filter(pk=email_id)

        for email_details in have_to_send_email_obj:
            # if email_details.am_bulletin.country.id == GEO_DATA_BHUTAN:
            #     CountryWiseBulletinFormatSend.bhutan_format_bulletin_send(email_details)
            # elif email_details.am_bulletin.country.id == GEO_DATA_TL:
                # CountryWiseBulletinFormatSend.tl_format_bulletin_send(email_details)
            # else:
            #     CountryWiseBulletinFormatSend.bhutan_format_bulletin_send(email_details)
            CountryWiseBulletinFormatSend.ffwc_format_bulletin_send(email_details)

        print(" $$$$$$$$$$$$$$$$$$ Email sent successfully $$$$$$$$$$$$$$$$$$$$ ")

    except Exception as exc: 
        raise self.retry(exc=exc)






















