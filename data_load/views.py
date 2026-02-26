from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from django.shortcuts import get_object_or_404
import requests

from django.db.models import Subquery, OuterRef, FloatField, DateTimeField, ExpressionWrapper, F, Case, When, Value
from django.db.models.functions import Cast, Coalesce
from rest_framework import viewsets
from django.shortcuts import get_object_or_404

from rest_framework import viewsets,status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework.decorators import api_view,action
from django.views.decorators.http import require_GET

from . import models as models
from . import serializers as serializers  # Import serializers module as 'serializer'
from datetime import datetime,timedelta,time
from collections import defaultdict
from rest_framework.response import Response

from django.db.models import Max, Sum, Subquery,OuterRef,Prefetch,Q,F
from django.contrib.auth.models import User
from rest_framework import generics

from django.utils import timezone
import pytz
from . import flood_report_generator_utils
from django.db.models import Q
from rest_framework.permissions import AllowAny
from django.views import View
from django.db.models import Avg

from django.db.models import Subquery, OuterRef, F, Case, When, Value, FloatField, CharField
from django.db.models.functions import Coalesce

import pandas as pd

from django.views.decorators.http import require_http_methods

from data_load.serializers import (
    # rainfallStationSerializer, 
    # rainfallObservationSerializer, 
    # monthlyRainfallSerializer, 
    # newRainfallStationSerializer,
    
    FfwcStations2025Serializer,
    FfwcStations2025UpdateSerializer,
    FfwcStations2025BulkUpdateSerializer,
)

from data_load.models import (
    Station,
    
    # FfwcRainfallStations, 
    # RainfallObservations, 
    MonthlyRainfall,
    # FfwcRainfallStationsNew,
    # FfwcRainfallStations2025
)

import os

import logging
logger = logging.getLogger(__name__)











class UserViewSet(viewsets.ViewSet):
    def userById(self, request, **kwargs):
        user_id = int(self.kwargs['user_id'])
        try:
            queryset = User.objects.filter(id=user_id).values().first()
            if queryset:
                return Response(queryset)
            return Response({"error": "User not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    def userStatusByUser(self, request, **kwargs):
        username = unquote(self.kwargs['username'])
        try:
            queryset = User.objects.filter(username=username).values().first()
            if queryset:
                user_status = {
                    'id': queryset['id'],
                    'is_active': queryset['is_active'],
                    'is_staff': queryset['is_staff'],
                    'is_superuser': queryset['is_superuser']
                }
                return Response(user_status)
            return Response({}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)




# Define flood level categories
FLOOD_LEVELS = {
    "na": "N/A",
    "normal": "Normal",
    "warning": "Warning",
    "flood": "Flood",
    "severe": "Severe Flood"
}


@api_view(['GET'])
def about_page(request):
    return Response({"message": "This is the About page"})


class updateDateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.FfwcLastUpdateDate.objects.all()
    serializer_class = serializers.lastUpdateDateSerializer

    def list(self, request, *args, **kwargs):
        # Order the queryset by 'last_update_date' in descending order and get the first one
        most_recent_entry = self.get_queryset().order_by('-last_update_date').first()
        
        # If an entry exists, serialize it
        if most_recent_entry:
            serializer = self.get_serializer(most_recent_entry)
            return Response(serializer.data)
        else:
            # Handle the case where no entries exist
            return Response({"detail": "No update date found."}, status=404)



class FloodAlertDisclaimerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.FloodAlertDisclaimer.objects.all()
    serializer_class = serializers.FloodAlertDisclaimerSerializer

class MessagesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Messages.objects.all()
    serializer_class = serializers.MessagesSerializer

class ScrollerMessagesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ScrollerMessages.objects.all()
    serializer_class = serializers.ScrollerMessagesSerializer

class SecondScrollerMessagesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.SecondScrollerMessages.objects.all()
    serializer_class = serializers.SecondScrollerMessagesSerializer

class BasinViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Basin.objects.all()
    serializer_class = serializers.BasinSerializer

class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Unit.objects.all()
    serializer_class = serializers.UnitSerializer

############################################################################## 
##############################################################################
### Added by: SHIFULLAH
### Date: 14-SEP-2025
##############################################################################
##############################################################################

# views.py
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import StationSummaryViewMobileV1
from .serializers import StationSummaryViewMobileV1Serializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200


class StationSummaryViewMobileV1ViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API backed by the view `station_summary_view_mobile_v1`.

    Uses station_id as the lookup field (so GET /stations/123/ will try station_id=123).
    """
    queryset = StationSummaryViewMobileV1.objects.all()
    serializer_class = StationSummaryViewMobileV1Serializer
    # pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = [
        'station_id', 'station_code', 'bwdb_id', 'division', 'district',
        'station_flood_status', 'status_name', 'station_serial_no', 'status',
        'monsoon_station', 'five_days_forecast', 'ten_days_forecast'
    ]

    search_fields = ['name', 'river', 'station_code', 'bwdb_id']
    ordering_fields = ['last_observation_date', 'station_id', 'level_difference', 'highest_water_level']
    ordering = ['-last_observation_date']

    lookup_field = 'station_id'


# class StationViewV2MobileSet(viewsets.ReadOnlyModelViewSet):
#     """
#         Returns Station records annotated with:
#         - last_water_level
#         - last_observation_date
#         - previous_water_level
#         - previous_observation_date
#         - level_difference (last - previous)
#         - status_name ('rising' / 'falling' / 'steady' / '-')
#         - station_flood_status (annotated using DB Case/When)
#     """
#     lookup_field = 'station_id'
#     serializer_class = serializers.StationV2MobileSerializer

#     def get_queryset(self):
#         qs = models.Station.objects.all().order_by('station_serial_no')

#         wlo_qs = models.WaterLevelObservation.objects.filter(
#             station_id=OuterRef('station_id')
#         ).order_by('-observation_date')

#         last_level_sq = Subquery(wlo_qs.values('water_level')[:1])
#         last_date_sq = Subquery(wlo_qs.values('observation_date')[:1])

#         prev_level_sq = Subquery(wlo_qs.values('water_level')[1:2])
#         prev_date_sq = Subquery(wlo_qs.values('observation_date')[1:2])

#         # Cast numeric/date subqueries
#         last_level_cast = Cast(last_level_sq, output_field=FloatField())
#         prev_level_cast = Cast(prev_level_sq, output_field=FloatField())
#         last_date_cast = Cast(last_date_sq, output_field=DateTimeField())
#         prev_date_cast = Cast(prev_date_sq, output_field=DateTimeField())

#         annotated = qs.annotate(
#             last_water_level=last_level_cast,
#             last_observation_date=last_date_cast,
#             previous_water_level=prev_level_cast,
#             previous_observation_date=prev_date_cast,
#         ).annotate(
#             level_difference=ExpressionWrapper(
#                 F('last_water_level') - F('previous_water_level'),
#                 output_field=FloatField()
#             )
#         ).annotate(
#             # helper expressions for comparisons: danger +1 and danger -0.5
#             danger_plus_one=ExpressionWrapper(F('danger_level') + Value(1.0), output_field=FloatField()),
#             danger_minus_point5=ExpressionWrapper(F('danger_level') - Value(0.5), output_field=FloatField()),
#         ).annotate(
#             status_name=Case(
#                 When(level_difference__gt=0, then=Value('rising')),
#                 When(level_difference__lt=0, then=Value('falling')),
#                 When(level_difference=0, then=Value('steady')),
#                 When(level_difference__isnull=True, then=Value('-')),
#                 default=Value('-'),
#             ),

#             station_flood_status=Case(
#                 When(danger_level=10000, then=Value('na')),
#                 # danger_level <= 0 or null -> normal
#                 When(Q(danger_level__lte=0) | Q(danger_level__isnull=True), then=Value('normal')),
#                 # last_water_level <= 0 -> na
#                 When(last_water_level__lte=0, then=Value('na')),
#                 # severe: last >= dl + 1
#                 When(last_water_level__gte=F('danger_plus_one'), then=Value('severe')),
#                 # flood: last > dl
#                 When(last_water_level__gt=F('danger_level'), then=Value('flood')),
#                 # warning: last >= dl - 0.5
#                 When(last_water_level__gte=F('danger_minus_point5'), then=Value('warning')),
#                 # default normal
#                 default=Value('normal'),
#             )
#         )

#         return annotated

#     def get_object(self):
#         queryset = self.get_queryset()
#         lookup_value = self.kwargs.get(self.lookup_field)
#         obj = get_object_or_404(queryset, station_id=lookup_value)
#         self.check_object_permissions(self.request, obj)
#         return obj
    
class StationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Station.objects.all().order_by('station_serial_no')
    serializer_class = serializers.StationSerializer

    lookup_field = 'station_id'  # Use station_id instead of id for lookups

    def get_object(self):
        queryset = self.get_queryset()
        lookup_value = self.kwargs.get(self.lookup_field)
        obj = get_object_or_404(queryset, station_id=lookup_value)
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=['get'])
    def by_name(self, request, **kwargs):
        """
        Custom endpoint to retrieve stations by name.
        Example: /stations/by_name/Dhaka/
        """
        station_name = self.kwargs.get('station_name')
        if not station_name:
            return Response({"detail": "station_name not provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.queryset.filter(name=station_name)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)




@api_view(['GET'])
def station_by_name(request, station_name):
    # Use get_object_or_404 to return a 404 if no station is found with the given name
    station = get_object_or_404(models.Station, name=station_name)
    serializer = serializers.StationByNameSerializer(station)
    return Response(serializer.data)

class StationsViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = serializers.StationsEndpointSerializer
    queryset = models.Station.objects.all().order_by('station_id')

    def list(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.queryset, many=True)
            return JsonResponse(serializer.data, safe=False)
        except models.Station.DoesNotExist:
            return JsonResponse([], safe=False)

class RainfallStationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.RainfallStation.objects.all()
    serializer_class = serializers.RainfallStationSerializer

class ObservedWaterlevelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ObservedWaterLevelSerializer

    def list(self, request, *args, **kwargs):
        try:
            # Get the latest observation date for valid stations
            latest_entry = models.WaterLevelObservation.objects.filter(
                station_id__isnull=False
            ).latest('observation_date')
            entry_date_time = latest_entry.observation_date
        except models.WaterLevelObservation.DoesNotExist:
            return JsonResponse([], safe=False)  # Return empty list if no data exists

        # Try the latest observation date for all valid stations
        queryset = models.WaterLevelObservation.objects.filter(
            observation_date=entry_date_time,
            station_id__isnull=False
        ).order_by('station_id__station_serial_no', '-observation_date').distinct()
        # ).order_by('station_id__station_id', '-observation_date').distinct()

        # Fall back to 3 hours earlier if no data is found
        if not queryset.exists():
            previous_three_hour_date_time = entry_date_time - timedelta(hours=3)
            queryset = models.WaterLevelObservation.objects.filter(
                observation_date=previous_three_hour_date_time,
                station_id__isnull=False
            ).order_by('station_id__station_serial_no', '-observation_date').distinct()
            # ).order_by('station_id__station_id', '-observation_date').distinct()

        # If still no data, fetch last 30 days for all valid stations
        if not queryset.exists():
            queryset =models.WaterLevelObservation.objects.filter(
                observation_date__gte=entry_date_time - timedelta(days=60),
                station_id__isnull=False
            ).order_by('station_id__station_serial_no', '-observation_date').distinct()
            # ).order_by('station_id__station_id', '-observation_date').distinct()

        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)
        return JsonResponse(serializer.data, safe=False)

class ThreeDaysObservedWaterlevelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ThreeDaysObservedWaterLevelSerializer

    def list(self, request, *args, **kwargs):
        try:
            # Subquery to ensure station_id exists in Station
            valid_stations = models.Station.objects.filter(station_id=OuterRef('station_id__station_id'))
            # Get the latest observation date for valid stations
            latest_entry = models.WaterLevelObservation.objects.filter(
                station_id__isnull=False,
                station_id__station_id__in=models.Station.objects.values('station_id')
            ).latest('observation_date')
            entry_date_time = latest_entry.observation_date
        except models.WaterLevelObservation.DoesNotExist:
            return JsonResponse({}, safe=False)  # Return empty dict if no data exists

        # Query for the last 3 days for valid stations
        queryset = models.WaterLevelObservation.objects.filter(
            observation_date__gte=entry_date_time - timedelta(days=3),
            station_id__isnull=False,
            station_id__station_id__in=models.Station.objects.values('station_id')
        ).select_related('station_id').order_by('station_id__station_id', 'observation_date')

        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)
        # Structure the data into the desired JSON format
        results = defaultdict(list)
        for entry in serializer.data:
            if entry:  # Skip None entries (from invalid stations)
                date_str = entry['wl_date']
                waterlevel_value = entry['waterlevel']
                results[str(entry['st_id'])].append({date_str: waterlevel_value})

        return JsonResponse(results, safe=False)


class ObservedWaterlevelByStationAndDateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ObservedWaterLevelSerializer

    def list(self, request, station_id=None, date=None, *args, **kwargs):
        try:
            # Parse the date parameter (YYYY-MM-DD)
            try:
                start_date = datetime.strptime(date, '%Y-%m-%d').date()
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(days=1)
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            # Query for the specified station and date range
            queryset = models.WaterLevelObservation.objects.filter(
                station_id__station_id=station_id,
                station_id__isnull=False,
                station_id__station_id__in=models.Station.objects.values('station_id'),
                observation_date__gte=start_datetime-timedelta(days=40),
                observation_date__lte=end_datetime-timedelta(days=0)
            ).order_by('-observation_date')

            # Serialize the data
            serializer = self.get_serializer(queryset, many=True)
            # Filter out None entries (invalid stations)
            response_data = [entry for entry in serializer.data if entry]
            return JsonResponse(response_data, safe=False)
        except models.Station.DoesNotExist:
            return JsonResponse([], safe=False)  # Return empty list if station doesn't exist
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

class WaterLevelObservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.WaterLevelObservation.objects.all()
    serializer_class = serializers.WaterLevelObservationSerializer

    @action(detail=False, methods=['get'], url_path='seven-days-observed-waterlevel-by-station/(?P<st_id>\d+)')
    def sevenDaysObservedWaterLevelByStation(self, request, st_id=None):
        station_id = st_id

        if not models.WaterLevelObservation.objects.filter(station_id__station_id=station_id).exists():
            print(f'Station Observed Does Not Exist: {station_id}')
            return JsonResponse(None, safe=False)

        print(f'Station Observed Exists: {station_id}')

        get_last_update_time = models.WaterLevelObservation.objects.filter(
            station_id__station_id=station_id
        ).order_by('-observation_date').values_list('observation_date', flat=True).first()

        print(f'Station Id: {station_id}, Last Update Time: {get_last_update_time}')

        last_update_datetime = datetime.strftime(get_last_update_time, "%Y-%m-%dT%H:%M:%S%z")
        database_time = datetime.strptime(last_update_datetime, "%Y-%m-%dT%H:%M:%S%z")
        new_database_time = database_time.replace(hour=6)

        queryset = models.WaterLevelObservation.objects.filter(
            station_id__station_id=station_id,
            observation_date__gte=new_database_time - timedelta(days=7)
        ).order_by('observation_date').select_related('station_id')

        serializer = serializers.SevenDaysWaterLevelSerializer(queryset, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['get'], url_path='observed-for-medium-range-forecast-by-station/(?P<st_id>\d+)')
    def experimentalObservedWaterLevelByStation(self, request, st_id=None):
        station_id = st_id

        if not models.WaterLevelObservation.objects.filter(station_id__station_id=station_id).exists():
            print(f'Station Observed Does Not Exist: {station_id}')
            return JsonResponse(None, safe=False)

        print(f'Station Observed Exists: {station_id}')

        # Get the latest observation date for the station
        try:
            local_tz = pytz.timezone('Asia/Dhaka')  # +06 timezone
            utc = pytz.UTC
            get_last_update_time = models.WaterLevelObservation.objects.filter(
                station_id__station_id=station_id
            ).order_by('-observation_date').values_list('observation_date', flat=True).first()

            if not get_last_update_time:
                print(f'No observation date found for station_id: {station_id}')
                return JsonResponse(None, safe=False)

            # Convert to UTC for response
            get_last_update_time = get_last_update_time.astimezone(utc)
            last_update_datetime = datetime.strftime(get_last_update_time, "%Y-%m-%dT%H:%M:%SZ")
            print(f'Station Id: {station_id}, Last Update Time: {last_update_datetime}')

            # Set hour to 06:00 and calculate start date (10 days before) in UTC
            database_time = get_last_update_time.replace(hour=6, minute=0, second=0, microsecond=0)
            new_database_time = database_time - timedelta(days=10)

            # Filter observations from the last 10 days
            queryset = models.WaterLevelObservation.objects.filter(
                station_id__station_id=station_id,
                observation_date__gte=new_database_time
            ).order_by('observation_date').select_related('station_id')

            serializer = serializers.ExperimentalObservedWaterLevelSerializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as e:
            print(f'Error retrieving observations for station_id {station_id}: {str(e)}')
            return JsonResponse(None, safe=False)


class ModifiedObservedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.WaterLevelObservation.objects.all() # A base queryset is still required

    def list(self, request, *args, **kwargs):

        queryset_max_dates = models.WaterLevelObservation.objects.values('station_id__station_id').annotate(
            max_observation_date=Max('observation_date')
        ).order_by('station_id__station_id')

        # Collect all unique max_observation_dates for filtering
        max_dates_list = [entry['max_observation_date'] for entry in queryset_max_dates]

        q_objects = Q()
        for entry in queryset_max_dates:
            q_objects |= (
                Q(station_id__station_id=entry['station_id__station_id']) &
                Q(observation_date=entry['max_observation_date'])
            )

        most_recent_records = models.WaterLevelObservation.objects.filter(q_objects).order_by(
            'station_id__station_id', 'observation_date'
        ).select_related('station_id') # Use select_related for efficient FK access

        waterlevelDict = defaultdict(dict)
        for result in most_recent_records:
            st_id = str(result.station_id.station_id) if result.station_id else "Unknown"
            wl_date = result.observation_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            waterlevel = str(result.water_level) # Convert Decimal to string for JSON serialization
            waterlevelDict[st_id][wl_date] = waterlevel
            # print(st_id, wl_date, waterlevel) # For debugging purposes

        return JsonResponse(waterlevelDict, safe=False)


@require_http_methods(["GET"])
def waterlevel_sum_by_station_and_year(request, st_id, year):
    months = [4, 5, 6, 7, 8, 9, 10]
    waterlevel_dict = {}

    for month in months:
        queryset = models.WaterLevelObservation.objects \
            .filter(station_id__station_id=st_id, observation_date__year=year, observation_date__month=month) \
            .aggregate(average_water_level=Avg("water_level"))

        waterlevel_dict[month] = queryset['average_water_level']

    return JsonResponse(waterlevel_dict, safe=False)


class WaterLevelForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.WaterLevelForecast.objects.all()
    serializer_class = serializers.WaterLevelForecastSerializer

    @action(detail=False, methods=['get'], url_path='forecast-waterlevel-by-station/(?P<station_id>\d+)')
    def forecast_waterlevel_by_station(self, request, station_id=None):
        # Check if forecasts exist for the given Station.station_id
        if not models.WaterLevelForecast.objects.filter(station_id__station_id=station_id).exists():
            print(f'Station Forecasts Do Not Exist: {station_id}')
            return JsonResponse(None, safe=False)

        # Get the latest forecast date for the station
        try:
            local_tz = pytz.timezone('Asia/Dhaka')  # +06 timezone
            utc = pytz.UTC
            get_last_update_time = models.WaterLevelForecast.objects.filter(
                station_id__station_id=station_id
            ).order_by('-forecast_date').values_list('forecast_date', flat=True).first()
            
            if not get_last_update_time:
                print(f'No forecast date found for station_id: {station_id}')
                return JsonResponse(None, safe=False)

            # Convert to UTC for response
            get_last_update_time = get_last_update_time.astimezone(utc)
            last_update_datetime = datetime.strftime(get_last_update_time, "%Y-%m-%dT%H:%M:%SZ")
            print(f'Forecast Water Level Date: {last_update_datetime}')

            # Calculate the start date (7 days before) in UTC
            database_time = get_last_update_time - timedelta(days=7)

            # Filter forecasts from the last 7 days
            queryset = models.WaterLevelForecast.objects.filter(
                station_id__station_id=station_id,
                forecast_date__gte=database_time
            )

            serializer = serializers.ForecastWaterLevelSerializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as e:
            print(f'Error retrieving forecasts for station_id {station_id}: {str(e)}')
            return JsonResponse(None, safe=False)

    @action(detail=False, methods=['get'], url_path='seven-days-forecast-waterlevel-by-station/(?P<station_id>\d+)')
    def seven_days_forecast_by_station(self, request, station_id=None):
        # Check if forecasts exist for the given Station.station_id
        if not models.WaterLevelForecast.objects.filter(station_id__station_id=station_id).exists():
            print(f'Station Forecasts Do Not Exist: {station_id}')
            return JsonResponse(None, safe=False)

        # Get the latest forecast date for the station
        try:
            local_tz = pytz.timezone('Asia/Dhaka')  # +06 timezone
            utc = pytz.UTC
            get_last_update_time = models.WaterLevelForecast.objects.filter(
                station_id__station_id=station_id
            ).order_by('-forecast_date').values_list('forecast_date', flat=True).first()
            
            if not get_last_update_time:
                print(f'No forecast date found for station_id: {station_id}')
                return JsonResponse(None, safe=False)

            # Convert to UTC for response
            get_last_update_time = get_last_update_time.astimezone(utc)
            last_update_datetime = datetime.strftime(get_last_update_time, "%Y-%m-%dT%H:%M:%SZ")
            print(f'Forecast Water Level Date: {last_update_datetime}')

            # Calculate the start date (9 days before) in UTC
            database_time = get_last_update_time - timedelta(days=9)

            # Filter forecasts from the last 9 days
            queryset = models.WaterLevelForecast.objects.filter(
                station_id__station_id=station_id,
                forecast_date__gte=database_time
            )

            serializer = serializers.SevenDaysWaterLevelForecastSerializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as e:
            print(f'Error retrieving forecasts for station_id {station_id}: {str(e)}')
            return JsonResponse(None, safe=False)


class FiveDaysForecastWaterlevelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.FiveDaysForecastWaterLevelSerializer
    queryset = models.WaterLevelForecast.objects.all()

    def list(self, request, date=None, *args, **kwargs):
        try:
            # Parse the date parameter from the URL (YYYY-MM-DD) if provided
            if date:
                try:
                    entry_date = datetime.strptime(date, "%Y-%m-%d")
                    entryDateTime = entry_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    logger.info(f"Using URL-provided date: {entryDateTime}")
                except ValueError as e:
                    logger.error(f"Invalid date format: {date}")
                    return JsonResponse({"error": f"Invalid date format, expected YYYY-MM-DD: {str(e)}"}, status=400)
            else:
                # Get entry_date from FfwcLastUpdateDate
                try:
                    last_update = models.FfwcLastUpdateDate.objects.first()
                    if last_update and last_update.entry_date:
                        entryDateTime = last_update.entry_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        logger.info(f"Using entry_date from FfwcLastUpdateDate: {entryDateTime}")
                    else:
                        logger.warning("No entry_date found in FfwcLastUpdateDate, using current date")
                        entryDateTime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                except models.FfwcLastUpdateDate.DoesNotExist:
                    logger.warning("FfwcLastUpdateDate table is empty, using current date")
                    entryDateTime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            logger.info(f"Fetching 5-day forecasts starting from {entryDateTime}")

            # Define start and end dates for the 5-day period
            start_date = entryDateTime + timedelta(days=1)
            end_date = start_date + timedelta(days=5) - timedelta(seconds=1)  # e.g., 2025-06-25 23:59:59

            # Query forecasts for specific hours (06:00, 09:00, 12:00, 15:00, 18:00 UTC)
            forecasts = models.WaterLevelForecast.objects.filter(
                forecast_date__range=(start_date, end_date),
                forecast_date__hour__in=(6, 9, 12, 15, 18),
                forecast_date__minute=0,
                forecast_date__second=0,
                station_id__isnull=False,
                station_id__station_id__in=models.Station.objects.values('station_id')
            ).order_by('station_id__station_id', 'forecast_date')

            logger.info(f"Found {forecasts.count()} forecast records for {start_date} to {end_date}")

            # Serialize the data
            serializer = self.get_serializer(forecasts, many=True)
            
            # Build response dictionary
            waterlevelDict = defaultdict(list)
            for entry in serializer.data:
                if entry:  # Skip None entries (from invalid stations)
                    date_str = entry['fc_date']
                    waterlevel_value = entry['waterlevel']
                    waterlevelDict[str(entry['st_id'])].append({date_str: waterlevel_value})

            if not waterlevelDict:
                logger.warning("No forecast data found for the specified period")
                return JsonResponse({"warning": "No forecast data available"}, status=200)

            return JsonResponse(waterlevelDict, safe=False)

        except Exception as e:
            logger.error(f"Error fetching forecasts: {str(e)}", exc_info=True)
            return JsonResponse({"error": f"Error fetching forecasts: {str(e)}"}, status=500)


# class SevenDaysForecastWaterlevel24HoursViewSet(viewsets.ReadOnlyModelViewSet):
#     serializer_class = serializers.SevenDaysForecastWaterLevelSerializer
#     queryset = models.WaterLevelForecast.objects.all()

#     def list(self, request, date=None, *args, **kwargs):
#         try:
#             # Parse the date parameter from the URL (YYYY-MM-DD) if provided
#             if date:
#                 try:
#                     entry_date = datetime.strptime(date, "%Y-%m-%d")
#                     entryDateTime = entry_date.replace(hour=6, minute=0, second=0, microsecond=0)
#                     logger.info(f"Using URL-provided date: {entryDateTime}")
#                 except ValueError as e:
#                     logger.error(f"Invalid date format: {date}")
#                     return JsonResponse({"error": f"Invalid date format, expected YYYY-MM-DD: {str(e)}"}, status=400)
#             else:
#                 # Get entry_date from FfwcLastUpdateDate
#                 try:
#                     last_update = models.FfwcLastUpdateDate.objects.first()
#                     if last_update and last_update.entry_date:
#                         entryDateTime = last_update.entry_date.replace(hour=6, minute=0, second=0, microsecond=0)
#                         logger.info(f"Using entry_date from FfwcLastUpdateDate: {entryDateTime}")
#                     else:
#                         logger.warning("No entry_date found in FfwcLastUpdateDate, using current date")
#                         entryDateTime = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
#                 except models.FfwcLastUpdateDate.DoesNotExist:
#                     logger.warning("FfwcLastUpdateDate table is empty, using current date")
#                     entryDateTime = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

#             logger.info(f"Fetching 7-day forecasts at 06:00:00 starting from {entryDateTime}")

#             # Define start and end dates for the 7-day period
#             start_date = entryDateTime
#             end_date = start_date + timedelta(days=7) - timedelta(seconds=1)  # e.g., 2025-07-08 23:59:59

#             # Query forecasts for 7 days at 06:00:00
#             forecasts = models.WaterLevelForecast.objects.filter(
#                 forecast_date__range=(start_date, end_date),
#                 forecast_date__hour=6,
#                 forecast_date__minute=0,
#                 forecast_date__second=0,
#                 station_id__isnull=False,
#                 station_id__station_id__in=models.Station.objects.values('station_id')
#             ).order_by('station_id__station_id', 'forecast_date')

#             logger.info(f"Found {forecasts.count()} forecast records for {start_date} to {end_date} at 06:00:00")

#             # Log sample data for debugging
#             if forecasts.exists():
#                 sample = forecasts[:5]
#                 for f in sample:
#                     logger.debug(f"Sample: Station {f.station_id.station_id}, Date {f.forecast_date}, Level {f.water_level}")

#             # Serialize the data
#             serializer = self.get_serializer(forecasts, many=True)

#             # Build response dictionary
#             waterlevelDict = defaultdict(dict)
#             for entry in serializer.data:
#                 if entry:  # Skip None entries (from invalid stations)
#                     date_str = entry['fc_date']
#                     waterlevel_value = entry['waterlevel']
#                     waterlevelDict[str(entry['st_id'])][date_str] = waterlevel_value

#             if not waterlevelDict:
#                 logger.warning("No forecast data found for 06:00:00 over the specified period")
#                 return JsonResponse({"warning": "No forecast data available for 06:00:00 daily"}, status=200)

#             return JsonResponse(waterlevelDict, safe=False)

#         except Exception as e:
#             logger.error(f"Error fetching forecasts: {str(e)}", exc_info=True)
#             return JsonResponse({"error": f"Error fetching forecasts: {str(e)}"}, status=500)


class SevenDaysForecastWaterlevel24HoursViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.SevenDaysForecastWaterLevelSerializer
    queryset = models.WaterLevelForecast.objects.all()

    def list(self, request, date=None, *args, **kwargs):
        try:
            # 1. Determine the Start Date
            if date:
                try:
                    entry_date = datetime.strptime(date, "%Y-%m-%d")
                    start_date = entry_date.replace(hour=6, minute=0, second=0, microsecond=0)
                except ValueError:
                    return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
            else:
                # DYNAMIC FIX: Get the latest date actually present in the forecast table
                latest_record = models.WaterLevelForecast.objects.aggregate(Max('forecast_date'))
                latest_date = latest_record.get('forecast_date__max')

                if latest_date:
                    # We start from the latest date found, but forced to 06:00:00
                    start_date = latest_date.replace(hour=6, minute=0, second=0, microsecond=0)
                    logger.info(f"Using latest available date from DB: {start_date}")
                else:
                    return JsonResponse({"error": "No data found in WaterLevelForecast table"}, status=404)

            # Define the 7-day window
            end_date = start_date + timedelta(days=7) - timedelta(seconds=1)

            # 2. Get flat list of station IDs
            station_ids = models.Station.objects.values_list('station_id', flat=True)

            # 3. Execution of the Query
            # We filter for records at exactly 06:00:00 for each day in the range
            forecasts = models.WaterLevelForecast.objects.filter(
                forecast_date__range=(start_date, end_date),
                forecast_date__hour=6,
                forecast_date__minute=0,
                forecast_date__second=0,
                station_id__isnull=False,
                station_id__station_id__in=station_ids
            ).order_by('station_id__station_id', 'forecast_date')

            # 4. Process Results
            serializer = self.get_serializer(forecasts, many=True)
            
            # Initialize dictionary with all 7 days for every station (showing null if missing)
            waterlevelDict = defaultdict(dict)
            for s_id in station_ids:
                s_id_str = str(s_id)
                for i in range(7):
                    day = start_date + timedelta(days=i)
                    waterlevelDict[s_id_str][day.strftime("%m-%d-%Y")] = None

            # Map actual results into the dictionary
            for entry in serializer.data:
                if entry and 'st_id' in entry:
                    waterlevelDict[str(entry['st_id'])][entry['fc_date']] = entry.get('waterlevel')

            # 5. Final check
            if not forecasts.exists():
                return JsonResponse({
                    "warning": "No forecast data matches the 06:00:00 timestamp",
                    "debug_info": {
                        "attempted_start": str(start_date),
                        "attempted_end": str(end_date),
                        "total_found": forecasts.count()
                    }
                }, status=200)

            return JsonResponse(waterlevelDict, safe=False)

        except Exception as e:
            logger.error(f"Error in SevenDaysForecastView: {str(e)}", exc_info=True)
            return JsonResponse({"error": "Internal server error"}, status=500)

class TenDaysForecastWaterlevel24HoursViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.TenDaysForecastWaterLevelSerializer
    queryset = models.WaterLevelForecastsExperimentals.objects.all()

    def list(self, request, date=None, *args, **kwargs):
        try:
            if date:
                try:
                    entry_date = datetime.strptime(date, "%Y-%m-%d")
                    entryDateTime = entry_date.replace(hour=6, minute=0, second=0, microsecond=0)
                    logger.info(f"Using URL-provided date: {entryDateTime}")
                except ValueError as e:
                    logger.error(f"Invalid date format: {date}")
                    return JsonResponse({"error": f"Invalid date format, expected YYYY-MM-DD: {str(e)}"}, status=400)
            else:
                try:
                    last_update = models.FfwcLastUpdateDateExperimental.objects.first()
                    if last_update and last_update.entry_date:
                        entryDateTime = last_update.entry_date.replace(hour=6, minute=0, second=0, microsecond=0)
                        logger.info(f"Using entry_date from FfwcLastUpdateDateExperimental: {entryDateTime}")
                    else:
                        logger.warning("No entry_date found in FfwcLastUpdateDateExperimental, using current date")
                        entryDateTime = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
                except models.FfwcLastUpdateDateExperimental.DoesNotExist:
                    logger.warning("FfwcLastUpdateDateExperimental table is empty, using current date")
                    entryDateTime = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

            logger.info(f"Fetching 10-day forecasts at 06:00:00 starting from {entryDateTime}")

            start_date = entryDateTime
            end_date = start_date + timedelta(days=10) - timedelta(seconds=1)

            # Get all valid station IDs
            # station_ids = models.Station.objects.values_list('station_id', flat=True)
            station_ids = models.Station.objects.filter(ten_days_forecast=True).values_list('station_id', flat=True)


            # Query forecasts for 10 days at 06:00:00
            forecasts = models.WaterLevelForecastsExperimentals.objects.filter(

                forecast_date__range=(start_date, end_date),
                forecast_date__hour=6,
                forecast_date__minute=0,
                forecast_date__second=0,
                station_id__isnull=False,
                station_id__station_id__in=station_ids
            ).order_by('station_id__station_id', 'forecast_date')

            logger.info(f"Found {forecasts.count()} forecast records for {start_date} to {end_date} at 06:00:00")

            if forecasts.exists():
                sample = forecasts[:5]
                for f in sample:
                    logger.debug(f"Sample: Station {f.station_id.station_id}, Date {f.forecast_date}, Min {f.waterlevel_min}, Max {f.waterlevel_max}, Mean {f.waterlevel_mean}")

            serializer = self.get_serializer(forecasts, many=True)

            # Build response dictionary with all days for each station
            waterlevelDict = defaultdict(dict)
            for station_id in station_ids:
                station_id_str = str(station_id)
                for i in range(10):
                    date = start_date + timedelta(days=i)
                    date_str = date.strftime("%m-%d-%Y")
                    waterlevelDict[station_id_str][date_str] = {"min": None, "max": None, "mean": None}

            for entry in serializer.data:
                if entry:
                    date_str = entry['fc_date']
                    waterlevelDict[str(entry['st_id'])][date_str] = {
                        'min': entry['min'],
                        'max': entry['max'],
                        'mean': entry['mean']
                    }

            if not any(waterlevelDict[station_id] for station_id in waterlevelDict):
                logger.warning("No forecast data found for 06:00:00 over the specified period")
                return JsonResponse({"warning": "No forecast data available for 06:00:00 daily"}, status=200)

            return JsonResponse(waterlevelDict, safe=False)

        except Exception as e:
            logger.error(f"Error fetching forecasts: {str(e)}", exc_info=True)
            return JsonResponse({"error": f"Error fetching forecasts: {str(e)}"}, status=500)

class MorningWaterlevelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset that returns the 9 AM water level observations
    for the latest two days for all stations.
    """
    queryset = models.WaterLevelObservation.objects.all()

    def list(self, request, *args, **kwargs):
        try:
            latest_record = self.get_queryset().latest('observation_date')
            latest_date = latest_record.observation_date.date()
        except models.WaterLevelObservation.DoesNotExist:
            return JsonResponse({}, safe=False)

        nine_am_time = time(9, 0, 0)
        
        today_9am = datetime.combine(latest_date, nine_am_time)
        yesterday_9am = datetime.combine(latest_date - timedelta(days=1), nine_am_time)

        queryset = self.get_queryset().filter(
            Q(observation_date=today_9am) | Q(observation_date=yesterday_9am)
        ).order_by('station_id__station_id', 'observation_date')

        waterlevel_dict = defaultdict(dict)
        for record in queryset:
            # station_id is an integer, so we convert it to a string for the dictionary key
            station_id = str(record.station_id.station_id)
            # Format the date string to match the requested output format
            date_str = record.observation_date.strftime("%m-%d-%Y %H:%M:%S")
            # Convert the DecimalField water_level to a string
            water_level = str(record.water_level)
            waterlevel_dict[station_id][date_str] = water_level

        return JsonResponse(waterlevel_dict, safe=False)

class AfternoonWaterlevelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset that returns the 3 PM water level observations
    for the latest two days for all stations.
    """
    queryset = models.WaterLevelObservation.objects.all()

    def list(self, request, *args, **kwargs):
        # Find the latest record to determine the "current" date
        try:
            latest_record = self.get_queryset().latest('observation_date')
            latest_date = latest_record.observation_date.date()
        except models.WaterLevelObservation.DoesNotExist:
            return JsonResponse({}, safe=False)

        # Define the 3 PM time
        three_pm_time = time(15, 0, 0)
        
        # Create datetime objects for the latest date's 3 PM and the previous day's 3 PM
        today_3pm = datetime.combine(latest_date, three_pm_time)
        yesterday_3pm = datetime.combine(latest_date - timedelta(days=1), three_pm_time)

        # Query for both timestamps using a combined filter
        queryset = self.get_queryset().filter(
            Q(observation_date=today_3pm) | Q(observation_date=yesterday_3pm)
        ).order_by('station_id__station_id', 'observation_date')

        # Process the combined data
        waterlevel_dict = defaultdict(dict)
        for record in queryset:
            # station_id is an integer, so we convert it to a string for the dictionary key
            station_id = str(record.station_id.station_id)
            # Format the date string to match the requested output format
            date_str = record.observation_date.strftime("%m-%d-%Y %H:%M:%S")
            # Convert the DecimalField water_level to a string
            water_level = str(record.water_level)
            waterlevel_dict[station_id][date_str] = water_level

        return JsonResponse(waterlevel_dict, safe=False)

class WaterLevelObservationExperimentalsView(APIView):
    def get(self, request, **kwargs):
        station_id = kwargs.get('st_id')
        if not station_id:
            logger.error("Station ID is required for WaterLevelObservationExperimentalsView")
            return Response({"error": "Station ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Processing experimental observation water levels for station: {station_id}")
        
        try:
            if not models.WaterLevelObservationExperimentals.objects.filter(station_id__station_id=station_id).exists():
                logger.info(f"No experimental observations found for station: {station_id}")
                return Response([], status=status.HTTP_200_OK) # Return empty array if no data
            
            # Query observation data for the given station, ordered by date
            queryset = models.WaterLevelObservationExperimentals.objects.filter(
                station_id__station_id=station_id
            ).order_by('observation_date') # <<<--- CHANGED THIS LINE
            
            serializer = serializers.WaterLevelObservationExperimentalsSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except models.Station.DoesNotExist: 
 
            logger.error(f"Station with ID {station_id} does not exist in the Station model or related data.")
            return Response({"error": f"Station with ID {station_id} not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error processing observation request for station {station_id}: {str(e)}", exc_info=True)
            return Response({"error": "An unexpected error occurred. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HistoricalWaterlevelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset that returns historical water level observations 
    for a given date range and hour.
    """
    queryset = models.WaterLevelObservation.objects.all()

    def list(self, request, *args, **kwargs):
        # 1. Get query parameters for the date range and hour
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        hour_str = request.query_params.get('hour')

        # 2. Validate and parse the input
        if not all([start_date_str, end_date_str, hour_str]):
            return JsonResponse(
                {"error": "Please provide 'start_date', 'end_date', and 'hour' query parameters."}, 
                status=400
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            target_hour = int(hour_str)
            if not 0 <= target_hour <= 23:
                raise ValueError("Hour must be between 0 and 23.")
        except (ValueError, TypeError):
            return JsonResponse(
                {"error": "Invalid date or hour format. Dates should be YYYY-MM-DD and hour should be an integer."}, 
                status=400
            )
        
        # 3. Build a list of datetime objects for the target hour in the date range
        target_time = time(target_hour, 0, 0)
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(datetime.combine(current_date, target_time))
            current_date += timedelta(days=1)

        # 4. Query the database for the list of datetimes
        queryset = self.get_queryset().filter(
            observation_date__in=date_list
        ).order_by('station_id__station_id', 'observation_date')

        # 5. Process the data and return the response
        waterlevel_dict = defaultdict(dict)
        for record in queryset:
            station_id = str(record.station_id.station_id)
            date_str = record.observation_date.strftime("%Y-%m-%d %H:%M:%S")
            water_level = str(record.water_level)
            waterlevel_dict[station_id][date_str] = water_level

        return JsonResponse(waterlevel_dict, safe=False)



class WaterLevelForecastsExperimentalsView(APIView):
    def get(self, request, **kwargs):
        station_id = kwargs.get('st_id')
        if not station_id:
            logger.error("Station ID is required for WaterLevelForecastsExperimentalsView")
            return Response({"error": "Station ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Processing experimental forecast water levels for station: {station_id}")
        
        try:
            # OPTION 1: Explicitly check for Station existence first (RECOMMENDED for clearer error)
            # This ensures that if the station_id itself is invalid, we return a 404
            # before trying to query related observation/forecast data.
            try:
                station_obj = models.Station.objects.get(station_id=station_id)
            except models.Station.DoesNotExist:
                logger.error(f"Station with ID {station_id} does not exist in the Station model.")
                return Response({"error": f"Station with ID {station_id} not found."}, status=status.HTTP_404_NOT_FOUND)

            # Check if station has any experimental forecasts
            # Use the station_obj directly now that we've retrieved it
            if not models.WaterLevelForecastsExperimentals.objects.filter(station_id=station_obj).exists():
                logger.info(f"No experimental forecasts found for station: {station_id}")
                return Response([], status=status.HTTP_200_OK) # Return empty list if no forecasts
            
            logger.info(f"Experimental forecasts exist for station: {station_id}")
            
            # Get the latest observation_date from WaterLevelObservationExperimentals
            # Filter by the station_obj directly.
            # Order by 'observation_date' (the actual model field) in descending order.
            latest_observation = models.WaterLevelObservationExperimentals.objects.filter(
                station_id=station_obj
            ).order_by('-observation_date').first() # <<<--- CORRECTED: Use 'observation_date'
            
            forecast_start_date = None
            if latest_observation:
                forecast_start_date = latest_observation.observation_date # <<<--- CORRECTED: Use 'observation_date'
                logger.info(f"Using latest experimental observation date for forecasts: {forecast_start_date}")
            else:
                logger.info(f"No experimental observations found for station: {station_id}. Returning all available forecasts.")
                # If no observations, we'll return all forecasts for this station.
                # Adjust this behavior based on your specific requirements.

            # Query forecast data where forecast_date >= latest observation date (if available)
            # Filter by the station_obj directly.
            queryset = models.WaterLevelForecastsExperimentals.objects.filter(
                station_id=station_obj
            )
            
            if forecast_start_date:
                queryset = queryset.filter(
                    forecast_date__gte=forecast_start_date # This was already correct, assuming 'forecast_date' is the model field
                )
            
            # Order the final queryset by 'forecast_date' (the actual model field)
            queryset = queryset.order_by('forecast_date') # <<<--- CORRECTED: Use 'forecast_date'
            
            serializer = serializers.WaterLevelForecastsExperimentalsSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e: # Catch all other unexpected errors
            logger.error(f"Error processing forecast request for station {station_id}: {str(e)}", exc_info=True)
            # Provide a generic error message for internal server errors
            return Response({"error": "An unexpected error occurred. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# class WaterLevelForecastsExperimentalsView(APIView):
#     def get(self, request, **kwargs):
#         try:
#             station_id = kwargs.get('st_id')
#             if not station_id:
#                 logger.error("Station ID is required")
#                 return Response({"error": "Station ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
#             logger.info(f"Processing experimental forecast water levels for station: {station_id}")
            
#             # Check if station exists in forecast data
#             if not models.WaterLevelForecastsExperimentals.objects.filter(station_id=station_id).exists():
#                 logger.info(f"Station Forecast Does Not Exist: {station_id}")
#                 return Response(None, status=status.HTTP_200_OK)
            
#             logger.info(f"Station Forecast Exists: {station_id}")
            
#             # Get the latest wl_date from WaterLevelObservationExperimentals
#             latest_observation = models.WaterLevelObservation.objects.filter(
#                 station_id=station_id
#             ).order_by('-observation_date').first()
            
#             if not latest_observation:
#                 logger.info(f"No observations found for station: {station_id}")
#                 return Response(None, status=status.HTTP_200_OK)
            
#             forecast_date = latest_observation.observation_date
#             logger.info(f"Using latest observation date for forecasts: {forecast_date}")
            
#             # Query forecast data where forecast_date >= latest wl_date
#             queryset = models.WaterLevelForecastsExperimentals.objects.filter(
#                 station_id=station_id,
#                 forecast_date__gte=forecast_date
#             ).order_by('forecast_date')
            
#             serializer = serializers.WaterLevelForecastsExperimentalsSerializer(queryset, many=True)
#             return Response(serializer.data, status=status.HTTP_200_OK)
        
#         except Exception as e:
#             logger.error(f"Error processing forecast request for station {station_id}: {str(e)}")
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RainfallObservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.RainfallObservation.objects.all()
    serializer_class = serializers.RainfallObservationSerializer

class AnnotatedObservedTrendViewSet(viewsets.ReadOnlyModelViewSet):
    def list(self, request, *args, **kwargs):
        # Get the latest observation date
        try:
            latest_record = models.WaterLevelObservation.objects.latest('observation_date')
            entry_date_time = latest_record.observation_date
        except models.WaterLevelObservation.DoesNotExist:
            return JsonResponse({}, safe=False)

        # Define time boundaries (latest date, 3 hours ago, 24 hours ago, and 2 days ago for filtering)
        d2 = entry_date_time - timedelta(days=2)
        time_3h_ago = entry_date_time - timedelta(hours=3)
        time_24h_ago = entry_date_time - timedelta(hours=24)

        # Dictionaries to store dates and water levels by station_id
        water_level_date_dict = defaultdict(list)
        water_level_values_dict = defaultdict(list)
        station_value_diff_by_hour = {}

        # Query observations from the last 2 days, ordered by station_id and observation_date (descending)
        observations = models.WaterLevelObservation.objects.filter(
            observation_date__gte=d2
        ).values('station_id', 'observation_date', 'water_level').order_by('station_id', '-observation_date')

        # Group observations by station_id
        for result in observations:
            st_id = result['station_id']
            water_level_date_dict[st_id].append(result['observation_date'])
            water_level_values_dict[st_id].append(float(result['water_level']))  # Convert Decimal to float for JSON

        # Calculate water level differences for each station
        for st_id in water_level_date_dict.keys():
            dates = water_level_date_dict[st_id]
            values = water_level_values_dict[st_id]
            length = len(dates)

            if length < 2:
                # Not enough data for differences
                station_value_diff_by_hour[st_id] = {'wl_date': [3, 24], 'waterlevel': ['na', 'na']}
                continue

            # Latest observation
            latest_date = dates[0]
            latest_value = values[0]

            # Find observations closest to 3 hours and 24 hours ago
            value_3h = 'na'
            value_24h = 'na'

            for i in range(1, length):
                date_diff = latest_date - dates[i]
                hours_diff = date_diff.total_seconds() / 3600

                # Check for observation closest to 3 hours ago
                if value_3h == 'na' and abs(hours_diff - 3) <= 1:  # Allow 1-hour tolerance
                    value_3h = round(latest_value - values[i],4)
                # Check for observation closest to 24 hours ago
                if value_24h == 'na' and abs(hours_diff - 24) <= 1:  # Allow 1-hour tolerance
                    value_24h = round(latest_value - values[i],4)

                # Stop if both differences are found
                if value_3h != 'na' and value_24h != 'na':
                    break

            station_value_diff_by_hour[st_id] = {
                'wl_date': [3, 24],
                'waterlevel': [value_3h, value_24h]
            }

        return JsonResponse(station_value_diff_by_hour, safe=False)



class RecentObservedWaterlevelViewSet(viewsets.ReadOnlyModelViewSet):
    def list(self, request, *args, **kwargs):
        try:
            latest_record = models.WaterLevelObservation.objects.latest('observation_date')
            entry_date_time = latest_record.observation_date
        except models.WaterLevelObservation.DoesNotExist:
            return JsonResponse({}, safe=False)

        one_day_ago = entry_date_time - timedelta(days=60)
        observed_values_dict = defaultdict(list)

        observations = models.WaterLevelObservation.objects.filter(
            observation_date__gte=one_day_ago
        ).values('station_id', 'observation_date', 'water_level').order_by('station_id', 'observation_date')

        for result in observations:
            st_id = result['station_id']
            wl_date = result['observation_date'].strftime('%Y-%m-%d %H')
            water_level = f"{result['water_level']:.2f}"  # Format as string with 2 decimal places
            observed_values_dict[st_id].append({wl_date: water_level})

        return JsonResponse(observed_values_dict, safe=False)



class WaterLevelByStationAndYearView(View):
    def get(self, request, **kwargs):
        station_id_str = kwargs['st_id']
        year = int(kwargs['year'])
        
        # The logic is simplified as both conditions
        # for 'current_year' and 'other years' are identical.
        queryset = models.WaterLevelObservation.objects.filter(
            station_id__station_id=station_id_str, # Using ForeignKey to filter by 'station_id'
            observation_date__year=year
        ).order_by('observation_date')
        
        queryset = queryset.filter(observation_date__month__range=[5, 10])
        
        waterlevel_data = {
            str(year): [
                {
                    'wl_date': record.observation_date.isoformat(),
                    'waterlevel': float(record.water_level)
                }
                for record in queryset
            ]
        }
        
        return JsonResponse(waterlevel_data, safe=False)


class ObservedRainfallViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ObservedRainfallSerializer

    def get_queryset(self):
        # Get the latest observation date for each station
        latest_entries = models.RainfallObservation.objects.values('station_id').annotate(
            latest_observation_date=Max('observation_date')
        )

        # Build filter conditions for (station_id, latest_observation_date) pairs
        conditions = [
            Q(station_id=entry['station_id'], observation_date=entry['latest_observation_date'])
            for entry in latest_entries
        ]

        # Handle empty case
        if not conditions:
            return models.RainfallObservation.objects.none()

        # Combine conditions with OR
        combined_condition = conditions[0]
        for condition in conditions[1:]:
            combined_condition |= condition

        # Filter observations and select related station and basin
        queryset = models.RainfallObservation.objects.filter(
            combined_condition
        ).select_related('station_id', 'station_id__basin')

        return queryset

    # @action(detail=False, url_path='forty-days-by-station-and-date/(?P<station_id>[^/.]+)/(?P<start_date>[^/.]+)')
    # def forty_days_rainfall_by_station_and_date(self, request, **kwargs):
    #     print(' . . In new Rainfall by Station And Date . . ')
        
    #     # Get station_id and start_date from URL
    #     station_id = self.kwargs['station_id']
    #     start_date_str = self.kwargs['start_date']
        
    #     # Parse the start date and calculate the date 40 days prior
    #     start_datetime = datetime.strptime(start_date_str, "%Y-%m-%d")
    #     previous_date_before_forty_days = start_datetime - timedelta(days=40)
        
    #     print('Start Date Time for Query..', start_datetime)
    #     print('Previous Date Before 40 Days..', previous_date_before_forty_days)

    #     # Filter the queryset using the new model and field names
    #     queryset = models.RainfallObservation.objects.filter(
    #         station_id=station_id,
    #         observation_date__gte=previous_date_before_forty_days,
    #         observation_date__lt=start_datetime
    #     )
        
    #     # Serialize the data using the new serializer
    #     serializer = serializers.RainfallObservationSerializer(queryset, many=True)
        
    #     return Response(serializer.data)

    def fourty_days_rainfall_by_station_and_date(self, request, station_id, start_date):
        print(' . . In new Rainfall by Station And Date . . ')
        
        # Parse the start date and calculate the date 40 days prior
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")+ timedelta(days=1)
        previous_date_before_forty_days = start_datetime - timedelta(days=40)
        
        print('Start Date Time for Query..', start_datetime)
        print('Previous Date Before 40 Days..', previous_date_before_forty_days)

        # Filter the queryset
        queryset = models.RainfallObservation.objects.filter(
            station_id=station_id,
            observation_date__gte=previous_date_before_forty_days,
            observation_date__lte=start_datetime
        )
        
        # Serialize the data
        serializer = serializers.FourtyDaysRainfallObservationSerializer(queryset, many=True)
        
        return Response(serializer.data)

class ObservedRainfallByDateView(APIView):
    def get(self, request, date_str):
        try:
            observation_date_naive = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Convert date to datetime object with a specific time (e.g., 06:00:00) and make it timezone-aware
            observation_datetime = timezone.make_aware(
                datetime.combine(observation_date_naive, datetime.min.time().replace(hour=6))
            )

            # Get all active rainfall stations
            # Assuming models.RainfallStation is the equivalent of FfwcRainfallStationsNew and FfwcRainfallStations
            all_stations = models.RainfallStation.objects.filter(status=True).select_related('basin')

                        # Start of the day (00:00:00)
            start_of_day = timezone.make_aware(datetime.combine(observation_date_naive, datetime.min.time()))
            # End of the day (23:59:59.999999)
            end_of_day = timezone.make_aware(datetime.combine(observation_date_naive, datetime.max.time()))

            # Get rainfall observations for the specific date
            # Assuming RainfallObservation.station_id links to RainfallStation.id
            observations = models.RainfallObservation.objects.filter(
                # observation_date__date=observation_date_naive
                # observation_date=observation_datetime
                observation_date__range=(start_of_day, end_of_day)
            ).select_related('station_id')

            # Create a dictionary for quick lookup of observations by station_id
            observed_rainfall_dict = {
                obs.station_id.id: float(obs.rainfall) for obs in observations
            }

            # Prepare the response data for all stations
            response_data = []
            today = datetime.today()
            current_month = today.month

            for station in all_stations:
                # Fetch normal and max rainfall once per station
                monthly_rainfall_data = models.MonthlyRainfall.objects.filter(
                    station_id=station.station_id,  # Assuming station_id in MonthlyRainfall refers to RainfallStation.station_id
                    month_serial=current_month
                ).first()

                normal_rainfall = monthly_rainfall_data.normal_rainfall if monthly_rainfall_data else None
                max_rainfall = monthly_rainfall_data.max_rainfall if monthly_rainfall_data else None

                response_data.append({
                    'station_id': station.id, # This is the primary key, st_id for the serializer
                    'station_code': station.station_id, # This is the string code, station_id for the serializer
                    'rf_date': observation_datetime.isoformat(),
                    'rainfall': observed_rainfall_dict.get(station.id, -9999.0), # Default to -9999.0 if no observation
                    'name': station.name,
                    'basin': station.basin.name if station.basin else None,
                    'division': station.division,
                    'district': station.district,
                    'upazilla': station.upazilla,
                    'lat': str(station.latitude) if station.latitude is not None else None,
                    'long': str(station.longitude) if station.longitude is not None else None,
                    'status': 1 if station.status else 0,
                    'normal_rainfall': normal_rainfall,
                    'max_rainfall': max_rainfall,
                })

            serializer = serializers.RainfallObservationByDateSerializer(response_data, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def rainfall_sum_by_station_and_year(request, st_id, year):
    """
    Calculates the average rainfall for specific months of a given year
    and station.
    """
    try:
        year = int(year)
        # The URL captures st_id, but we need the ForeignKey to RainfallStation.
        # We'll filter on the station_code from the RainfallStation model.
        station = models.RainfallStation.objects.get(station_id=st_id)
    except models.RainfallStation.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid year or station code format'}, status=400)

    months = [4, 5, 6, 7, 8, 9, 10]
    rainfall_dict = {}

    for month in months:
        queryset = models.RainfallObservation.objects \
            .filter(station_id=station) \
            .filter(observation_date__year=year, observation_date__month=month) \
            .aggregate(average_rainfall=Avg("rainfall"))
        
        rainfall_dict[month] = queryset['average_rainfall']

    return JsonResponse(rainfall_dict, safe=False)


# class ObservedRainfallByDateView(APIView):
#     def get(self, request, date_str):
#         try:
#             observation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
#             observations = models.RainfallObservation.objects.filter(
#                 observation_date__date=observation_date
#             ).select_related('station_id', 'station_id__basin')
#             if not observations:
#                 return Response(
#                     {"error": f"No rainfall observations found for {date_str}"},
#                     status=status.HTTP_404_NOT_FOUND
#                 )
#             serializer = serializers.RainfallObservationByDateSerializer(observations, many=True)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except ValueError:
#             return Response(
#                 {"error": "Invalid date format. Use YYYY-MM-DD."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         except Exception as e:
#             return Response(
#                 {"error": f"An error occurred: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

class ThreeDaysObservedRainfallViewSet(viewsets.ReadOnlyModelViewSet):
    
    queryset = models.RainfallObservation.objects.all()
    serializer_class = serializers.ThreeDaysObservedRainfallSerializer

    def list(self, request, *args, **kwargs):
        # Get the latest observation date for filtering
        latest_entry = models.RainfallObservation.objects.latest('observation_date')
        latest_entry_date_time = latest_entry.observation_date

        # Query for the last 10 days of data for all stations, ordered by station_id and date
        queryset = models.RainfallObservation.objects.filter(
            observation_date__gte=latest_entry_date_time - timedelta(days=10)
        ).order_by('station_id', 'observation_date')

        # Structure the data into the desired JSON format
        results = defaultdict(list)
        for entry in queryset:
            date_str = entry.observation_date.strftime("%d-%m-%Y")
            rainfall_value = f"{entry.rainfall:.2f}"  # Format rainfall to 2 decimal places
            results[str(entry.station_id_id)].append({date_str: rainfall_value})

        return JsonResponse(results, safe=False)



class RainfallByStationViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = serializers.ThreeDaysObservedRainfallSerializer

    def list(self, request, station_id=None, *args, **kwargs):
        # Get the latest observation date for filtering
        latest_entry = models.RainfallObservation.objects.latest('observation_date')
        latest_entry_date_time = latest_entry.observation_date

        # Query for the last 30 days of data for the specified station_id
        queryset = models.RainfallObservation.objects.filter(
            station_id=station_id,
            observation_date__gte=latest_entry_date_time - timedelta(days=30)
        ).order_by('-observation_date')

        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)
        response_data = [
            {
                "st_id": entry["station_id"],
                "rf_date": entry["observation_date"],
                "rainfall": f"{float(entry['rainfall']):.2f}"
            }
            for entry in serializer.data
        ]

        return JsonResponse(response_data, safe=False)


def get_experimental_stations(request):
    stations = models.Station.objects.filter(experimental=True).order_by('station_id').annotate(
        json_id=F('station_id') 
    ).values('json_id', 'name') # Select the newly created 'json_id' and the 'name'
    
    
    result_list = []
    for station_data in stations:
        result_list.append({
            'id': station_data['json_id'], 
            'name': station_data['name']
        })
        
    return JsonResponse(result_list, safe=False)


def get_medium_range_stations(request):

    
    stations_queryset = models.Station.objects.filter(
        medium_range_station=True
    ).order_by('station_id').select_related('basin', 'unit') 
    
    result_list = []
    for station in stations_queryset:
        # Construct the dictionary for each station, matching the desired JSON structure
        station_data = {
            "id": station.station_id, # The primary key 'id'
            "coords": f"{station.latitude},{station.longitude}", # Combine latitude and longitude
            "name": station.name,
            "river": station.river,
            # "basin_order": station.basin.order if station.basin else None, # Assuming 'order' exists on Basin model
            "basin": station.basin.name if station.basin else None, # Access name of related basin
            "dangerlevel": str(station.danger_level) if station.danger_level is not None else None, # Convert float to string, handle None
            "riverhighestwaterlevel": str(station.highest_water_level) if station.highest_water_level is not None else None, # Convert float to string, handle None
            "pmdl": station.pmdl,
            "river_chainage": station.river_chainage,
            "division": station.division,
            "district": station.district,
            "upazilla": station.upazilla,
            "union": station.union,
            "long": str(station.longitude), # Convert float to string
            "order_up_down": station.order_up_down,
            "lat": str(station.latitude),   # Convert float to string
            "forecast_observation": int(station.forecast_observation) if station.forecast_observation else None, # Convert to int if exists
            "status": int(station.status), # Convert boolean to 0 or 1
            "station_order": station.station_order,
            "medium_range_station": int(station.medium_range_station), # Convert boolean to 0 or 1
            "unit_id": station.unit.id if station.unit else None, # Access id of related unit
            "jason_2_satellie_station": int(station.jason_2_satellite_station) if station.jason_2_satellite_station is not None else 0, # Handle typo, convert bool to 0/1, default 0 if None
            "rhwl": station.highest_water_level, # Original field name, not string
            "date_of_rhwl": station.highest_water_level_date.strftime('%Y-%m-%d') if station.highest_water_level_date else None # Format date
        }
        
        # Remove keys with None values if you want a cleaner JSON (optional)
        # station_data = {k: v for k, v in station_data.items() if v is not None}
        
        result_list.append(station_data)
        
    return JsonResponse(result_list, safe=False)




def get_extended_range_stations(request):
    """
    Returns a list of medium range stations with data formatted as specified.
    """
    
    # Select stations where medium_range_station is True
    # Use select_related to fetch related Basin and Unit objects efficiently
    stations_queryset = models.Station.objects.filter(
        extended_range_station=True
    ).order_by('station_id').select_related('basin', 'unit') # Fetch related basin and unit objects
    
    result_list = []
    for station in stations_queryset:
        # Construct the dictionary for each station, matching the desired JSON structure
        station_data = {
            "id": station.station_id, # The primary key 'id'
            "coords": f"{station.latitude},{station.longitude}", # Combine latitude and longitude
            "name": station.name,
            "river": station.river,
            # "basin_order": station.basin.order if station.basin else None, # Assuming 'order' exists on Basin model
            "basin": station.basin.name if station.basin else None, # Access name of related basin
            "dangerlevel": str(station.danger_level) if station.danger_level is not None else None, # Convert float to string, handle None
            "riverhighestwaterlevel": str(station.highest_water_level) if station.highest_water_level is not None else None, # Convert float to string, handle None
            "pmdl": station.pmdl,
            "river_chainage": station.river_chainage,
            "division": station.division,
            "district": station.district,
            "upazilla": station.upazilla,
            "union": station.union,
            "long": str(station.longitude), # Convert float to string
            "order_up_down": station.order_up_down,
            "lat": str(station.latitude),   # Convert float to string
            "forecast_observation": int(station.forecast_observation) if station.forecast_observation else None, # Convert to int if exists
            "status": int(station.status), # Convert boolean to 0 or 1
            "station_order": station.station_order,
            "medium_range_station": int(station.medium_range_station), # Convert boolean to 0 or 1
            "unit_id": station.unit.id if station.unit else None, # Access id of related unit
            "jason_2_satellie_station": int(station.jason_2_satellite_station) if station.jason_2_satellite_station is not None else 0, # Handle typo, convert bool to 0/1, default 0 if None
            "rhwl": station.highest_water_level, # Original field name, not string
            "date_of_rhwl": station.highest_water_level_date.strftime('%Y-%m-%d') if station.highest_water_level_date else None # Format date
        }
        
        # Remove keys with None values if you want a cleaner JSON (optional)
        # station_data = {k: v for k, v in station_data.items() if v is not None}
        
        result_list.append(station_data)
        
    return JsonResponse(result_list, safe=False)


class ShortRangeStationByBasinView(APIView):
    def get(self, request, **kwargs):
        # Retrieves 'basin_id' from the URL keyword arguments.
        basin_id = self.kwargs.get('basin_id')
        if basin_id is None:
            # Returns a 400 Bad Request if basin_id is not provided in the URL.
            return Response({"detail": "basin_id is required in the URL."}, status=status.HTTP_400_BAD_REQUEST)

        # Filters the Station objects based on the basin ID and other criteria.
        # - basin__id=basin_id: Filters by the ID of the related Basin object.
        # - status=True: Filters for active stations (status is a BooleanField).
        # - .exclude(forecast_observation__in=['0', '', None]): Excludes stations where
        #   'forecast_observation' is '0', an empty string, or None. This handles the
        #   'forecast_observation__gt=0' logic for a CharField.
        queryset = models.Station.objects.filter(
            basin__id=basin_id,
            status=True,
            medium_range_station=False
        ).exclude(
            forecast_observation__in=['0', '', None]
        ).order_by('station_id')

        # Initializes the serializer with the filtered queryset.
        # 'many=True' indicates that a list of objects is being serialized.
        serializer = serializers.ShortRangeStationSerializer(queryset, many=True)

        # Returns the serialized data as an API response.
        return Response(serializer.data)


class MediumRangeStationByBasinView(APIView):
    def get(self, request, **kwargs):
        # Retrieves 'basin_id' from the URL keyword arguments.
        basin_id = self.kwargs.get('basin_id')
        if basin_id is None:
            # Returns a 400 Bad Request if basin_id is not provided in the URL.
            return Response({"detail": "basin_id is required in the URL."}, status=status.HTTP_400_BAD_REQUEST)
        queryset = models.Station.objects.filter(
            basin__id=basin_id,
            status=True,
            medium_range_station=True
        ).exclude(
            forecast_observation__in=['0', '', None]
        ).order_by('station_id')

        # Initializes the serializer with the filtered queryset.
        # 'many=True' indicates that a list of objects is being serialized.
        serializer = serializers.ShortRangeStationSerializer(queryset, many=True)

        # Returns the serialized data as an API response.
        return Response(serializer.data)

class ShortRangeStationByDivisionView(APIView):
    def get(self, request, **kwargs):
        # Retrieve the division name from the URL keyword arguments
        division_name = self.kwargs.get('division_name')
        if division_name is None:
            return Response({"detail": "division_name is required in the URL."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = models.Station.objects.filter(
            division=division_name, # Use __iexact for case-insensitive match
            status=True,
            medium_range_station=False
        ).exclude(
            forecast_observation__in=['0', '', None]
        ).order_by('station_id')

        serializer = serializers.ShortRangeStationSerializer(queryset, many=True)
        return Response(serializer.data)

class MediumRangeStationByDivisionView(APIView):
    def get(self, request, **kwargs):
        # Retrieve the division name from the URL keyword arguments
        division_name = self.kwargs.get('division_name')
        if division_name is None:
            return Response({"detail": "division_name is required in the URL."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = models.Station.objects.filter(
            division=division_name, # Use __iexact for case-insensitive match
            status=True,
            medium_range_station=True
        ).exclude(
            forecast_observation__in=['0', '', None]
        ).order_by('station_id')

        serializer = serializers.ShortRangeStationSerializer(queryset, many=True)
        return Response(serializer.data)

    
class StationByIdView(APIView):
    def get(self, request, **kwargs):
        station_id = self.kwargs.get('station_id')
        if station_id is None:
            return Response({"detail": "station_id is required in the URL."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = models.Station.objects.filter(station_id=station_id)

        if not queryset.exists():
            return Response({"detail": f"Station with ID '{station_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

        # Use the new StationByIdResponseSerializer for this specific endpoint
        serializer = serializers.StationByIdResponseSerializer(queryset, many=True)
        return Response(serializer.data)




class ThresholdBasinsListCreateView(generics.ListAPIView):
    queryset = models.ThresholdBasins.objects.all()
    serializer_class = serializers.ThresholdBasinsSerializer

@api_view(['GET'])
def district_flood_alerts_observed_forecast_by_observed_dates(request, date):
    """
    Retrieves pre-calculated district flood alerts from the database.
    Attempts to fetch for the specified date and subsequent 6 days.
    If no data is available for this period, it falls back to the most recent
    available alert_date in the database and fetches 7 days from there.
    """
    requested_start_date = None
    try:
        requested_start_date = datetime.strptime(date, '%Y-%m-%d').date()
        logger.info(f"API request for flood alerts starting from: {requested_start_date}")
    except ValueError:
        logger.error(f"Invalid date format: {date}")
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD (e.g., 2025-07-08)."}, status=400)

    # Define the 7-day window based on the requested date
    # This is the initial period we will attempt to fetch data for
    initial_fetch_start_date = requested_start_date
    initial_fetch_end_date = requested_start_date + timedelta(days=6)

    # --- Attempt to fetch data for the requested 7-day period ---
    alerts_for_initial_period = models.DistrictFloodAlert.objects.filter(
        alert_date__range=(initial_fetch_start_date, initial_fetch_end_date)
    ).select_related('alert_type').order_by('alert_date', 'district_name')

    # Check if any data was found for the initial period
    if not alerts_for_initial_period.exists():
        logger.info(f"No data found for requested period ({initial_fetch_start_date} to {initial_fetch_end_date}). Initiating fallback.")

        # --- Fallback Plan: Find the most recent available alert_date ---
        latest_available_alert_date_agg = models.DistrictFloodAlert.objects.aggregate(Max('alert_date'))
        latest_available_date = latest_available_alert_date_agg['alert_date__max']

        if latest_available_date:
            # Adjust the start_date to the most recent available date
            final_start_date = latest_available_date
            logger.info(f"Falling back to most recent available date: {final_start_date}")

            # Re-fetch data based on the new, adjusted start_date
            final_end_date = final_start_date + timedelta(days=6)
            alerts_to_process = models.DistrictFloodAlert.objects.filter(
                alert_date__range=(final_start_date, final_end_date)
            ).select_related('alert_type').order_by('alert_date', 'district_name')

            if not alerts_to_process.exists():
                logger.warning(f"Even after fallback, no data found for period starting {final_start_date}.")
                return JsonResponse({"warning": "No historical data available in the system for any date."}, status=200)

        else:
            logger.warning("No flood alert data available in the database at all.")
            return JsonResponse({"warning": "No flood alert data available in the system for any date."}, status=200)
    else:
        # Data found for the requested period, so use it
        final_start_date = initial_fetch_start_date
        final_end_date = initial_fetch_end_date
        alerts_to_process = alerts_for_initial_period # Use the data already fetched

    # --- Organize and format the data for response ---
    organized_alerts = defaultdict(list)
    for alert in alerts_to_process:
        alert_data = {
            "district": alert.district_name,
            "alert_type": alert.alert_type.alert_type
        }
        organized_alerts[alert.alert_date].append(alert_data)

    result = []
    for day_offset in range(7):
        current_date = final_start_date + timedelta(days=day_offset)
        current_date_str = current_date.strftime('%Y-%m-%d')

        daily_alerts = organized_alerts.get(current_date, [])
        # Ensure sorting if it's not guaranteed by DB query (though it should be)
        daily_alerts = sorted(daily_alerts, key=lambda x: x['district'])

        result.append({
            "date": current_date_str,
            "alerts": daily_alerts
        })

    # Final check for empty result (shouldn't happen if previous checks are robust)
    if not result:
        logger.warning("Unexpected: Result is empty after processing alerts. Check logic.")
        return JsonResponse({"warning": "An unexpected issue occurred, no data to display."}, status=500)

    return Response(result)

# @api_view(['GET'])
# def district_flood_alerts_observed_forecast_by_observed_dates(request, date):
#     def calculate_flood_level(water_level, danger_level):
#         if danger_level is None or water_level is None or water_level < 0:
#             return "na"
#         elif water_level >= danger_level + 1:
#             return "severe"
#         elif water_level >= danger_level:
#             return "flood"
#         elif water_level >= danger_level - 0.5:
#             return "warning"
#         else:
#             return "normal"

#     # Parse and validate the date parameter (YYYY-MM-DD)
#     try:
#         start_date = datetime.strptime(date, '%Y-%m-%d').date()
#         logger.info(f"Processing flood alerts for start date: {start_date}")
#     except ValueError:
#         logger.error(f"Invalid date format: {date}")
#         return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD (e.g., 2025-07-02)."}, status=400)

#     # Fetch stations with valid district and danger level
#     stations = models.Station.objects.filter(
#         district__isnull=False,
#         danger_level__isnull=False,
#         station_id__isnull=False
#     ).exclude(
#         district=''
#     ).values('station_id', 'name', 'district', 'danger_level')

#     if not stations:
#         logger.error("No valid station data found with non-null district and danger_level")
#         return JsonResponse({"error": "No valid station data found."}, status=500)

#     logger.info(f"Found {len(stations)} valid stations")

#     # Get the latest forecast date
#     latest_forecast = models.WaterLevelForecast.objects.aggregate(Max('forecast_date'))
#     latest_forecast_date = latest_forecast['forecast_date__max']
#     logger.info(f"Latest forecast date: {latest_forecast_date}")

#     # Initialize result list
#     result = []

#     # Determine how many forecast days are available
#     max_days = 7  # 1 observed + 6 forecasted
#     if latest_forecast_date:
#         forecast_end_date = latest_forecast_date.date()
#         forecast_start_date = start_date + timedelta(days=1)
#         days_available = (forecast_end_date - forecast_start_date).days + 1
#         max_forecast_days = min(6, max(0, days_available))
#         max_days = min(max_days, 1 + max_forecast_days)
#     else:
#         max_days = 1  # Only observed data if no forecasts
#         logger.warning("No forecast data available, limiting to observed data")

#     # Process up to 7 days: Day 0 (observed), Days 1-6 (forecasted if available)
#     for day_offset in range(max_days):
#         current_date = start_date + timedelta(days=day_offset)
#         day_start = datetime.combine(current_date, datetime.min.time())
#         day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
#         print(f"Processing day {day_offset}: {day_start} to {day_end}")
#         logger.debug(f"Processing day {day_offset}: {day_start} to {day_end}")

#         # Initialize district alerts
#         district_alerts = defaultdict(lambda: {"severe": 0, "flood": 0, "warning": 0, "normal": 0, "na": 0})

#         # Get data: observed for day 0, forecasted for days 1-6
#         if day_offset == 0:
#             try:
#                 latest_data = models.WaterLevelObservation.objects.filter(
#                     observation_date__range=(day_start, day_end),
#                     station_id__isnull=False,
#                     station_id__station_id__in=[s['station_id'] for s in stations]
#                 ).values('station_id__station_id').annotate(
#                     max_waterlevel=Max('water_level')
#                 ).values('station_id__station_id', 'max_waterlevel')

#                 if not latest_data:
#                     logger.warning(f"No observed data for {day_start}, trying previous day")
#                     day_start -= timedelta(days=1)
#                     day_end -= timedelta(days=1)
#                     latest_data = models.WaterLevelObservation.objects.filter(
#                         observation_date__range=(day_start, day_end),
#                         station_id__isnull=False,
#                         station_id__station_id__in=[s['station_id'] for s in stations]
#                     ).values('station_id__station_id').annotate(
#                         max_waterlevel=Max('water_level')
#                     ).values('station_id__station_id', 'max_waterlevel')
#             except Exception as e:
#                 logger.error(f"Error fetching observed data: {str(e)}")
#                 latest_data = []
#         else:
#             latest_data = models.WaterLevelForecast.objects.filter(
#                 forecast_date__range=(day_start, day_end),
#                 station_id__isnull=False,
#                 station_id__station_id__in=[s['station_id'] for s in stations]
#             ).values('station_id__station_id').annotate(
#                 max_waterlevel=Max('water_level')
#             ).values('station_id__station_id', 'max_waterlevel')

#         logger.info(f"Found {len(latest_data)} data records for {current_date}")

#         # Convert data to a dictionary for quick lookup
#         data_dict = {item['station_id__station_id']: item for item in latest_data}

#         # Process stations
#         for station in stations:
#             station_id = station['station_id']
#             district_name = station['district'].lower().strip()
#             if not district_name:
#                 continue

#             if station_id in data_dict:
#                 data = data_dict[station_id]
#                 try:
#                     water_level = float(data['max_waterlevel'])
#                     danger_level = float(station['danger_level'])
#                     flood_level = calculate_flood_level(water_level, danger_level)
#                     district_alerts[district_name][flood_level] += 1
#                 except (ValueError, TypeError) as e:
#                     logger.debug(f"Invalid data for station {station_id}: {str(e)}")
#                     district_alerts[district_name]["na"] += 1
#             else:
#                 district_alerts[district_name]["na"] += 1

#         # Determine primary alert type per district
#         daily_alerts = []
#         for district, levels in district_alerts.items():
#             max_level = "na"
#             for level in ["severe", "flood", "warning", "normal"]:
#                 if levels[level] > 0:
#                     max_level = level
#                     break
#             daily_alerts.append({
#                 "district": district.capitalize(),
#                 "alert_type": FLOOD_LEVELS[max_level],
#             })

#         # Sort daily alerts by district name
#         daily_alerts = sorted(daily_alerts, key=lambda x: x['district'])

#         # Add to result
#         result.append({
#             "date": current_date.strftime('%Y-%m-%d'),
#             "alerts": daily_alerts
#         })

#     if not result:
#         logger.warning("No data available for the specified period")
#         return JsonResponse({"warning": "No data available for the specified period"}, status=200)

#     return JsonResponse(result, safe=False)






@api_view(['GET'])
def MonsoonFlashFlood(request,**kwargs):

    forecast_date = kwargs['forecast_date']
    basin_id = kwargs['basin_id']

    latest_record = models.MonsoonBasinWiseFlashFloodForecast.objects.latest('prediction_date')
    latest_date = latest_record.prediction_date  # Access the date field

    first_query =  models.MonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
    
    if not first_query.exists():
        forecast_date = latest_date
        second_query =  models.MonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
        forecasts = second_query
    else:
        forecasts = first_query


    # Initialize the response structure
    response_data = {

        "Hours": {
            "0": 24,
            "1": 48,
            "2": 72,
            "3": 120,
            "4": 168,
            "5": 240
        },

        "Threshold": defaultdict(float),
    }

    threshold_list=[]

    date_value_dict = defaultdict(list)
    # Populate the response data with values from the database
    for forecast in forecasts:
        threshold_list.append(round(forecast.thresholds,2))
        date_value_dict[forecast.date].append(round(forecast.value,2))
 
    # Convert defaultdict to regular dict
    threshold_dict={}
    for i,threshold in enumerate(sorted(set(threshold_list))):threshold_dict[str(i)]=threshold
    response_data["Threshold"] = threshold_dict
  
    for key in date_value_dict.keys():
        string_date = key.strftime("%Y-%m-%d")
        response_data[string_date] = {str(i): value for i, value in enumerate(date_value_dict[key])}

    return Response(response_data)

def get_latest_prediction_date(basin_id):

    latest_date_qs = models.BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.filter(
        basin_id=basin_id
    ).aggregate(Max('prediction_date'))
    
    return latest_date_qs.get('prediction_date__max')


@api_view(['GET'])
def BMDWRFMonsoonFlashFlood(request, **kwargs):
    """
    Retrieves BMD WRF flash flood forecast data for the requested prediction_date and basin_id.
    If no data is found for the requested date, it falls back to the latest available 
    prediction_date in the database for the given basin_id.
    """

    requested_forecast_date_str = kwargs.get('forecast_date')
    requested_basin_id = kwargs.get('basin_id')
    
    # Define a variable to hold the date that is actually used for the query
    forecast_date_to_use = None
    
    # Convert the requested date string to a date object
    try:
        requested_date = datetime.strptime(requested_forecast_date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)


    # --- 1. Query Data with Fallback Logic ---
    
    # A. First, try the requested date
    forecasts = models.BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.filter(
        prediction_date=requested_date, 
        basin_id=requested_basin_id
    ).order_by('date', 'hours')

    if forecasts.exists():
        forecast_date_to_use = requested_date
    else:
        # B. If no data for requested date, find the last available date and retry
        latest_available_date = get_latest_prediction_date(requested_basin_id)
        
        if latest_available_date:
            forecasts = models.BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.filter(
                prediction_date=latest_available_date, 
                basin_id=requested_basin_id
            ).order_by('date', 'hours')
            
            if forecasts.exists():
                forecast_date_to_use = latest_available_date
                # Optionally add a message to the response indicating the fallback
                # print(f"Fallback: Using data from {latest_available_date} instead of {requested_date}")
            else:
                # This should ideally not happen if get_latest_prediction_date is correct
                pass 
    
    
    if not forecasts.exists():
        # Fallback failed, no data found at all for the basin
        return Response({
            "error": (f"No BMDWRF forecast data found for Basin ID {requested_basin_id} "
                      f"on requested date {requested_forecast_date_str} or the latest available date.")
        }, status=404)
    

    # --- 2. Restructure Data ---
    
    # The date actually used for the successful query is now in forecast_date_to_use
    
    response_data = {
        "Hours": {
            "0": 24, "1": 48, "2": 72, 
            "3": 120, "4": 168, "5": 240
        },
        "Threshold": defaultdict(float),
        # Report the date that was actually used
        # "prediction_date_used": forecast_date_to_use.strftime("%Y-%m-%d") 
    }

    threshold_list = []
    date_value_dict = defaultdict(list)
    
    for forecast in forecasts:
        threshold_list.append(forecast.thresholds)
        date_value_dict[forecast.date].append(forecast.value)

    # Populate the "Threshold" object 
    threshold_dict = {}
    for i, threshold in enumerate(sorted(list(set(threshold_list)))):
        threshold_dict[str(i)] = round(threshold, 0)

    response_data["Threshold"] = threshold_dict
  
    # Populate the date keys with indexed values
    for key in date_value_dict.keys():
        string_date = key.strftime("%Y-%m-%d")
        response_data[string_date] = {str(i): value for i, value in enumerate(date_value_dict[key])}

    return Response(response_data)




@api_view(['GET'])
def UkMetMonsoonFlashFlood(request,**kwargs):

    forecast_date = kwargs['forecast_date']
    basin_id = kwargs['basin_id']

    latest_record = models.UKMetMonsoonBasinWiseFlashFloodForecast.objects.latest('prediction_date')
    latest_date = latest_record.prediction_date  # Access the date field

    first_query =  models.UKMetMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
    
    if not first_query.exists():
        forecast_date = latest_date
        second_query =  models.UKMetMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
        forecasts = second_query
    else:
        forecasts = first_query


    # Initialize the response structure
    response_data = {

        "Hours": {
            "0": 24,
            "1": 48,
            "2": 72,
            "3": 120,
            "4": 168,
            "5": 240
        },

        "Threshold": defaultdict(float),
    }

    threshold_list=[]

    date_value_dict = defaultdict(list)
    # Populate the response data with values from the database
    for forecast in forecasts:
        threshold_list.append(forecast.thresholds)
        date_value_dict[forecast.date].append(forecast.value)
 
    # Convert defaultdict to regular dict
    threshold_dict={}
    for i,threshold in enumerate(sorted(set(threshold_list))):threshold_dict[str(i)]=threshold
    response_data["Threshold"] = threshold_dict
  
    for key in date_value_dict.keys():
        string_date = key.strftime("%Y-%m-%d")
        response_data[string_date] = {str(i): value for i, value in enumerate(date_value_dict[key])}

    return Response(response_data)

@api_view(['GET'])
def MonsoonProbabilisticFlashFlood(request,**kwargs):

    forecast_date = kwargs['givenDate']
    basin_id = kwargs['basin_id']

    latest_record = models.MonsoonProbabilisticFlashFloodForecast.objects.latest('prediction_date')
    latest_date = latest_record.prediction_date  # Access the date field

    first_query =  models.MonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
    
    if not first_query.exists():
        forecast_date = latest_date
        second_query =  models.MonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
        forecasts = second_query
    else:
        forecasts = first_query


    # Initialize the response structure
    response_data = {

        "Hours": {
            "0": 24,
            "1": 48,
            "2": 72,
            "3": 120,
            "4": 168,
            "5": 240
        },

        "Thresholds": defaultdict(float),
    }

    threshold_list=[]

    date_value_dict = defaultdict(list)
    # Populate the response data with values from the database
    for forecast in forecasts:
        threshold_list.append(round(forecast.thresholds,2))
        date_value_dict[forecast.date].append(round(forecast.value,2))
 
    # Convert defaultdict to regular dict
    threshold_dict={}
    for i,threshold in enumerate(sorted(set(threshold_list))):threshold_dict[str(i)]=threshold
    response_data["Thresholds"] = threshold_dict
  
    for key in list(date_value_dict.keys())[:-1]:
        string_date = key.strftime("%Y-%m-%d")
        response_data[string_date] = {str(i): value for i, value in enumerate(date_value_dict[key])}

    return Response(response_data)

@api_view(['GET'])
def UKMetMonsoonProbabilisticFlashFlood(request,**kwargs):

    forecast_date = kwargs['givenDate']
    basin_id = kwargs['basin_id']

    latest_record = models.UKMetMonsoonProbabilisticFlashFloodForecast.objects.latest('prediction_date')
    latest_date = latest_record.prediction_date  # Access the date field

    first_query =  models.UKMetMonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
    
    if not first_query.exists():
        forecast_date = latest_date
        second_query =  models.UKMetMonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=forecast_date, basin_id=basin_id)
        forecasts = second_query
    else:
        forecasts = first_query


    # Initialize the response structure
    response_data = {

        "Hours": {
            "0": 24,
            "1": 48,
            "2": 72,
            "3": 120,
            "4": 168,
            "5": 240
        },

        "Thresholds": defaultdict(float),
    }

    threshold_list=[]

    date_value_dict = defaultdict(list)
    # Populate the response data with values from the database
    for forecast in forecasts:
        threshold_list.append(forecast.thresholds)
        date_value_dict[forecast.date].append(forecast.value)
 
    # Convert defaultdict to regular dict
    threshold_dict={}
    for i,threshold in enumerate(sorted(set(threshold_list))):threshold_dict[str(i)]=threshold
    response_data["Thresholds"] = threshold_dict
  
    for key in list(date_value_dict.keys())[:-1]:
        string_date = key.strftime("%Y-%m-%d")
        response_data[string_date] = {str(i): value for i, value in enumerate(date_value_dict[key])}

    return Response(response_data)



from data_load.models import FloodSummaryReport
from data_load.flood_summary_generator_utils import generate_flood_summary_data 

@api_view(['GET']) 
@require_GET 
def flood_summary_view(request):

    target_date_str = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))
    target_date_obj = None

    try:
        target_date_obj = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        logger.error(f"Invalid date format requested: {target_date_str}")
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    try:
        # Attempt to retrieve the report from the database
        summary_report = FloodSummaryReport.objects.get(report_date=target_date_obj)
        logger.info(f"Flood summary report for {target_date_str} retrieved from DB.")
        return JsonResponse(summary_report.summary_data, safe=False)

    except FloodSummaryReport.DoesNotExist:
        # If the report does not exist, generate it
        logger.info(f"Flood summary report for {target_date_str} not found in DB. Attempting to generate...")
        try:
            # Call the generation function (this should now use direct DB calls)
            generated_data = generate_flood_summary_data(target_date_str)

            if "error" in generated_data:
                logger.error(f"Error during on-demand generation for {target_date_str}: {generated_data['error']}")
                return JsonResponse({"error": generated_data['error']}, status=generated_data.get('status', 500))

            # Store the newly generated report in the database
            FloodSummaryReport.objects.create(
                report_date=target_date_obj,
                summary_data=generated_data,
                # processing_time might be calculated inside generate_flood_summary_data
                # if you return it as part of the data or track it separately.
                # For simplicity, we assume generate_flood_summary_data returns the final dict.
            )
            logger.info(f"Flood summary report for {target_date_str} successfully generated and stored.")
            return JsonResponse(generated_data, safe=False)

        except Exception as e:
            logger.exception(f"Unexpected error during on-demand generation for {target_date_str}")
            return JsonResponse({"error": f"An unexpected error occurred during report generation: {str(e)}"}, status=500)




from django.http import JsonResponse, Http404
from django.views.decorators.cache import cache_page
from datetime import datetime
from .models import FloodReport

@cache_page(60 * 60)  # Cache for 1 hour
@api_view(['GET'])
def flood_monitoring_report(request):
    # Get target date from query parameter or use today
    target_date = request.GET.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        report = FloodReport.objects.get(report_date=target_date)
        return JsonResponse(report.report_data)
    except FloodReport.DoesNotExist:
        raise Http404(f"No flood report available for {target_date}")




#  Transboundary Moduels VIEWs

from userauth.serializers import UserAuthProfileStationsSerializer,UserAuthProfileIndianStationsSerializer
from userauth.models import UserAuthProfileStations,UserAuthProfileIndianStations


class InsertUserStationView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserAuthProfileStationsSerializer

class InsertUserIndianStationView(generics.CreateAPIView):
  permission_classes = (AllowAny,)
  serializer_class = UserAuthProfileIndianStationsSerializer


@api_view(['GET'])
def DeleteProfileID(request,**kwargs):

    profile_id = kwargs['profile_id']
    station_id = kwargs['station_id']

    queryset= UserAuthProfileStations.objects\
    .filter(profile_id=profile_id)\
    .filter(station_id=station_id)\
    .values()[0]

    # context={"id":queryset}

    return Response(queryset["id"])

@api_view(['DELETE'])
def deleteProfileStationsByUserId(request,pk):

    id=int(pk)
    try:
        instance = UserAuthProfileStations.objects.get(id=id)
        instance.delete()
        return Response({'Status':'Deleted'})
    except instance.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)



@api_view(['GET'])
def DeleteIndianProfileID(request,**kwargs):

    profile_id = kwargs['profile_id']
    station_id = kwargs['station_id']

    queryset= UserAuthProfileIndianStations.objects\
    .filter(profile_id=profile_id)\
    .filter(indianstations_id=station_id)\
    .values()[0]

    # context={"id":queryset}

    return Response(queryset["id"])

@api_view(['DELETE'])
def deleteProfileIndianStationsByUserId(request,pk):

    id=int(pk)
    try:
        instance = UserAuthProfileIndianStations.objects.get(id=id)
        instance.delete()
        return Response({'Status':'Deleted'})
    except instance.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


from .serializers import FloodmapsSerializer
def floodmaps_data(request):
    floodmaps = models.Floodmaps.objects.all()
    # serializer = FloodmapsSerializer(floodmaps, many=True)
    serializer = FloodmapsSerializer(floodmaps, many=True,context={'request': request})
    return JsonResponse(serializer.data, safe=False)




class monsoonConfigViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = models.MonsoonConfig.objects.all()
    serializer_class = serializers.MonsoonConfigSerializer
    
    
    
    
    

"""
#######################################################################################
### ADDED BY: SHAIF    | DATE: 2025-08-13
### REQUESTED BY: JOBAYER
#######################################################################################
"""
# class observedRainfallViewSet(viewsets.ReadOnlyModelViewSet):

#     serializer_class = rainfallObservationSerializer

#     def get_queryset(self):

#         today = datetime.now()
#         current_month = today.month
#         current_year = today.year
#         latest_dates_subquery = RainfallObservations.objects.filter(
#             rf_date__year=current_year,
#             rf_date__month=current_month,
#             rf_date__lte=today # Only up to the current day
#         ).values('st_id').annotate(
#             latest_rf_date=Max('rf_date')
#         )

#         st_id_latest_date_pairs = [(entry['st_id'], entry['latest_rf_date']) for entry in latest_dates_subquery]


#         queryset = RainfallObservations.objects.filter(
#             rf_date__year=current_year,
#             rf_date__month=current_month,
#             rf_date__lte=today # Only up to the current day
#         ).values('st_id').annotate(
#             total_rainfall=Sum('rainfall')
#         ).order_by('st_id') # Order by station ID


#         return queryset


#     # def observedRainfallByDate(self, request, **kwargs):

#     #     startDate = self.kwargs.get('startDate')

#     #     if not startDate:
#     #         return Response({"error": "startDate parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        
#     #     startDate = startDate + 'T06:00:00Z'

#     #     # Parse and validate the date
#     #     try:
#     #         lastUpdateDateTime = datetime.strptime(startDate, "%Y-%m-%dT%H:%M:%SZ")
#     #         lastUpdateDateTime = timezone.make_aware(lastUpdateDateTime) if timezone.is_naive(lastUpdateDateTime) else lastUpdateDateTime
#     #     except ValueError:
#     #         return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        
#     #     print('Last Update Date Time in Rainfall Observation: ', lastUpdateDateTime)
#     #     # Get all stations (ensure no duplicates)
#     #     stationListQueryset = FfwcRainfallStations.objects.distinct()

#     #     # Get rainfall observations for the specific date
#     #     rainfall_queryset = RainfallObservations.objects.filter(rf_date=lastUpdateDateTime)
        
#     #     # Create a dictionary of rainfall data (ensure unique st_id)
#     #     rainfall_dict = {obs.st_id: float(obs.rainfall) for obs in rainfall_queryset}
        

#     #     stations_new_dict = {station.id: station for station in FfwcRainfallStationsNew.objects.all()}
#     #     stations_2025_dict = {station.id: station for station in FfwcRainfallStations2025.objects.all()}
#     #     stations_dict = {station.id: station for station in FfwcRainfallStations.objects.all()}


#     #     # Prepare response data including all stations
#     #     response_data = []
#     #     seen_st_ids = set()  # Track unique st_id to avoid duplicates
#     #     for station in stationListQueryset:
#     #         # Skip stations not in FfwcRainfallStationsNew or already processed
#     #         if not FfwcRainfallStationsNew.objects.filter(id=station.id).exists() or station.id in seen_st_ids:
#     #             continue
#     #         seen_st_ids.add(station.id)
#     #         station_2025 = stations_2025_dict.get(station.id)
#     #         station_id = station_2025.st_id if station_2025 else None

#     #         response_data.append({
#     #             'st_id': station.id,
#     #             'station_id': station_id,  # Include station_id in response_data
#     #             'rf_date': lastUpdateDateTime.isoformat(),
#     #             'rainfall': rainfall_dict.get(station.id, -9999.0),
#     #             'name': None,
#     #             'basin_order': None,
#     #             'basin': None,
#     #             'division': None,
#     #             'district': None,
#     #             'upazilla': None,
#     #             'lat': None,
#     #             'long': None,
#     #             'status': None,
#     #             'normal_rainfall': None,
#     #             'max_rainfall': None
#     #         })
        
#     #     # Serialize the data
#     #     serializer = rainfallObservationByDateSerializer(data=response_data, many=True)
#     #     if serializer.is_valid():
#     #         return Response(serializer.data)
#     #     else:
#     #         print("Serializer errors:", serializer.errors)
#     #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#     def observedRainfallByDate(self, request, **kwargs):

#         startDate = self.kwargs.get('startDate')

#         if not startDate:
#             return Response({"error": "startDate parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        
#         startDate_str = startDate + 'T06:00:00Z'

#         # Parse and validate the date
#         try:
#             lastUpdateDateTime = datetime.strptime(startDate_str, "%Y-%m-%dT%H:%M:%SZ")
#             lastUpdateDateTime = timezone.make_aware(lastUpdateDateTime) if timezone.is_naive(lastUpdateDateTime) else lastUpdateDateTime
#         except ValueError:
#             return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        
#         print('Initial Last Update Date Time in Rainfall Observation: ', lastUpdateDateTime)
        
#         # --- Bulk Fallback Logic Start ---
#         max_fallback_attempts = 2 # Try today and one previous day
#         current_date_to_check = lastUpdateDateTime
        
#         for attempt in range(max_fallback_attempts):
#             rainfall_queryset = RainfallObservations.objects.filter(rf_date=current_date_to_check)
            
#             # Check if there are any observations at all
#             if rainfall_queryset.exists():
#                 # A more robust check: see if a significant portion of observations are valid
#                 # For simplicity, we'll consider it "exists" if any record is found.
#                 # You might want to refine this, e.g., if less than X% of stations have data.
#                 print(f"Found rainfall data for {current_date_to_check.isoformat()}.")
#                 lastUpdateDateTime = current_date_to_check # Update the actual date used
#                 break # Exit the loop, we found data
#             else:
#                 print(f"No rainfall data found for {current_date_to_check.isoformat()}. Falling back to previous day.")
#                 current_date_to_check -= timedelta(days=1)
#         else:
#             # This block executes if the loop completes without a 'break'
#             print("Could not find rainfall data even after fallback attempts. Using the initial date.")
#             # lastUpdateDateTime retains its initial value, and rainfall_queryset will be empty
#             # The individual station loop will then assign -9999.0 to all.
#         # --- Bulk Fallback Logic End ---
        
#         print('Final Last Update Date Time being used: ', lastUpdateDateTime)

#         # Get rainfall observations for the determined date
#         # rainfall_queryset is already populated by the fallback loop
#         rainfall_dict = {obs.st_id: float(obs.rainfall) for obs in rainfall_queryset}
        
#         # Get all stations (ensure no duplicates)
#         stationListQueryset = FfwcRainfallStations.objects.distinct()

#         stations_new_dict = {station.id: station for station in FfwcRainfallStationsNew.objects.all()}
#         stations_2025_dict = {station.id: station for station in FfwcRainfallStations2025.objects.all()}

#         # Prepare response data including all stations
#         response_data = []
#         seen_st_ids = set()  # Track unique st_id to avoid duplicates

#         for station in stationListQueryset:
#             # Skip stations not in FfwcRainfallStationsNew or already processed
#             if not FfwcRainfallStationsNew.objects.filter(id=station.id).exists() or station.id in seen_st_ids:
#                 continue
#             seen_st_ids.add(station.id)
            
#             station_2025 = stations_2025_dict.get(station.id)
#             station_id = station_2025.st_id if station_2025 else None

#             # Get rainfall from the rainfall_dict (which is for the chosen day after fallback)
#             current_day_rainfall = rainfall_dict.get(station.id, -9999.0)

#             response_data.append({
#                 'st_id': station.id,
#                 'station_id': station_id,
#                 'rf_date': lastUpdateDateTime.isoformat(), # This will now reflect the *actual* date used
#                 'rainfall': current_day_rainfall,
#                 'name': None, 
#                 'basin_order': None,
#                 'basin': None,
#                 'division': None,
#                 'district': None,
#                 'upazilla': None,
#                 'lat': None,
#                 'long': None,
#                 'status': None,
#                 'normal_rainfall': None,
#                 'max_rainfall': None
#             })
        
#         # Serialize the data
#         serializer = rainfallObservationByDateSerializer(data=response_data, many=True)
#         if serializer.is_valid():
#             return Response(serializer.data)
#         else:
#             print("Serializer errors:", serializer.errors)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def rainfallByStation(self,request,**kwargs):

#         print('In Rainfall by Station .. ')
#         stationId=self.kwargs['st_id']

#         entryDate = datetime.strptime(entryDateTimeString,'%Y-%m-%dT%H:%M:%SZ').replace(hour=6)
#         print('Entry Date in Rainfall By Station: ', entryDate)

#         latest_record = RainfallObservations.objects.filter(st_id=stationId).latest('rf_date')
#         print('Latest Rainfall Record :', latest_record.rf_date)
#         entryDate = latest_record.rf_date

#         queryset = RainfallObservations.objects.filter(
#             st_id=stationId,rf_date__gte=entryDate-timedelta(days=40)
#             ).order_by('-rf_date')
#         # queryset = WaterLevelForecasts.objects.filter(st_id=stationId,fc_date__gte=databaseTime)
        
#         serializer= threeDaysObservedRainfallSerializer(queryset,many=True)
        
#         return Response(serializer.data)

#     def rainfallByStationAndDate(self,request,**kwargs):

#         print(' . . In Rainfall by Station And Date . . ')
#         stationId=self.kwargs['st_id']
#         startDate=self.kwargs['startDate']
#         startDate=startDate+'T06:00:00Z'
        
#         # getLastUpdateTime=RainfallObservations.objects.filter(st_id=1).order_by('-rf_date').values_list('rf_date',flat=True)[0]
#         # lastUpdateDateTime=datetime.strftime(getLastUpdateTime,"%Y-%m-%dT%H:%M:%SZ")
#         lastUpdateDateTime= datetime.strptime(startDate,"%Y-%m-%dT%H:%M:%SZ")-timedelta(days=3) 

#         # hourPart=datetime.strptime(lastUpdateDateTime,"%Y-%m-%dT%H:%M:%SZ").time()
#         # databaseTime=datetime.strptime(lastUpdateDateTime,"%Y-%m-%dT%H:%M:%SZ")
#         # queryDate= datetime.combine(date.today(), hourPart)

#         # queryset = RainfallObservations.objects.filter(
#         #     st_id=stationId,
#         #     rf_date__gte=lastUpdateDateTime-timedelta(days=40)
#         #     ).filter(rf_date__lte=lastUpdateDateTime-timedelta(days=0))

#         queryset = RainfallObservations.objects.filter(
#             st_id=stationId,
#             rf_date__gte=lastUpdateDateTime
#             ).filter(rf_date__lte=lastUpdateDateTime+timedelta(days=3))
        
#         serializer= threeDaysObservedRainfallSerializer(queryset,many=True)
        
#         return Response(serializer.data)

#     def fourtyDaysRainfallByStationAndDate(self,request,**kwargs):

#         print(' . . In Rainfall by Station And Date . . ')
#         stationId=self.kwargs['st_id']
#         startDate=self.kwargs['startDate']
#         startDate=startDate+'T06:00:00Z'
        
#         # getLastUpdateTime=RainfallObservations.objects.filter(st_id=1).order_by('-rf_date').values_list('rf_date',flat=True)[0]
#         # lastUpdateDateTime=datetime.strftime(getLastUpdateTime,"%Y-%m-%dT%H:%M:%SZ")
#         lastUpdateDateTime= datetime.strptime(startDate,"%Y-%m-%dT%H:%M:%SZ")
#         previousDateBeforeFourtyDays =lastUpdateDateTime -timedelta(days=40)
#         print('Last Update Date Time in Observed Rainfall .. ', lastUpdateDateTime)

#         # hourPart=datetime.strptime(lastUpdateDateTime,"%Y-%m-%dT%H:%M:%SZ").time()
#         # databaseTime=datetime.strptime(lastUpdateDateTime,"%Y-%m-%dT%H:%M:%SZ")
#         # queryDate= datetime.combine(date.today(), hourPart)

#         queryset = RainfallObservations.objects.filter(
#             st_id=stationId,
#             rf_date__gte=previousDateBeforeFourtyDays
#             ).filter(rf_date__lte=lastUpdateDateTime)
        
#         serializer= threeDaysObservedRainfallSerializer(queryset,many=True)
        
#         return Response(serializer.data)

    
#     def rainfallSumByStationAndYear(self,request,**kwargs):

#         stationId=self.kwargs['st_id']
#         year=int(self.kwargs['year'])
#         months=[4,5,6,7,8,9,10]
        
#         rainfallDict={}

#         for month in months:

#             queryset= RainfallObservations.objects\
#             .filter(st_id=stationId)\
#             .filter(rf_date__year__gte=year,rf_date__month__gte=month)\
#             .filter(rf_date__year__lte=year,rf_date__month__lte=month)\
#             .aggregate(Avg("rainfall"))

#             rainfallDict[month]=queryset

#         return JsonResponse(rainfallDict,safe=False)

    
#     def rainfallAvgByStationAndYear(self,request,**kwargs):

#         stationId=self.kwargs['st_id']
#         year=int(self.kwargs['year'])
#         months=[4,5,6,7,8,9,10]
        
#         rainfallDict={}

#         for month in months:

#             queryset= RainfallObservations.objects\
#             .filter(st_id=stationId)\
#             .filter(rf_date__year__gte=year,rf_date__month__gte=month)\
#             .filter(rf_date__year__lte=year,rf_date__month__lte=month)\
#             .aggregate(Max("rainfall"))

#             rainfallDict[month]=queryset

#         return JsonResponse(rainfallDict,safe=False)



# rainfall_sum_by_station_and_year=observedRainfallViewSet.as_view({'get':'rainfallSumByStationAndYear'})



"""
#######################################################################################
### ADDED BY: SHAIF | DATE: 2025-08-14
### ASSIGNED BY: SAJIB BHAI
#######################################################################################
"""
class FfwcStations2025ListViewsAPIs(generics.ListAPIView):     # ListCreateAPIView
    queryset = Station.objects.all().order_by('station_serial_no')
    serializer_class = FfwcStations2025Serializer
    permission_classes = [IsAuthenticated,]  # Ensure only authenticated users can update
    
    
class StationUpdateView(generics.UpdateAPIView):
    queryset = Station.objects.all()
    serializer_class = FfwcStations2025UpdateSerializer
    lookup_field = 'station_id'
    permission_classes = [IsAuthenticated,]  # Ensure only authenticated users can update

    def put(self, request, *args, **kwargs): 
        instance = self.get_object()
        
        # print(' ##### data: ', request.data)
        
        # Partial update allowed - only station_serial_number is updated
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    

# class FfwcStations2025BulkUpdateView(APIView):
#     permission_classes = [IsAuthenticated,]  # Ensure only authenticated users can update
    
#     def put(self, request, *args, **kwargs): 
#         # print(" ##### data: ", request.data)
        
#         if not isinstance(request.data, list):
#             return Response(
#                 {"error": "Expected a list of items"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         updated_count = 0
#         errors = []
        
#         for item in request.data: 
#             if 'web_id' not in item or 'station_serial_no' not in item:
#                 errors.append({
#                     "item": item,
#                     "error": "Both 'web_id' and 'station_serial_no' are required"
#                 })
#                 continue
            
#             try: 
#                 station = get_object_or_404(Station, station_id=item['web_id']) 
#                 station.station_serial_no = item['station_serial_no']
#                 station.save()
#                 updated_count += 1
#             except Exception as e:
#                 errors.append({
#                     "item": item,
#                     "error": str(e)
#                 })
        
#         if errors:
#             return Response({
#                 "message": f"Updated {updated_count} stations, {len(errors)} failed",
#                 "errors": errors
#             }, status=status.HTTP_207_MULTI_STATUS)
            
#         return Response({
#             "message": f"Successfully updated {updated_count} stations"
#         }, status=status.HTTP_200_OK)



class FfwcStations2025BulkUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            return Response({"error": "Expected a list of items"}, status=400)

        updated_count = 0
        errors = []

        for item in request.data:
            if 'web_id' not in item or 'station_serial_no' not in item:
                errors.append({"item": item, "error": "Missing fields"})
                continue
            
            try:
                updated = Station.objects.filter(
                    station_id=item['web_id']
                ).update(station_serial_no=item['station_serial_no'])
                
                if updated == 0:
                    errors.append({"item": item, "error": "Station not found"})
                else:
                    updated_count += 1
            except Exception as e:
                errors.append({"item": item, "error": str(e)})
        
        if errors:
            return Response({
                "message": f"Updated {updated_count}, failed {len(errors)}",
                "errors": errors
            }, status=207)
        
        return Response({"message": f"Updated {updated_count} stations"}, status=200)



from data_load.models import BulletinRelatedManue
from data_load.serializers import BulletinRelatedManueSerializer
class BulletinRelatedManueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Bulletins to be viewed.
    """
    queryset = BulletinRelatedManue.objects.all().order_by('id')
    serializer_class = BulletinRelatedManueSerializer



from .serializers import ScheduledTaskSerializer,ScheduledTaskToggleSerializer
from .models import ScheduledTask

class ScheduledTaskListView(generics.ListAPIView):

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer


class ScheduledTaskCreateView(generics.CreateAPIView):

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsAuthenticated]

class ScheduledTaskUpdateView(generics.UpdateAPIView):

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsAuthenticated]

class ScheduledTaskToggleView(generics.UpdateAPIView):

    queryset = ScheduledTask.objects.all()
    # Use the new, specialized serializer
    serializer_class = ScheduledTaskToggleSerializer
    # permission_classes = [IsAuthenticated]
    
    # Optional but recommended: Restrict to PATCH method only
    http_method_names = ['patch']



from .models import DistrictFloodAlertAutoUpdate
from .serializers import DistrictFloodAlertAutoUpdateSerializer, DistrictFloodAlertAutoUpdateStatusSerializer

class DistrictFloodAlertListView(generics.ListAPIView):
    """
    API view to list all flood alert auto-update statuses for districts.
    """
    queryset = DistrictFloodAlertAutoUpdate.objects.all()
    serializer_class = DistrictFloodAlertAutoUpdateSerializer



class UpdateDistrictAutoUpdateView(APIView):
    # Add these two lines to bypass all security checks for this view
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, district_name, *args, **kwargs):
        # ... your existing code for the post method remains the same
        try:
            district = DistrictFloodAlertAutoUpdate.objects.get(district_name__iexact=district_name)
        except DistrictFloodAlertAutoUpdate.DoesNotExist:
            return Response(
                {"error": "District not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        payload_serializer = DistrictFloodAlertAutoUpdateStatusSerializer(data=request.data)
        if not payload_serializer.is_valid():
            return Response(
                payload_serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_status = payload_serializer.validated_data['auto_update']

        district.auto_update = new_status
        district.save()

        response_serializer = DistrictFloodAlertAutoUpdateStatusSerializer(district)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


from rest_framework import generics
from .models import JsonEntry
from .serializers import JsonEntrySerializer
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# NEW: This view ONLY handles listing all entries (GET)
class JsonEntryListView(generics.ListAPIView):
    queryset = JsonEntry.objects.all()
    serializer_class = JsonEntrySerializer

# NEW: This view ONLY handles creating a new entry (POST)
@method_decorator(csrf_exempt, name='dispatch')
class JsonEntryCreateView(generics.CreateAPIView):
    queryset = JsonEntry.objects.all()
    serializer_class = JsonEntrySerializer

# This view for individual items remains the same
class JsonEntryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JsonEntry.objects.all()
    serializer_class = JsonEntrySerializer


from django.conf import settings
from typing import Optional

RELATIVE_DATA_PATH = 'assets/csv' 
def find_latest_valid_ensemble_date(base_dir: str, station_name: str, max_days_back: int = 30) -> Optional[datetime]:

    current_date = datetime.now()
    
    # Filename is constant, regardless of the date folder
    ensemble_file_name = f'all_en_corr_{station_name}.csv' 
    
    for i in range(max_days_back + 1):
        target_date = current_date - timedelta(days=i)
        date_folder = target_date.strftime('%Y%m%d')

        input_file_path = os.path.join(base_dir, date_folder, ensemble_file_name)
        
        if os.path.isdir(os.path.join(base_dir, date_folder)) and os.path.exists(input_file_path):
            return target_date  
            
    return None # No valid file found within the search range


def get_ensemble_percentiles_json(request):

    
    STATION_NAME = 'DALIA' 
    MAX_SEARCH_DAYS = 30 
    df = None 
    
    # Define the actual data root directory
    DATA_ROOT_DIR = os.path.join(settings.BASE_DIR, RELATIVE_DATA_PATH)
    
    if not os.path.isdir(DATA_ROOT_DIR):
         return JsonResponse(
            {"error": f"Data root directory not found: {DATA_ROOT_DIR}"}, 
            status=500
        )

    # --- 1. Find the latest valid date folder containing the Ensemble file ---
    target_date = find_latest_valid_ensemble_date(DATA_ROOT_DIR, STATION_NAME, MAX_SEARCH_DAYS)
    
    if target_date is None:
        return JsonResponse(
            {"error": f"Ensemble data not found for Station '{STATION_NAME}' within the last {MAX_SEARCH_DAYS} days in {DATA_ROOT_DIR}. Ensure files are named 'all_en_corr_{STATION_NAME}.csv'."}, 
            status=404
        )
        
    date_folder = target_date.strftime('%Y%m%d')

    ensemble_file_name = f'all_en_corr_{STATION_NAME}.csv'
    input_file_path = os.path.join(DATA_ROOT_DIR, date_folder, ensemble_file_name)
    
    try:
        df = pd.read_csv(input_file_path, parse_dates=['Time'])
            
    except Exception as e:
        return JsonResponse(
            {"error": f"Error processing ensemble data from {date_folder} at {input_file_path}: {str(e)}"}, 
            status=500
        )
        
    ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
    df_ensemble = df[ensemble_cols]
    
    quantiles = [0.25, 0.50, 0.75]
    percentiles = df_ensemble.quantile(quantiles, axis=1).T
    
    df_result = pd.concat([df['Time'], percentiles], axis=1)
    df_result.columns = ['Time', 'min', 'mean', 'max']
    df_result['Time'] = pd.to_datetime(df_result['Time']).dt.strftime('%Y-%m-%d %H:%M:%S')


    df_sliced = df_result.iloc[2:]

    data_percentiles = {
        "date": df_sliced['Time'].tolist(),
        "min": df_sliced['min'].round(3).tolist(),
        "mean": df_sliced['mean'].round(3).tolist(),
        "max": df_sliced['max'].round(3).tolist()
    }

    forecast_start_date_str = df_sliced['Time'].iloc[0].split(' ')[0]
    df_ex = None
    pb_error = None
    

    exceedence_file_name = f'exceedence{date_folder}.csv'
    exceedence_file_path = os.path.join(DATA_ROOT_DIR, date_folder, exceedence_file_name)
    
    try:
        df_ex = pd.read_csv(exceedence_file_path)
    except FileNotFoundError:
        pb_error = f"Exceedence probability file not found for folder: {date_folder}. Path: {exceedence_file_path}"
    except Exception as e:
        pb_error = f"Error processing exceedence data: {str(e)}"

    if df_ex is not None and 'ex_pr' in df_ex.columns:
        num_pb_rows = min(11, len(df_ex))
        
        # Use the dates from the already sliced df_sliced (starting at index 0 of df_sliced)
        date_pb_list = df_sliced['Time'].iloc[:num_pb_rows].tolist() 
        pb_list = df_ex['ex_pr'].iloc[:num_pb_rows].round(3).tolist()
        
        data_pb = {
            "date": date_pb_list,
            "pb": pb_list
        }
    else:

        date_pb_list = df_sliced['Time'].iloc[0:11].tolist() 
        data_pb = {
            "date": date_pb_list,
            "pb": [0] * len(date_pb_list), 
            "error": pb_error or "Exceedence data missing 'ex_pr' column or insufficient data. Probabilities set to 0."
        }

    
    response_data = {
        "code": "success",
        "message": "Data has been fetched!",

        "metadata": {
            "station_id": 80,
            "basin_name": "Brahmaputra Basin",
            "forecast_date": forecast_start_date_str,
            "dc_unit": "",
            "pb_unit": "%",
            "model": "Arima",
            "forecast_type":"Experimental"
        },
        "data": data_percentiles,
        "data_pb": data_pb,
    }

    return JsonResponse(response_data)


def get_allmodels_percentiles_json(request):

    
    STATION_NAME = 'DALIA' 
    MAX_SEARCH_DAYS = 30 
    df = None 
    
    # Define the actual data root directory
    DATA_ROOT_DIR = os.path.join(settings.BASE_DIR, RELATIVE_DATA_PATH)
    
    if not os.path.isdir(DATA_ROOT_DIR):
         return JsonResponse(
            {"error": f"Data root directory not found: {DATA_ROOT_DIR}"}, 
            status=500
        )

    # --- 1. Find the latest valid date folder containing the Ensemble file ---
    target_date = find_latest_valid_ensemble_date(DATA_ROOT_DIR, STATION_NAME, MAX_SEARCH_DAYS)
    
    if target_date is None:
        return JsonResponse(
            {"error": f"Ensemble data not found for Station '{STATION_NAME}' within the last {MAX_SEARCH_DAYS} days in {DATA_ROOT_DIR}. Ensure files are named 'all_en_corr_{STATION_NAME}.csv'."}, 
            status=404
        )
        
    date_folder = target_date.strftime('%Y%m%d')

    ensemble_file_name = f'all_en_corr_{STATION_NAME}.csv'
    input_file_path = os.path.join(DATA_ROOT_DIR, date_folder, ensemble_file_name)
    
    try:
        # Load data, converting 'Time' to datetime objects
        df = pd.read_csv(input_file_path, parse_dates=['Time'])
        
        # Convert the full timestamp (e.g., '2025-10-20 00:00:00+00:00') 
        # to the required 'YYYY-MM-DD' date string format
        df['Time'] = df['Time'].dt.strftime('%Y-%m-%d')
            
    except Exception as e:
        return JsonResponse(
            {"error": f"Error processing ensemble data from {date_folder} at {input_file_path}: {str(e)}"}, 
            status=500
        )

    # Set the formatted 'Time' column as the index
    df_indexed = df.set_index('Time')

    # 1. Convert the indexed DataFrame to a Python dictionary, 
    # resulting in: {'date': {'EN#00': val, ...}, ...}
    temp_dict = df_indexed.to_dict(orient='index')

    # 2. Transform the dictionary to the final desired structure: {'date': [values]}
    # This dictionary comprehension extracts only the values list from the inner dictionary.
    response_data = {
        date: list(data_dict.values())
        for date, data_dict in temp_dict.items()
    }
    
    # Return the dictionary. JsonResponse expects a dictionary and correctly serializes it.
    return JsonResponse(response_data)



@api_view(['GET'])
def ThresholdBasedFlasFloodDorecastModelOptionsView(request):
    model_options = [
        {
            "name": "UKMET",
            "deterministic": "https://api.ffwc.gov.bd/data_load/ukmet-monsoon-basin-wise-flash-flood/$DATE/$STATION",
            "probabilistic": "https://api.ffwc.gov.bd/data_load/ukmet-monsoon-probabilistic-flash-flood/$DATE/$STATION",
            "default": True
        },

        {
            "name": "BMDWRF",
            "deterministic": "https://api.ffwc.gov.bd/data_load/bmd-wrf-forecast/$DATE/$STATION",
            "probabilistic": "",
            "default": False
        },

        {
            "name": "ECMWF",
            "deterministic": "https://api.ffwc.gov.bd/data_load/monsoon-basin-wise-flash-flood/$DATE/$STATION",
            "probabilistic": "https://api.ffwc.gov.bd/data_load/monsoon-probabilistic-flash-flood/$DATE/$STATION",
            "default": False
        }

    ]
    
    return Response(model_options)



@api_view(['GET'])
def FlowPath(request,lat,lng):

    print('In Flow Path API')

    lat = float(lat)
    lng = float(lng)

    # # Request the Watershed via the API
    url = "https://mghydro.com/app/flowpath_api?lat={}&lng={}&precision=high".format(lat, lng)
    r = requests.get(url=url)

    if r.status_code == 400 or r.status_code == 404:
        jsonResult = r.text

    if r.status_code == 500:
        jsonResult= {'error': "Server error. Please contact the developer."}

    # Status code of 200 means everything was OK!
    if r.status_code == 200: 
        jsonResult = r.json()  
        fname = 'floodForecastStations/userbasin.json'
        with open(fname, 'w') as f:
            f.write(r.text)
            print('File Written . .')

    # jsonResult= {'lat':lat,'lng':lng}
    return Response(jsonResult)



@api_view(['GET'])
def UserDefinedBasin(request,lat,lng):
    # from geopy.distance import distance

    # print('In User Defined Basin')

    # # coordinates = []
    # reference_point = (lat, lng)
    # nearest_point = None
    # min_distance = float('inf')

    # dir_path = os.getcwd()
    # river_points=os.path.join(dir_path,'assets/river-points.json')

    # with open(river_points, 'r') as file:
    #     coordinates = json.load(file)

    # for point_coords in coordinates:
    #     dist = distance(reference_point, point_coords).miles  # You can also use .km for kilometers
    #     print(dist)

    #     if dist < min_distance:
    #         min_distance = dist
    #         nearest_point = point_coords

    # print('Nearest Point: ', nearest_point)

    # for feature in feature_collection['features']:
        
    #     if(feature['geometry'] is not None):
    #         geom = feature['geometry']
    #         if geom['type'] in ['LineString', 'MultiLineString', 'Polygon', 'MultiPolygon']:
    #             coords = geom['coordinates']
    #             coordinates.extend(coords)

    # print(coordinates)
        # if geom['type'] == 'Point':
        #     coordinates.append(geom['coordinates'])
        # elif geom['type'] == 'MultiPoint':
        #     coordinates.extend(geom['coordinates'])
        # elif geom['type'] in ['LineString', 'MultiLineString', 'Polygon', 'MultiPolygon']:
        #     # For LineString and Polygon, you might want to extract all points
        #     coords = geom['coordinates']
        #     if geom['type'] == 'Polygon':
        #         # For polygons, coordinates are nested
        #         for ring in coords:
        #             coordinates.extend(ring)
        #     else:
        #         coordinates.extend(coords)

        # for geometry in feature:
        #     print(geometry['coordinates'])

    # print(data['features']['geometry'])

    # # reading the data from the file 
    # with open(station_threshold_path) as f: 
    #     data = f.read() 

    # d = ast.literal_eval(data) 
    # print(d)


    lat = float(lat)
    lng = float(lng)

    # lat = float(nearest_point[0])
    # lng = float(nearest_point[1])

    # nearest_point

    # # Request the Watershed via the API
    url = "https://mghydro.com/app/watershed_api?lat={}&lng={}&precision=high".format(lat, lng)
    print(url)
    r = requests.get(url=url)

    if r.status_code == 400 or r.status_code == 404:
        jsonResult = r.text

    if r.status_code == 500:
        jsonResult= {'error': "Server error. Please contact the developer."}

    # Status code of 200 means everything was OK!
    if r.status_code == 200: 
        jsonResult = r.json()  
    #     fname = 'floodForecastStations/userbasin.json'
    #     with open(fname, 'w') as f:
    #         f.write(r.text)
    #         print('File Written . .')

    # jsonResult= {'lat':lat,'lng':lng}
    return Response(jsonResult)



@api_view(['GET'])
def SubBasinPrecipiation(request,lat,lng):

    print('In Basin Wise Precipitation')

    dir_path = os.getcwd()
    station_threshold_path=os.path.join(dir_path,'floodForecastStations/stationThresholdsList.txt')

    # reading the data from the file 
    with open(station_threshold_path) as f: 
        data = f.read() 

    d = ast.literal_eval(data) 
    
    # print(d)


    lat = float(lat)
    lng = float(lng)

    jsonResult= {'lat':lat,'lng':lng}

    jsonResult = d[1]
    return Response(jsonResult)