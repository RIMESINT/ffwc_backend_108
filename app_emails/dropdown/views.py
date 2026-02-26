from rest_framework import status 
from rest_framework.views import APIView
from rest_framework.response import Response 
from rest_framework import viewsets
# from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework import generics
from rest_framework.exceptions import APIException

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# import serializer
from app_emails.dropdown.serializers import (
    CropTypeResponseSerializer, CropTypeCustomRequestSerializer,                             
)

# import models
from app_emails.models import (
    MailingList
)

# import mixins
# from mixins.pagination_mixins.pagination import PaginationSetup, StandardResultsSetPagination   #, PaginationSetup.custom_standard_pagination
# from mixins.pagination_mixins.pagination.PaginationSetup import PaginationSetup.custom_standard_pagination
from mixins.exception_mixins.exceptions import CustomAPIException
# for permission mixins
# from mixins.user_permissions.permissions import CustomUserPermission as cap 

#  import project constant
# from ffwc_django_project.project_constant import PAGINATION_CONSTANT, SESAME_USERS









"""
    ##################################################
    ### Email Group List DROPDOWN
    ##################################################
"""  
@method_decorator(csrf_exempt, name='dispatch') 
class EmailGroupListDropdownViewSet(viewsets.ViewSet): 
    
    permission_classes = (IsAuthenticated,)

    def list_drop_down(self, request):
        """ 
            Purpose: list of email group drop down

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
        
        
        
        req_serializer = CropTypeCustomRequestSerializer(data=self.request.GET.dict())
        if req_serializer.is_valid():  
            queryset = MailingList.objects.all().order_by('id')
            res_serializer = CropTypeResponseSerializer(queryset, many=True) 
            return Response(res_serializer.data, status=status.HTTP_200_OK)  
        raise CustomAPIException(req_serializer.errors) 




