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

from datetime import datetime as dt

# import serializer
from app_bulletin.agromet_bulletin.serializers import ( 
    AMBulletinLVReqSerializer, AMBulletinLVResponseSerializer, 
    AMBulletinMapPathReqSerializer,
    AMBulletinDetailsDateReqSerializer,
    AMBulletinDetailsReqSerializer, AMBulletinDetailsResSerializer,
    AMBulletinAddReqSerializer, 
    AMBulletinUpdateReqSerializer,  
    AMBulletinDeleteReqSerializer,    

    AMBulletinUpdate2ReqSerializer,              
)

# import models
from app_bulletin.models import (
    AgrometBulletin, AgrometBulletinSourceDestinationDetails
) 

# import mixins
from mixins.pagination_mixins.pagination import PaginationSetup, StandardResultsSetPagination   
# from mixins.exception_mixins.exceptions import CustomAPIException
# for permission mixins
# from mixins.user_permissions.permissions import CustomUserPermission as cap 

#  import project constant
from ffwc_django_project.project_constant import PAGINATION_CONSTANT

from ffwc_django_project.settings import BASE_DIR, MEDIA_URL









# Create your views here. 
"""
    ##################################################
    ### Pest Fav Con Configuration VIEWS
    ##################################################
""" 
class AMBulletinListView(generics.ListAPIView):
    """ 
        Purpose: list of pest types

        Method: GET
        Args: 
                crop_stage_id: Positive Integer 

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
    
    # permission_classes = (IsAuthenticated,)
    queryset = AgrometBulletin.objects.all()
    serializer_class = AMBulletinLVResponseSerializer
    pagination_class =  StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user 
        req_serializer = AMBulletinLVReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():  
            if 'page_size' in self.request.GET:
                self.pagination_class = PaginationSetup.custom_standard_pagination(page_size=self.request.GET['page_size'])
            return AgrometBulletin.objects.all().order_by('-forecast_date')  
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 


"""
    API for CROP STAGE DETAILS & UPDATE & DELETE 
"""
class AMBulletinMapPathDateWiseView(APIView):
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
    queryset = AgrometBulletin.objects.all()
    serializer_class = AMBulletinDetailsResSerializer 

    def get(self, request):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        data = self.request.GET.dict()
        # print("*********** data", data)
        req_serializer = AMBulletinMapPathReqSerializer(data=data)
        if req_serializer.is_valid():
            
            response = {}
            # print("response: ", response)

            fcst_date = dt.strptime(data['forecast_date'],'%Y-%m-%d')
            path_dt = fcst_date.strftime("%d%m%Y")
            # print("path_dt: ", path_dt)

            if len(AgrometBulletinSourceDestinationDetails.objects.filter(country=data['country']))>0:
                path_obj = AgrometBulletinSourceDestinationDetails.objects.filter(country=data['country'])[0]
                plot_base_path = str(MEDIA_URL)+str(path_obj.destination_path)+path_dt+'/'+str(path_obj.country.unique_value)+"/"
                plot_path = {
                    "accum_rf_1st_7d": plot_base_path+"accum_rf_1st_7d.png",
                    "max_temp_1st_7d": plot_base_path+"max_temp_1st_7d.png",
                    "min_temp_1st_7d": plot_base_path+"min_temp_1st_7d.png"
                }
                # print("plot_path: ", (plot_path))
                response["plot_path"] = plot_path
            else:
                return Response(dict(message="Plot is not availabe for this country"), status=status.HTTP_404_NOT_FOUND)

            return Response(response, status=status.HTTP_200_OK) 
        raise CustomAPIException(req_serializer.errors)



"""
    API for CROP STAGE DETAILS & UPDATE & DELETE 
"""
class AMBulletinDetailsDateWiseView(APIView):
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
    queryset = AgrometBulletin.objects.all()
    serializer_class = AMBulletinDetailsResSerializer 

    def get(self, request):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        data = self.request.GET.dict()
        # print("*********** data", data)
        req_serializer = AMBulletinDetailsDateReqSerializer(data=data)
        if req_serializer.is_valid():
            if len(AgrometBulletin.objects.filter(forecast_date=data['forecast_date'], country=data['country']))==0:
                return Response(dict(message='Agromet bulletin details doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            queryset = AgrometBulletin.objects.filter(
                forecast_date=data['forecast_date'], 
                country=data['country']
            ).order_by('-updated_by') 
            res_serializer = AMBulletinDetailsResSerializer(queryset, many=True)  

            response = dict(**res_serializer.data[0])
            # print("response: ", response)

            fcst_date = dt.strptime(data['forecast_date'],'%Y-%m-%d')
            path_dt = fcst_date.strftime("%d%m%Y")
            # print("path_dt: ", path_dt)

            if len(AgrometBulletinSourceDestinationDetails.objects.filter(country=data['country']))>0:
                path_obj = AgrometBulletinSourceDestinationDetails.objects.filter(country=data['country'])[0]
                plot_base_path = str(MEDIA_URL)+str(path_obj.destination_path)+path_dt+'/'+str(path_obj.country.unique_value)+"/"
                plot_path = {
                    "accum_rf_1st_7d": plot_base_path+"accum_rf_1st_7d.png",
                    "max_temp_1st_7d": plot_base_path+"max_temp_1st_7d.png",
                    "min_temp_1st_7d": plot_base_path+"min_temp_1st_7d.png"
                }
                # print("plot_path: ", (plot_path))
                response["plot_path"] = plot_path

            return Response(response, status=status.HTTP_200_OK) 
        raise CustomAPIException(req_serializer.errors)

"""
    API for CROP STAGE DETAILS & UPDATE & DELETE 
