import ast

from rest_framework import status 
from rest_framework.views import APIView
from rest_framework.response import Response 
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework import generics
from rest_framework.exceptions import APIException

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction


# import serializer
from app_dissemination.email_dissemination.serializers import (  
    CropResponseSerializer, CropLAVCustomReqSerializer, 
    DefaultGeoLevelDetailsReqSerializer, DefaultGeoLevelDetailsResSerializer,
    DefaultGeoLevelUpdateReqSerializer,
    DefaultGeoLevelTypeDeleteReqSerializer, 
    DefaultGeoLevelAddReqSerializer                          
)

# import models 
from app_dissemination.models import (
    EmailsDisseminationQueue,
)
# from data_load.models import (
#     AuthUser
# )
from django.contrib.auth.models import User, Group

# import mixins
from mixins.pagination_mixins.pagination import PaginationSetup, StandardResultsSetPagination   #, PaginationSetup.custom_standard_pagination
# from mixins.pagination_mixins.pagination.PaginationSetup import PaginationSetup.custom_standard_pagination
from mixins.exception_mixins.exceptions import CustomAPIException
# for permission mixins
from mixins.user_permissions.permissions import CustomUserPermission as cap 

from mixins.lookup.upper_case import UpperCase

#  import project constant
from ffwc_django_project.project_constant import PAGINATION_CONSTANT










class AMBulletinToQueueView(generics.ListAPIView):
    """ 
        Purpose: list of crop types

        Method: GET
        Args:
                crop_type_id: Positive Integer
                country_id: Positive Integer 

        Returns:
            JSON response containing message, status and data if applicable:
                Success:
                    status: Positive Integer
                    next: URL
                    previous: URL
                    limit: Positive Integer
                    results: List of JSON
                Failure:
                    message: JSON
                    status: Positive Integer
    """
    
    permission_classes = (IsAuthenticated,)
    queryset = EmailsDisseminationQueue.objects.all()
    serializer_class = CropResponseSerializer
    pagination_class = StandardResultsSetPagination
    # filter_backends = [filters.DjangoFilterBackend]
    # filterset_class = CropNameFilter  # Use the custom filter class

    def get_queryset(self):
        user = self.request.user 
        req_serializer = CropLAVCustomReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():  
            if 'page_size' in self.request.GET:
                self.pagination_class = PaginationSetup.custom_standard_pagination(page_size=self.request.GET['page_size'])
            # if 'crop_type_id' in self.request.GET:
            #     return EmailsDisseminationQueue.objects.filter(crop_type=self.request.GET['crop_type_id'], country=self.request.GET['country_id'])

            return EmailsDisseminationQueue.objects.all() 
        raise CustomAPIException(req_serializer.errors)



