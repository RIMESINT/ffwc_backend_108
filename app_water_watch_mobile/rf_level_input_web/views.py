from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from django.core.paginator import Paginator
from django.http import JsonResponse

from app_water_watch_mobile.models import RFLevelInputForMobileUser
from app_water_watch_mobile.rf_level_input_web.serializers import RFLevelInputForMobileUserSerializer

from ffwc_django_project.project_constant import PAGINATION_CONSTANT






class StandardPagination(PageNumberPagination):
    page_size = PAGINATION_CONSTANT['page_size']
    page_size_query_param = PAGINATION_CONSTANT['page_size_query_param']
    max_page_size = PAGINATION_CONSTANT['max_page_size']

# class RFLevelInputListAPIView(APIView):
#     """
#         API view to list RFLevelInputForMobileUser records with optional filtering and pagination
#     """
#     # serializer_class = WaterLevelInputForMobileUserSerializer
#     # pagination_class = StandardPagination
#     # filter_backends = [DjangoFilterBackend]
    
#     def get(self, request):
#         try:
#             queryset = RFLevelInputForMobileUser.objects.all().select_related(
#                 'station', 'created_by', 'updated_by'
#             )
            
#             station_id = request.GET.get('station_id', None)
#             is_acepted = request.GET.get('is_acepted', None)
#             created_by = request.GET.get('created_by', None)
            
#             if station_id:
#                 queryset = queryset.filter(station__id=station_id)
            
#             if is_acepted is not None:
#                 if is_acepted.lower() in ['true', '1', 'yes', 'approved']:
#                     queryset = queryset.filter(is_acepted=True)
#                 elif is_acepted.lower() in ['false', '0', 'no', 'rejected']:
#                     queryset = queryset.filter(is_acepted=False)
#                 else:
#                     queryset = queryset.filter(is_acepted=None)
            
#             if created_by:
#                 queryset = queryset.filter(created_by__id=created_by)
            
#             queryset = queryset.order_by('-observation_date')
            
#             page_number = request.GET.get('page', 1)
#             page_size = request.GET.get('page_size', PAGINATION_CONSTANT['page_size'])  # Default page size 10
            
#             try:
#                 page_number = int(page_number)
#                 page_size = int(page_size)
#             except ValueError:
#                 return Response(
#                     {"error": "page and page_size must be integers"}, 
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             if page_size > PAGINATION_CONSTANT['max_page_size']:
#                 page_size = PAGINATION_CONSTANT['max_page_size']
            
#             paginator = Paginator(queryset, page_size)
            
#             try:
#                 page_obj = paginator.page(page_number)
#             except Exception as e:
#                 return Response(
#                     {"error": f"Invalid page: {str(e)}"}, 
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             serializer = RFLevelInputForMobileUserSerializer(page_obj, many=True)
            
#             response_data = {
#                 'count': paginator.count,
#                 'total_pages': paginator.num_pages,
#                 'current_page': page_number,
#                 'page_size': page_size,
#                 'next': page_obj.has_next(),
#                 'previous': page_obj.has_previous(),
#                 'results': serializer.data
#             }
            
#             if page_obj.has_next():
#                 response_data['next_page'] = page_obj.next_page_number()
#             if page_obj.has_previous():
#                 response_data['previous_page'] = page_obj.previous_page_number()
            
#             return Response(response_data, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             return Response(
#                 {"error": f"An error occurred: {str(e)}"}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
            
            
class RFLevelInputListAPIView(generics.ListAPIView):
    serializer_class = RFLevelInputForMobileUserSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    
    def get_queryset(self):
        queryset = RFLevelInputForMobileUser.objects.all()
        
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

