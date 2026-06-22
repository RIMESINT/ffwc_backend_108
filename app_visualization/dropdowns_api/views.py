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

#  import models
from app_visualization.models import (
    SourceDataType,
    Source, Parameter,
    SystemState, BasinDetails,
)

# import serializers
from app_visualization.dropdowns_api.serializers import (
    SourceDatatypeDDReqSerializer, SourceDatatypeDDResponseSerializer,
    SourceDDReqSerializer, SourceDDResponseSerializer,
    SystemStateDDReqSerializer, SystemStateDDResponseSerializer,  
    ParametersDDReqSerializer, ParametersDDResponseSerializer,
    BasinsDDReqSerializer, BasinsDDResponseSerializer,
)

# import mixins
# from mixins.pagination_mixins.pagination import PaginationSetup, StandardResultsSetPagination
# from mixins.exception_mixins.exceptions import CustomAPIException










"""
    API's for sources
"""
@method_decorator(csrf_exempt, name='dispatch') 
class SourceDataTypeViewSet(viewsets.ViewSet):  
    permission_classes = (IsAuthenticated,)

    def source_data_type_list_dd(self, request):
        """ 
            Purpose: list of sources drop down

            Method: GET
            Args:
                None

            Returns:
                JSON response containing message, status and data if applicable:
                    Success:
                        status: Positive Integer 
                        results: List of JSON
                    Failure:
                        message: JSON
                        status: Number
        """
        
        req_serializer = SourceDatatypeDDReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():  
            try:
                queryset = SourceDataType.objects.all().order_by('name')
                res_serializer = SourceDatatypeDDResponseSerializer(queryset, many=True) 
                return Response(res_serializer.data, status=status.HTTP_200_OK) 
            except Exception as e:
                return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST) 
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 
        # raise CustomAPIException(req_serializer.errors) 
        # return Response(dict(e), status=status.HTTP_200_OK) 


"""
    API's for sources
"""
@method_decorator(csrf_exempt, name='dispatch') 
class SourceViewSet(viewsets.ViewSet):  
    permission_classes = (IsAuthenticated,)

    def source_list_dd(self, request):
        """ 
            Purpose: list of sources drop down

            Method: GET
            Args:
                None

            Returns:
                JSON response containing message, status and data if applicable:
                    Success:
                        status: Positive Integer 
                        results: List of JSON
                    Failure:
                        message: JSON
                        status: Number
        """
        
        req_serializer = SourceDDReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():  
            try:
                queryset = Source.objects.filter( 
                    source_type=req_serializer.data['source_type'],
                    source_data_type=req_serializer.data['source_data_type']
                ).order_by('name')
                res_serializer = SourceDDResponseSerializer(queryset, many=True) 
                return Response(res_serializer.data, status=status.HTTP_200_OK) 
            except Exception as e:
                return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST) 
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 
        # raise CustomAPIException(req_serializer.errors) 
        # return Response(dict(e), status=status.HTTP_200_OK) 







"""
    API's for sources
"""
@method_decorator(csrf_exempt, name='dispatch') 
class SystemStateViewSet(viewsets.ViewSet):  
    permission_classes = (IsAuthenticated,)

    def system_state_list_dd(self, request):
        """ 
            Purpose: list of sources drop down

            Method: GET
            Args:
                None

            Returns:
                JSON response containing message, status and data if applicable:
                    Success:
                        status: Positive Integer 
                        results: List of JSON
                    Failure:
                        message: JSON
                        status: Numbers 
        """
        
        req_serializer = SystemStateDDReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid(): 
            # print("*****####### : ", req_serializer.data['source'])
            queryset = SystemState.objects.filter(
                source__id=req_serializer.data['source'], 
            ).order_by('name')
            # print("queryset: ", queryset)
            res_serializer = SystemStateDDResponseSerializer(queryset, many=True) 
            return Response(res_serializer.data[0], status=status.HTTP_200_OK)  
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST)
        # raise CustomAPIException(req_serializer.errors) 
    



"""
    API's for parameters
"""
@method_decorator(csrf_exempt, name='dispatch') 
class ParametersDDViewSet(viewsets.ViewSet):  
    permission_classes = (IsAuthenticated,)

    def param_list_dd(self, request):
        """ 
            Purpose: list of sources drop down

            Method: GET
            Args:
                None

            Returns:
                JSON response containing message, status and data if applicable:
                    Success:
                        status: Positive Integer 
                        results: List of JSON
                    Failure:
                        message: JSON
                        status: Numbers 
        """
        
        req_serializer = ParametersDDReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid(): 
            # print("*****####### : ", req_serializer.data['source'])
            queryset = Parameter.objects.all().order_by('name')
            # print("queryset: ", queryset)
            res_serializer = ParametersDDResponseSerializer(queryset, many=True) 
            return Response(res_serializer.data, status=status.HTTP_200_OK)  
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST)
        # raise CustomAPIException(req_serializer.errors) 



"""
    API's for parameters
"""
@method_decorator(csrf_exempt, name='dispatch') 
class BasinListDDViewSet(viewsets.ViewSet):  
    permission_classes = (IsAuthenticated,)

    def basin_list_dd(self, request):
        """ 
            Purpose: list of sources drop down

            Method: GET
            Args:
                None

            Returns:
                JSON response containing message, status and data if applicable:
                    Success:
                        status: Positive Integer 
                        results: List of JSON
                    Failure:
                        message: JSON
                        status: Numbers 
        """
        
        req_serializer = BasinsDDReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid(): 
            # print("*****####### : ", req_serializer.data['source'])
            queryset = BasinDetails.objects.all().order_by('name')
            # print("queryset: ", queryset)
            res_serializer = BasinsDDResponseSerializer(queryset, many=True) 
            return Response(res_serializer.data, status=status.HTTP_200_OK)  
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST)
        # raise CustomAPIException(req_serializer.errors) 