"""
class AMBulletinDetailsView(APIView):
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
    
    # permission_classes = (IsAuthenticated,)
    queryset = AgrometBulletin.objects.all()
    serializer_class = AMBulletinDetailsResSerializer 

    
    def get(self, request, id):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        req_serializer = AMBulletinDetailsReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():
            if len(AgrometBulletin.objects.filter(id=id))==0:
                return Response(dict(message='Agromet bulletin details doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            queryset = AgrometBulletin.objects.filter(pk=id) 
            res_serializer = AMBulletinDetailsResSerializer(queryset, many=True)  

            response = dict(**res_serializer.data[0])
            # print("response: ", response)

            # fcst_date = dt.strptime(data['forecast_date'],'%Y-%m-%d')
            # bulletin_country = queryset[0].country
            # fcst_date = queryset[0].forecast_date
            # path_dt = fcst_date.strftime("%d%m%Y")
            # print("path_dt: ", path_dt)

            # if len(AgrometBulletinSourceDestinationDetails.objects.filter(country=bulletin_country))>0:
            # path_obj = AgrometBulletinSourceDestinationDetails.objects.filter(country=bulletin_country)[0]
            # plot_base_path = str(MEDIA_URL)+str(path_obj.destination_path)+path_dt+'/'+str(path_obj.country.unique_value)+"/"
            plot_path = {
                "accum_rf_1st_7d": None,    #plot_base_path+"accum_rf_1st_7d.png",
                "max_temp_1st_7d": None,    #plot_base_path+"max_temp_1st_7d.png",
                "min_temp_1st_7d": None,    #plot_base_path+"min_temp_1st_7d.png"
            }
            # print("plot_path: ", (plot_path))
            response["plot_path"] = plot_path

            return Response(response, status=status.HTTP_200_OK) 
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 

    def put(self, request, id):
        """
            API for UPDATE by using ID
        """
        user = self.request.user 
        # print("data: ", self.request.data)
        req_serializer = AMBulletinUpdateReqSerializer(data=self.request.data)
        if req_serializer.is_valid():
            if len(AgrometBulletin.objects.filter(id=id))==0:
                return Response(dict(message='Agromet bulletin details doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            # if (cap.country_admin(self.request)==False):
            #     return Response(dict(message='You donot have permission. Please contact to the admin'), status=status.HTTP_401_UNAUTHORIZED)
            try:
                req_serializer.update(user, id, data=self.request.data, files=self.request.FILES)
            except Exception as e:
                return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST)
            return Response(dict(success=True, message='Successfully Agromet bulletin details updated!'), status=status.HTTP_201_CREATED)   
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 

    def delete(self, request, id):
        """
            API for DELETE by using ID
        """
        user = self.request.user 
        req_serializer = AMBulletinDeleteReqSerializer(data=self.request.data)
        if req_serializer.is_valid():
            if len(AgrometBulletin.objects.filter(id=id))==0:
                return Response(dict(message='Agromet bulletin details doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            # if (cap.country_admin(self.request)==False):
            #     return Response(dict(message='You donot have permission. Please contact to the admin'), status=status.HTTP_401_UNAUTHORIZED)
            req_serializer.delete(user, id)
            return Response(dict(success=True, message='Successfully Agromet bulletin details deleted!'), status=status.HTTP_201_CREATED)   
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 



"""
    API for CROP STAGE ADD/INSERT
"""
class AddAMBulletinView(APIView):
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
    
    # permission_classes = (IsAuthenticated,)
    queryset = AgrometBulletin.objects.all()
    serializer_class = AMBulletinAddReqSerializer 

    def post(self, request): 
        user = self.request.user 
        print("data: ", self.request.data)
        # print("data type: ", type(self.request.data))
        
        req_serializer = AMBulletinAddReqSerializer(data=self.request.data)
        if req_serializer.is_valid(): 
            
            # try:
            req_serializer.save(user, data=self.request.data) 
            # except Exception as e:
            #     return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST) 
            return Response(dict(success=True, message='Successfully agromet bulletin details saved!'), status=status.HTTP_201_CREATED)   
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 


"""
    API for CROP STAGE DETAILS & UPDATE & DELETE 
"""
class AMBulletinUpdateView(APIView):
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
    
    # permission_classes = (IsAuthenticated,)
    queryset = AgrometBulletin.objects.all()
    serializer_class = AMBulletinUpdate2ReqSerializer  

    def put(self, request, id):
        """
            API for UPDATE by using ID
        """
        user = self.request.user 
        # print("data: ", self.request.data)
        req_serializer = AMBulletinUpdate2ReqSerializer(data=self.request.data)
        if req_serializer.is_valid():
            if len(AgrometBulletin.objects.filter(id=id))==0:
                return Response(dict(message='Agromet bulletin details doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            # if (cap.country_admin(self.request)==False):
            #     return Response(dict(message='You donot have permission. Please contact to the admin'), status=status.HTTP_401_UNAUTHORIZED)
            try:
                req_serializer.update(user, id, data=self.request.data, files=self.request.FILES)
            except Exception as e:
                return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST)
            return Response(dict(success=True, message='Successfully Agromet bulletin details updated!'), status=status.HTTP_201_CREATED)   
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 


 




