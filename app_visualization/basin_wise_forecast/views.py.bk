import ast
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import datetime as dt
from django.db.models import Max

# Django decorators for CSRF and Class-based views
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status 
from rest_framework.response import Response 
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework import generics
from rest_framework.exceptions import APIException

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
        API for various forecast:
        1. Dynamically identifies the most recent forecast run per source.
        2. Limits output to exactly 10 days to prevent chart label errors.
        3. Excludes basins named '_not_working'.
    """  
    permission_classes = (IsAuthenticated,)

    def level_wise_forecast_date_wise_all_loc(self, request):
        data = {}

        requested_data = self.request.GET.dict()
        req_serializer = ForcastStateDDReqSerializer(data=requested_data)
        
        if req_serializer.is_valid():

            parameter = request.GET.getlist('parameter') 
            source = request.GET.get('source', None) 
            # We keep this for fallback, but the logic now prioritizes the latest DB entry
            input_forecast_date = request.GET.get('forecast_date', None)
            basin_details = request.GET.get('basin_details', '[]')
            
            try:
                basin_details_list = ast.literal_eval(basin_details)
            except:
                basin_details_list = []

            # 1. Source Validation
            if source == None: 
                return JsonResponse({'error': 'no source defined'})
            
            source_qs = Source.objects.filter(id=source)
            if source_qs.count() != 1:
                return JsonResponse({'error': 'invalid source'})
            
            source_obj = source_qs[0]

            # 2. Most Recent Date Logic (Works for all sources)
            latest_available_date = ForecastDaily.objects.filter(
                source__id=source
            ).aggregate(Max('forecast_date'))['forecast_date__max']

            if latest_available_date:
                forecast_date = latest_available_date
            else:
                # If the table is empty for this source, try to use the provided date
                try:
                    forecast_date = dt.strptime(input_forecast_date, '%Y%m%d').date()
                except:
                    return JsonResponse({'error': 'no data exists for source and invalid date format provided'})

            # 3. 10-Day Limit Definition
            # This prevents the 'useless' dates at the end of the chart
            end_date_limit = forecast_date + timedelta(days=10)

            # 4. Basin Selection (Excluding basins with '_not_working' in the name)
            if len(basin_details_list) == 0:
                basin_name_list = BasinDetails.objects.all().exclude(
                    name__icontains='_not_working'
                ).order_by('name')
            else: 
                basin_name_list = BasinDetails.objects.filter(
                    id__in=basin_details_list
                ).exclude(
                    name__icontains='_not_working'
                ).order_by('name')
        
            # 5. Parameter Selection
            if len(parameter) == 0:
                sel_param = Parameter.objects.all().values('id', 'name', 'full_name', 'unit')
            else:
                sel_param = Parameter.objects.filter(id__in=parameter).values('id', 'name', 'full_name', 'unit')

            # 6. Response Construction
            data['error'] = None
            data['source'] = source_obj.name 
            data['data'] = {}

            all_upz_list_forcast = []
            for upz in basin_name_list:
                upz_data = {
                    'id': upz.id,
                    'name': upz.name,
                    'forecast_data': {}
                }

                for param in sel_param:
                    # Filter data strictly to the identified latest date and the 10-day window
                    param_details_data = ForecastDaily.objects.filter( 
                        source__id=source,
                        parameter__id=param['id'],
                        basin_details__id=upz.id,
                        forecast_date=forecast_date,
                        step_start__gte=forecast_date,
                        step_start__lt=end_date_limit
                    ).values('id', 'step_start', 'step_end', 'val_min', 'val_avg', 'val_max').order_by('step_start')

                    # Final slice to ensure only 10 points are returned
                    upz_data['forecast_data'][param['name']] = list(param_details_data)[:10]
                
                all_upz_list_forcast.append(upz_data)
            
            data['data'] = all_upz_list_forcast

            return JsonResponse(data, safe=True, json_dumps_params={'indent': 4})

        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST)