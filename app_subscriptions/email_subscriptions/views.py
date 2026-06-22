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

# import serializer
from app_subscriptions.email_subscriptions.serializers import ( 
    DiseaseLVReqSerializer, DiseaseLVResponseSerializer, 
    DiseaseDetailsReqSerializer, DiseaseDetailsResSerializer,
    DiseaseAddReqSerializer, 
    DiseaseUpdateReqSerializer, DiseaseDeleteReqSerializer,                  
)

# import models
from app_subscriptions.models import (
    EmailsSubscription
)

# import mixins
from mixins.pagination_mixins.pagination import (
    PaginationSetup, StandardResultsSetPagination
)   
from mixins.exception_mixins.exceptions import CustomAPIException











# Create your views here. 
"""
    ##################################################
    ### CROP Stage Configuration VIEWS
    ##################################################
""" 
class ListEmailSubscription(generics.ListAPIView):
    """ 
        Purpose: list of disease types

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
    queryset = EmailsSubscription.objects.all()
    serializer_class = DiseaseLVResponseSerializer
    pagination_class =  StandardResultsSetPagination

    def get_queryset(self):
        data = self.request.GET.dict()
        user = self.request.user 
        # print(" $$$$$$ data: ", data)
        
        req_serializer = DiseaseLVReqSerializer(data=data)
        if req_serializer.is_valid():  
            if 'page_size' in self.request.GET:
                self.pagination_class = PaginationSetup.custom_standard_pagination(
                    page_size=int(data['page_size'])
                )
            return EmailsSubscription.objects.all().order_by('email')  
        raise CustomAPIException(req_serializer.errors)


"""
#     API for CROP STAGE DETAILS & UPDATE & DELETE 
# """
class EmailSubscriptionDetailsView(APIView):
    """ 
        Purpose: details of disease 

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
    queryset = EmailsSubscription.objects.all()
    serializer_class = DiseaseDetailsResSerializer 

    def get(self, request, id):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        # print(" ############################### ")
        req_serializer = DiseaseDetailsReqSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():
            if len(EmailsSubscription.objects.filter(id=id))==0:
                return Response(dict(message='EmailsSubscription details doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            
            queryset = EmailsSubscription.objects.filter(pk=id) 
            res_serializer = DiseaseDetailsResSerializer(queryset, many=True)  
            return Response(res_serializer.data[0], status=status.HTTP_200_OK) 
        raise CustomAPIException(req_serializer.errors)

    def put(self, request, id):
        """
            API for UPDATE by using ID
        """
        user = self.request.user 
        # print("data: ", self.request.data)
        req_serializer = DiseaseUpdateReqSerializer(data=self.request.data)
        if req_serializer.is_valid():
            if len(EmailsSubscription.objects.filter(id=id))==0:
                return Response(
                    dict(message='Subscription email doesnot exist'), 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            try:
                req_serializer.update(user, id, data=self.request.data)
            except Exception as e:
                return Response(
                    dict(message=str(e.args[0])), 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                dict(success=True, message='Successfully subscription email updated!'), 
                status=status.HTTP_201_CREATED
            )   
        raise CustomAPIException(req_serializer.errors)

    def delete(self, request, id):
        """
            API for DELETE by using ID
        """
        user = self.request.user 
        req_serializer = DiseaseDeleteReqSerializer(data=self.request.data)
        if req_serializer.is_valid():
            if len(EmailsSubscription.objects.filter(id=id))==0:
                return Response(
                    dict(message='EmailsSubscription details doesnot exist'), 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                req_serializer.delete(user, id)
            except Exception as e:
                return Response(
                    dict(message=str(e.args[0])), 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                dict(success=True, message='Successfully subscription email deleted!'), 
                status=status.HTTP_201_CREATED
            )   
        raise CustomAPIException(req_serializer.errors)



"""
    API for CROP STAGE ADD/INSERT
"""
class AddEmailSubscription(APIView):
    """ 
        Purpose: details of disease

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
    queryset = EmailsSubscription.objects.all()
    serializer_class = DiseaseAddReqSerializer 

    def post(self, request): 
        user = self.request.user 
        data = request.data 
        # print("data: ", data)
        
        req_serializer = DiseaseAddReqSerializer(data=data)
        if req_serializer.is_valid(): 
            
            if len(EmailsSubscription.objects.filter(
                email= data['email']
            ))>=1:
                return Response(
                    dict(message='This email is already subscribed ...'), 
                    status=status.HTTP_400_BAD_REQUEST
                )
            try: 
                req_serializer.save(user, data=data) 
            except Exception as e:
                return Response(
                    dict(message=str(e.args[0])), 
                    status=status.HTTP_400_BAD_REQUEST
                ) 
            return Response(
                dict(success=True, message='Successfully email saved for subscription!'), 
                status=status.HTTP_201_CREATED
            )    
        raise CustomAPIException(req_serializer.errors)











