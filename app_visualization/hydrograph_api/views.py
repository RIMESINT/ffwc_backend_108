import os

import pandas as pd

from datetime import date as py_date_obj, datetime as dt


from rest_framework import status 
from rest_framework.response import Response 
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework import generics
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.conf import settings

#  import models
# from app_visualization.models import (
#     Source, Parameter,
#     SystemState, BasinDetails,
#     StreamFlowStation, RainfallObservation,
#     StreamFlowStation, 
# )

# import serializers
from app_visualization.hydrograph_api.serializers import (
    FfwcHydrographV1ReqSerializer, FfwcHydrographV1ResSerializer, 
)

# import middleware
from app_middlewares.permissions.dir_with_sub_dir_permissions import (
    DirectoryPermission
)

# import mixins
# from mixins.pagination_mixins.pagination import PaginationSetup, StandardResultsSetPagination
# from mixins.exception_mixins.exceptions import CustomAPIException
FFWC_SF_BASE_URL = settings.BASE_DIR










"""
    API for CROP STAGE DETAILS & UPDATE & DELETE 
"""
class FfwcHydrographVisView(APIView):
    """ 
        Purpose: details of pest 

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
    # queryset = StreamFlowStation.objects.all()
    serializer_class = FfwcHydrographV1ResSerializer 

    
    # def get(self, request, place_name, date):
    def get(self, request):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        req_data = self.request.GET.dict()
        # print("user: ", user)
        print("req_data: ", req_data)

        req_serializer = FfwcHydrographV1ReqSerializer(data=req_data)
        if req_serializer.is_valid():
            
            HYDROGRAPH_DIR = "/assets/assets/hydrograph/"
            DATE_FOLDER = "output_"+str(req_data['date'])+"/"
            
            FILE_NAME = str(req_data['place_name'])+".png"
            # FILE_NAME = str(req_data['place_name'])+"_"+str(req_data['date'])+".jpeg"
            
            HYDROGRAPH_FILE = str(FFWC_SF_BASE_URL) + HYDROGRAPH_DIR + DATE_FOLDER + FILE_NAME
            print("HYDROGRAPH_FILE: ", HYDROGRAPH_FILE)
            
            # change directory permission as chmod 777
            DirectoryPermission.directory_all_files_and_folder_permissions(
                directory_path=(str(FFWC_SF_BASE_URL) + HYDROGRAPH_DIR),
                permission_mode=0o777
            )
            
            file_names = os.listdir((str(FFWC_SF_BASE_URL) + HYDROGRAPH_DIR))
            # print("Files in the directory:", file_names) 
            
            if os.path.isfile(HYDROGRAPH_FILE):
                # If the file exists, read the file
                # with open(HYDROGRAPH_FILE, 'rb') as file:
                #     file_content = file.read()
                #     print(f"File '{file_name}' has been read successfully.")
                return Response(
                    dict(hydrograph_path=str(HYDROGRAPH_DIR + DATE_FOLDER + FILE_NAME)), 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    dict(error="File does not exist"), 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # return Response(dict(msg=f"place_name: {req_data['place_name']}"), status=status.HTTP_200_OK) 
            # return Response(res_serializer.data, status=status.HTTP_200_OK)
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 





"""
    API for CROP STAGE DETAILS & UPDATE & DELETE 
"""
class FfwcHydrographVisViewV2(APIView):
    """ 
        Purpose: details of pest 

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
    # queryset = StreamFlowStation.objects.all()
    serializer_class = FfwcHydrographV1ResSerializer 

    
    # def get(self, request, place_name, date):
    def get(self, request):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        req_data = self.request.GET.dict()
        # print("user: ", user)
        # print("req_data: ", req_data)

        req_serializer = FfwcHydrographV1ReqSerializer(data=req_data)
        if req_serializer.is_valid():
            
            HYDROGRAPH_DIR = "/assets/assets/hydrograph/"
            DATE_FOLDER = "output_"+str(req_data['date'])+"/"
            if len(req_data['place_name'].strip('[]'))>0:
                FILE_NAME_LIST = req_data['place_name'].strip('[]').split(',')
            else:
                FILE_NAME_LIST = []
            # print("FILE_NAME_LIST: ", FILE_NAME_LIST)
            
            FILE_NAME = []
            for fn in FILE_NAME_LIST:
                FILE_NAME.append(str(fn)+".png")
            # FILE_NAME = str(req_data['place_name'])+".png"
            # FILE_NAME = str(req_data['place_name'])+"_"+str(req_data['date'])+".jpeg"
            # print("FILE_NAME: ", FILE_NAME)
            # print("FILE_NAME: ", type(FILE_NAME))
            
            HYDROGRAPH_FILE = []
            for fn in FILE_NAME:
                HYDROGRAPH_FILE.append(str(FFWC_SF_BASE_URL) + HYDROGRAPH_DIR + DATE_FOLDER + fn) 
                # HYDROGRAPH_FILE.append(fn) 
            # print("HYDROGRAPH_FILE: ", HYDROGRAPH_FILE)
            
            # change directory permission as chmod 777
            DirectoryPermission.directory_all_files_and_folder_permissions(
                directory_path=(str(FFWC_SF_BASE_URL) + HYDROGRAPH_DIR),
                permission_mode=0o777
            )
            
            # file_names = os.listdir((str(FFWC_SF_BASE_URL) + HYDROGRAPH_DIR))
            # print("Files in the directory:", file_names) 
            
            if len(HYDROGRAPH_FILE) > 0:
                output_list = []
                for hfp in range(len(HYDROGRAPH_FILE)):
                    if os.path.isfile(HYDROGRAPH_FILE[hfp]):
                        # If the file exists, read the file
                        # with open(HYDROGRAPH_FILE, 'rb') as file:
                        #     file_content = file.read()
                        #     print(f"File '{file_name}' has been read successfully.")
                        output_list.append(str(HYDROGRAPH_DIR + DATE_FOLDER + FILE_NAME[hfp]))
                    
                return Response(
                    dict(hydrograph_path=output_list), 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    dict(error="File does not exist"), 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # return Response(dict(msg=f"place_name: {req_data['place_name']}"), status=status.HTTP_200_OK) 
            # return Response(res_serializer.data, status=status.HTTP_200_OK)
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST)







