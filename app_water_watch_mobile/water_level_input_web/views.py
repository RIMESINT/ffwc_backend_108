# views.py
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from app_water_watch_mobile.models import (
    WaterLevelInputForMobileUser
)
from app_water_watch_mobile.water_level_input_web.serializers import (
    WaterLevelInputForMobileUserSerializer
)

from ffwc_django_project.project_constant import PAGINATION_CONSTANT






class StandardPagination(PageNumberPagination):
    page_size = PAGINATION_CONSTANT['page_size']
    page_size_query_param = PAGINATION_CONSTANT['page_size_query_param']
    max_page_size = PAGINATION_CONSTANT['max_page_size']


class WaterLevelInputListAPIView(generics.ListAPIView):
    serializer_class = WaterLevelInputForMobileUserSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    
    def get_queryset(self):
        queryset = WaterLevelInputForMobileUser.objects.all()
        
        station_id = self.request.query_params.get('station_id', None)
        is_acepted = self.request.query_params.get('is_acepted', None)
        created_by = self.request.query_params.get('created_by', None)
        
        if station_id:
            queryset = queryset.filter(station__id=station_id)
        
        if is_acepted is not None:
            if is_acepted.lower() in ['true', '1', 'yes', 'approved']:
                queryset = queryset.filter(is_acepted=True)
            elif is_acepted.lower() in ['false', '0', 'no', 'rejected']:
                queryset = queryset.filter(is_acepted=False)
            else:
                queryset = queryset.filter(is_acepted=None)
        
        if created_by:
            queryset = queryset.filter(created_by__id=created_by)
        
        return queryset.order_by('-observation_date')