"""
    API for CROP TYPE DETAILS & UPDATE & DELETE 
"""
class AMBulletinToQueueDetailsView(APIView):
    """ 
        Purpose: details of crop type 

        Method: POST
        Args:
                name: String

        Returns:
            JSON response containing message, status and data if applicable:
                Success:
                    status: Positive Integer 
                    results: List of JSON
                Failure:
                    message: JSON
                    status: Number
    """
    
    permission_classes = (IsAuthenticated,)
    queryset = EmailsDisseminationQueue.objects.all()
    serializer_class = CropResponseSerializer 

    def get(self, request, id):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        req_serializer = DefaultGeoLevelDetailsReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():
            if len(EmailsDisseminationQueue.objects.filter(pk=id))==0:
                return Response(dict(message='Default level for this country doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            queryset = EmailsDisseminationQueue.objects.filter(pk=id)  

            res_serializer = CropResponseSerializer(queryset, many=True)  
            return Response(res_serializer.data[0], status=status.HTTP_200_OK)  
        raise CustomAPIException(req_serializer.errors)

    # def put(self, request, id):
    #     """
    #         API for UPDATE by using ID
    #     """
    #     user = self.request.user 
    #     data = self.request.data
    #     req_serializer = DefaultGeoLevelUpdateReqSerializer(data=data)
    #     if req_serializer.is_valid():
    #         if len(EmailsDisseminationQueue.objects.filter(pk=id))==0:
    #             return Response(dict(message='Default level for this country doesnot exist'), status=status.HTTP_404_NOT_FOUND)
    #         if (cap.country_admin(self.request)==False):
    #             return Response(dict(message='You donot have permission. Please contact to the admin'), status=status.HTTP_401_UNAUTHORIZED)
    #         try:
    #             with transaction.atomic():
    #                 req_serializer.update(user, id, data=data)
    #                 existing_forecast_process_level_del = req_serializer.delete_existing_forecast_process(user, data=data, country_id=country_id)
    #                 existing_forecast_level = req_serializer.save_existing_forecast_process(user, data=data, files=self.request.FILES, country_id=country_id)
    #         except Exception as e:
    #             return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST)
    #         return Response(dict(success=True, message='Default level for this country successfully updated!'), status=status.HTTP_201_CREATED)   
    #     raise CustomAPIException(req_serializer.errors)

    # def delete(self, request, id):
    #     """
    #         API for DELETE by using ID
    #     """
    #     user = self.request.user 
    #     req_serializer = DefaultGeoLevelTypeDeleteReqSerializer(data=self.request.data)
    #     if req_serializer.is_valid():
    #         if len(EmailsDisseminationQueue.objects.filter(country=country_id))==0:
    #             return Response(dict(message='Country Wise Default Level Setting doesnot exist'), status=status.HTTP_404_NOT_FOUND)
    #         if (cap.country_admin(self.request)==False):
    #             return Response(dict(message='You donot have permission. Please contact to the admin'), status=status.HTTP_401_UNAUTHORIZED)
    #         try:
    #             with transaction.atomic():
    #                 country_id = EmailsDisseminationQueue.objects.filter(country=country_id)[0].country.id
    #                 req_serializer.delete(user, country_id)
    #                 existing_forecast_process_level_del = req_serializer.delete_existing_forecast_process(user, country_id=country_id)
    #         except Exception as e:
    #             return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST)
    #         return Response(dict(success=True, message='Default level for this country successfully deleted!'), status=status.HTTP_201_CREATED)   
    #     raise CustomAPIException(req_serializer.errors)


"""
    API for AM Bulletin To Queue ADD/ INSERT
"""
class AddAMBulletinToQueueView(APIView):
    """ 
        Purpose: details of crop type drop down

        Method: POST
        Args:
                name: String

        Returns:
            JSON response containing message, status and data if applicable:
                Success:
                    status: Positive Integer 
                    results: List of JSON
                Failure:
                    message: JSON
                    status: Number
    """
    
    permission_classes = (IsAuthenticated,)
    queryset = EmailsDisseminationQueue.objects.all()
    serializer_class = DefaultGeoLevelAddReqSerializer 

    def post(self, request): 
        user = self.request.user 
        # data = self.request.data['bulletin_queue_list']
        data = self.request.data
        files = self.request.FILES
        # print("################### user: ", user) 
        # print("################### data: ", data) 
        # print("################### files: ", files) 
        # print("################### files name: ", files['am_bulletin_pdf'].name) 
        # return Response(dict(success=True, message='Hi...'), status=200)   
        req_serializer = DefaultGeoLevelAddReqSerializer(data=self.request.data)
        if req_serializer.is_valid():
            
            # if (cap.country_admin(self.request)==False):
            #     return Response(dict(message='You donot have permission. Please contact to the admin'), status=status.HTTP_401_UNAUTHORIZED)
            # if (EmailsDisseminationQueue.objects.filter(country__id=data['country'])):
            #     return Response(dict(message='Default level for this country is already exist'), status=status.HTTP_404_NOT_FOUND)
            
            # try:
                # for datum in data: 
            default_level = req_serializer.save(user, data=data, files=files) 
            # except Exception as e:
            #     return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST)
            return Response(dict(success=True, message='Successfully agromet bulletin saved in email dissemination queue!'), status=status.HTTP_201_CREATED)   
        raise CustomAPIException(req_serializer.errors)












###############################################################################
###############################################################################
### TESTING
###############################################################################
###############################################################################
"""
    API for CROP TYPE DETAILS & UPDATE & DELETE 
"""
class AMBulletinToQueueDetailsTestingView(APIView):
    """ 
        Purpose: details of crop type 

        Method: POST
        Args:
                name: String

        Returns:
            JSON response containing message, status and data if applicable:
                Success:
                    status: Positive Integer 
                    results: List of JSON
                Failure:
                    message: JSON
                    status: Number
    """
    
    permission_classes = (IsAuthenticated,)
    queryset = EmailsDisseminationQueue.objects.all()
    serializer_class = CropResponseSerializer 

    def get(self, request, id):
        """
            API for DETAILS by using ID
        """
        from app_dissemination.healper_files.email_task_queqe_dissimination import (
            CountryWiseBulletinFormatSend
        )




        user = self.request.user 
        # try:
        email_id = id
        print(" $$$$$$$$$$$$$$$$$$ Email sent successfully $$$$$$$$$$$$$$$$$$$$ ") 
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
        return Response(dict(msg="successful"), status=status.HTTP_200_OK)  
        # raise CustomAPIException(req_serializer.errors)