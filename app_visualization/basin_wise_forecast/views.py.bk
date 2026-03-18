import ast

from datetime import datetime

from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.shortcuts import render

from datetime import datetime as dt

from rest_framework import status 
from rest_framework.response import Response 
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework import generics
from rest_framework.exceptions import APIException

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


from app_visualization.models import (
    Parameter, Source, BasinDetails,
    ForecastDaily, ForecastSteps, SystemState
)

from app_visualization.basin_wise_forecast.serializers import (
    ForcastStateDDReqSerializer
) 








@method_decorator(csrf_exempt, name='dispatch') 
class BasinWiseForcastingViewSet(viewsets.ViewSet):
    """
        API for various forecast 
    """  
    permission_classes = (IsAuthenticated,)


    def level_wise_forecast_date_wise_all_loc(self, request):
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

        data = {}

        requested_data = self.request.GET.dict()
        req_serializer = ForcastStateDDReqSerializer(data=requested_data)
        if req_serializer.is_valid():

            parameter = request.GET.getlist('parameter') 
            source = request.GET.get('source', None) 
            forecast_date   = request.GET.get('forecast_date', None)
            basin_details = request.GET.get('basin_details')
            basin_details_list = ast.literal_eval(basin_details)
            print("basin_details: ", basin_details)
            print("basin_details type: ", type(basin_details))
            print("basin_details_list: ", basin_details_list)
            print("basin_details_list type: ", type(basin_details_list)) 


            if source==None: 
                return JsonResponse({'error':'no source defined'})
            elif Source.objects.filter(id=source).count()!=1:
                return JsonResponse({'error':'invalid source'})
            
            source_obj = Source.objects.filter(pk=source)[0]
                        

            if forecast_date==None:
                return JsonResponse({'error':'FDATE not defined'})
            else:
                try:
                    forecast_date = dt.strptime(forecast_date,'%Y%m%d').strftime('%Y-%m-%d')
                    # print("type of forecast_date: ", (forecast_date))
                    # print("type of forecast_date: ", type(forecast_date))
                except:
                    return JsonResponse({'error':'invalid date format. provide YYYYMMDD format'})

            
            if len(basin_details_list) == 0:
                basin_name_list = BasinDetails.objects.all().order_by('name')#.values('id','name','parent','level','unique_key')
                # print("type of basin_name_list: ", (basin_name_list))
            elif len(basin_details_list) > 0: 
                basin_name_list = BasinDetails.objects.filter(id__in=basin_details_list).order_by('name')
        

            if len(parameter)==0: # all parameters

                sel_param = Parameter.objects.all().values('id','name','full_name','unit')
            else:
                sel_param = Parameter.objects.filter(id__in=parameter).values('id','name','full_name','unit')


            data['error']       = None
            data['source']      = source_obj.name 
            data['data']        = {}

            all_upz_list_forcast = []
            for upz in basin_name_list:

                upz_data = {}

                upz_data['id'] = upz.id 
                upz_data['name'] = upz.name 
                # upz_data['name'] = upz['name']
                upz_data['forecast_data'] = {}

                for param in sel_param:

                    param_data={}

                    param_details_data = ForecastDaily.objects.filter( 
                        source__id=source,
                        parameter__id=param['id'],
                        # location__id=upz['id'],
                        basin_details__id=upz.id,
                        forecast_date=forecast_date    #datetime.strptime(forecast_date, '%m/%d/%y %H:%M:%S')     #forecast_date
                        ).values('id', 'step_start', 'step_end', 'val_min', 'val_avg', 'val_max').order_by('step_start')

                    # param_data[param['name']] = list(param_details_data)
                    # print(" param_details_data: ", type(param_details_data))

                    upz_data['forecast_data'][param['name']]=list(param_details_data)
                
                all_upz_list_forcast.append(upz_data)
                # data['data']=upz_data
            data['data']=all_upz_list_forcast

            # return JsonResponse(data, safe=True, json_dumpsparameter={'indent': 4})
            return JsonResponse(data, safe=True, json_dumps_params={'indent': 4})
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST)