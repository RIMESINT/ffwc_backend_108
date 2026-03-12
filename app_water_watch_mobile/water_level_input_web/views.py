# views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from app_water_watch_mobile.models import (
    WaterLevelInputForMobileUser
)
from app_water_watch_mobile.water_level_input_web.serializers import (
    WaterLevelInputForMobileUserSerializer,
    WaterLevelInputApproveRejectSerializer
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
        is_approved = self.request.query_params.get('is_approved', None)
        is_rejected = self.request.query_params.get('is_rejected', None)
        
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
        
        if is_approved is not None:
            if is_approved.lower() in ['true', '1', 'yes', 'approved']:
                queryset = queryset.filter(is_approved=True)
            elif is_approved.lower() in ['false', '0', 'no', 'rejected']:
                queryset = queryset.filter(is_approved=False)
            else:
                queryset = queryset.filter(is_approved=None)
        
        if is_rejected is not None:
            if is_rejected.lower() in ['true', '1', 'yes', 'approved']:
                queryset = queryset.filter(is_rejected=True)
            elif is_rejected.lower() in ['false', '0', 'no', 'rejected']:
                queryset = queryset.filter(is_rejected=False)
            else:
                queryset = queryset.filter(is_rejected=None)
        
        return queryset.order_by('-observation_date')

class WaterLevelInputApproveRejectAPIView(generics.UpdateAPIView):
    """
    PATCH /v1/water_level_input_approve_reject/<pk>/
    Approve or reject a water level input. Only one of is_approved or 
    is_rejected can be True at a time.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WaterLevelInputApproveRejectSerializer
    queryset = WaterLevelInputForMobileUser.objects.all()
    http_method_names = ['patch']  # Only PATCH allowed — partial update

    def perform_update(self, serializer):
        is_approved = serializer.validated_data.get('is_approved', False)
        is_rejected = serializer.validated_data.get('is_rejected', False)

        # Enforce mutual exclusivity — one DB write only
        if is_approved:
            serializer.save(is_approved=True, is_rejected=False)
        elif is_rejected:
            serializer.save(is_approved=False, is_rejected=True)
        else:
            serializer.save()
    