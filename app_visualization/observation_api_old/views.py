import pandas as pd

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
    Source, Parameter,
    SystemState, BasinDetails,
    FfwcRainfallStation, RainfallObservation,
)

# import serializers
from app_visualization.observation_api.serializers import (
    SourceDDReqSerializer, SourceDDResponseSerializer,
    RFObsReqSerializer, RFObsDetailsResSerializer,

)

# import mixins
# from mixins.pagination_mixins.pagination import PaginationSetup, StandardResultsSetPagination
# from mixins.exception_mixins.exceptions import CustomAPIException










"""
    API's for sources
"""
@method_decorator(csrf_exempt, name='dispatch') 
class StationListViewSet(viewsets.ViewSet):  
    # permission_classes = (IsAuthenticated,)
    

    def station_list_dd(self, request):
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
                queryset = FfwcRainfallStation.objects.select_related(
                    'observe_data_source'
                ).filter( 
                    observe_data_source=req_serializer.data['observe_data_source'],
                ).order_by('name')
                res_serializer = SourceDDResponseSerializer(queryset, many=True) 
                return Response(res_serializer.data, status=status.HTTP_200_OK) 
            except Exception as e:
                return Response(dict(message=str(e.args[0])), status=status.HTTP_400_BAD_REQUEST) 
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 
        # raise CustomAPIException(req_serializer.errors) 
        # return Response(dict(e), status=status.HTTP_200_OK) 




"""
    API for CROP STAGE DETAILS & UPDATE & DELETE 
"""
class RFObservationDetailsView(APIView):
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
    queryset = RainfallObservation.objects.all()
    serializer_class = RFObsDetailsResSerializer 

    
    def get(self, request, id):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        req_data = self.request.GET.dict()
        print("req_data: ", req_data)

        req_serializer = RFObsReqSerializer(data=req_data)
        if req_serializer.is_valid():
            if len(RainfallObservation.objects.filter(st__id=id))==0:
                return Response(dict(message='Observation data doesnot exist'), status=status.HTTP_404_NOT_FOUND)
            queryset = RainfallObservation.objects.filter(st__id=id) 

            data = list(queryset.values())
            df = pd.DataFrame(data)

            # df['rf_date'] = pd.to_datetime(df['rf_date'])
            df['date'] = df['rf_date'].dt.date
            df = df.sort_values(
                by=['date', 'rf_date'], ascending=[False, True], 
                # inplace=True
            )

            df = df.drop_duplicates(subset=['date', 'rf_date'])
            df.reset_index(drop=True, inplace=True)
            
            last_row_each_day = df.groupby('date').tail(1)
            last_row_each_day.reset_index(drop=True, inplace=True)
            # print(last_row_each_day)
            df = last_row_each_day.head(int(req_data["day"]))
            print(df)
            
            total_rainfall = df['rainFall'].sum()
            print("Total Rainfall:", total_rainfall)

            rf_id_list = df['rf_id'].tolist()
            # print(rf_id_list)

            queryset = RainfallObservation.objects.filter(
                rf_id__in=rf_id_list
            ).order_by('-rf_date') 

            # df_data = last_row_each_day.to_dict(orient='records')

            res_serializer = RFObsDetailsResSerializer(queryset, many=True)  
            
            # return Response(dict(msg=f"Im id: {id}"), status=status.HTTP_200_OK) 
            return Response(res_serializer.data, status=status.HTTP_200_OK)
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 













