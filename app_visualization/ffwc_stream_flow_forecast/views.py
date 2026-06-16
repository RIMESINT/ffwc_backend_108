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
from app_visualization.models import (
    Source, Parameter,
    SystemState, BasinDetails,
    StreamFlowStation, RainfallObservation,
    StreamFlowStation, 
)

# import serializers
from app_visualization.ffwc_stream_flow_forecast.serializers import (
    SourceDDReqSerializer, SourceDDResponseSerializer,
    RFObsReqSerializer, RFObsDetailsResSerializer,

)

# import mixins
# from mixins.pagination_mixins.pagination import PaginationSetup, StandardResultsSetPagination
# from mixins.exception_mixins.exceptions import CustomAPIException
FFWC_SF_BASE_URL = settings.BASE_DIR










"""
    API's for sources
"""
@method_decorator(csrf_exempt, name='dispatch') 
class FfwcSFStationListViewSet(viewsets.ViewSet):  
    permission_classes = (IsAuthenticated,)

    def sf_station_list_dd(self, request):
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
                queryset = StreamFlowStation.objects.select_related(
                    'forecast_data_source'
                ).filter( 
                    forecast_data_source=req_serializer.data['forecast_data_source'],
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
class FfwcSFForecastDailyDetailsView(APIView):
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
    queryset = StreamFlowStation.objects.all()
    serializer_class = RFObsReqSerializer 

    
    def get(self, request, id):
        """
            API for DETAILS by using ID
        """
        user = self.request.user 
        req_data = self.request.GET.dict()
        print("req_data: ", req_data)

        req_serializer = RFObsReqSerializer(data=req_data)
        if req_serializer.is_valid():

            sf_st_obj = StreamFlowStation.objects.filter(
                pk=id
            )[0]
            sf_st_file_name_not_formatted = sf_st_obj.file_name
            
            MY_SF_CSV_DIR = Source.objects.filter(
				name='FFWC_STREAM_FLOW_FORCAST', source_type="location_specific",
				source_data_type__name="Forecast"
			)[0].destination_path

            sys_state_last_update = SystemState.objects.filter(
				name='FFWC_STREAM_FLOW_FORECAST_DAILY',
				source__id=50
			)[0].last_update
            sys_state_last_update_str = sys_state_last_update.strftime('%Y%m%d')
            
            # date_obj = todate.strftime("%Y%m%d")
            csv_file_name_date_obj = dt.strptime(sys_state_last_update_str,'%Y%m%d')
            sf_st_file_name = csv_file_name_date_obj.strftime(sf_st_file_name_not_formatted)
            print(" ############ sf_st_file_name: ", sf_st_file_name)
            # return
            

            # csv_read_dir = str(FFWC_SF_BASE_URL)+str(MY_SF_CSV_DIR)+str(sys_state_last_update_str)+"/"
            csv_read_dir = str(FFWC_SF_BASE_URL)+str(MY_SF_CSV_DIR)
            print("csv_read_dir: ", csv_read_dir)

            file_path = str(csv_read_dir)+str(sf_st_file_name)

            df = pd.read_csv(file_path)
            # df['date'] = pd.to_datetime(df['Time']).dt.date
            df['datetime'] = pd.to_datetime(df['Time']) 
            df.sort_values(by=['datetime', 'Time'], ascending=[False, True], inplace=True)
            df_new = df.groupby('datetime')['Streamflow'].sum().reset_index(name='accu_stream_flow')
            df_new.sort_values(by=['datetime'], ascending=[True], inplace=True)
            
            day_to_hour = int(req_data['day'])*12
            df_final = df_new.head(day_to_hour)
            # print("###########################################")
            
            df_data = df_final.to_dict(orient='records')

            # print("df_final: ", df_final)

            res_serializer = RFObsDetailsResSerializer(df_data, many=True)  
            
            # return Response(dict(msg=f"Im id: {id}"), status=status.HTTP_200_OK) 
            return Response(res_serializer.data, status=status.HTTP_200_OK)
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST) 













