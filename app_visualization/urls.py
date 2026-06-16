from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
from django.urls import path


from app_visualization.dropdowns_api.views import (
    SourceDataTypeViewSet,
	SourceViewSet, SystemStateViewSet, ParametersDDViewSet,
    BasinListDDViewSet, 
)
from app_visualization.basin_wise_forecast.views import (
    BasinWiseForcastingViewSet
)
from app_visualization.basin_wise_forecast_from_nc_file.views import (
    BasinWiseForcastFromNcFileViewSet
)
from app_visualization.observation_api.views import (
    StationListViewSet, RFObservationDetailsView, 
    StationListViewSetV2, RFObservationDetailsV2View,
    StationListDDDetailsV5APIView,
)
from app_visualization.ffwc_stream_flow_forecast.views import (
    FfwcSFStationListViewSet, FfwcSFForecastDailyDetailsView,
)
from app_visualization.hydrograph_api.views import (
    FfwcHydrographVisView, FfwcHydrographVisViewV2,
    
)









urlpatterns = [  
    path(
        'dropdown/v1/source_data_type_list_dd/', 
        SourceDataTypeViewSet.as_view({'get': 'source_data_type_list_dd'}), 
        name='source_data_type_list_dd'
    ),  
    path(
        'dropdown/v1/source_list_dd/', 
        SourceViewSet.as_view({'get': 'source_list_dd'}), 
        name='source_list_dd'
    ),  
	path(
        'dropdown/v1/system_state_list_dd/', 
        SystemStateViewSet.as_view({'get': 'system_state_list_dd'}), 
        name='system_state_list_dd'
    ),  
    path(
        'dropdown/v1/param_list_dd/', 
        ParametersDDViewSet.as_view({'get': 'param_list_dd'}), 
        name='param_list_dd'
    ), 
    path(
        'dropdown/v1/basin_list_dd/', 
        BasinListDDViewSet.as_view({'get': 'basin_list_dd'}), 
        name='basin_list_dd'
    ), 

    ##########################################################
    ### API for forecast with source, basin wise
    ##########################################################
    path(
        'basin_wise_forecast/v1/level_wise_forecast_date_wise_all_loc/', 
        BasinWiseForcastingViewSet.as_view({'get': 'level_wise_forecast_date_wise_all_loc'}), 
        name='level_wise_forecast_date_wise_all_loc'
    ),  

    ##########################################################
    ### API for forecast with source, basin wise from NC file
    ##########################################################
    path(
        'basin_wise_forecast_from_nc_file/v1/level_wise_forecast_date_wise_all_loc_from_nc_file/', 
        BasinWiseForcastFromNcFileViewSet.as_view({'post': 'level_wise_forecast_date_wise_all_loc_from_nc_file'}), 
        name='level_wise_forecast_date_wise_all_loc_from_nc_file'
    ),

    ##########################################################
    ### API for observation with observation_api
    ##########################################################
	path(
        'dropdown/v1/station_list_dd/', 
        StationListViewSet.as_view({'get': 'station_list_dd'}), 
        name='station_list_dd'
    ), 
    ##################################
    ### Optimized DB Intensive Query
    ##################################
    path(
        'dropdown/v5/station_list_dd/', 
        StationListDDDetailsV5APIView.as_view(), 
        name='station_list_dd'
    ),

    path(
        'v1/rf_obs_details/<int:id>/', 
        RFObservationDetailsView.as_view(), 
        name='rf_obs_details'
    ),
    
    path(
        'dropdown/v2/station_list_dd/', 
        StationListViewSetV2.as_view({'get': 'station_list_dd'}), 
        name='station_list_dd'
    ),
    path(
        'v2/rf_obs_details/<int:id>/', 
        RFObservationDetailsV2View.as_view(), 
        name='rf_obs_details'
    ),

    ##########################################################
    ### API for forecast with ffwc stream flow
    ##########################################################
	path(
        'dropdown/v1/sf_station_list_dd/', 
        FfwcSFStationListViewSet.as_view({'get': 'sf_station_list_dd'}), 
        name='sf_station_list_dd'
    ), 
    path(
        'v1/ffwc_sf_forecast_details/<int:id>/', 
        FfwcSFForecastDailyDetailsView.as_view(), 
        name='ffwc_sf_forecast_details'
    ),
    
    ##########################################################
    ### API for Hydrograph
    ##########################################################
	path(
        # 'v1/hydrograph_api/ffwc_hydrograph_visualization/<str:place_name>/<str:date>/', 
        'v1/hydrograph_api/ffwc_hydrograph_visualization/', 
        FfwcHydrographVisView.as_view(), 
        name='ffwc_hydrograph_visualization'
    ),
    path(  
        'v2/hydrograph_api/ffwc_hydrograph_visualization/', 
        FfwcHydrographVisViewV2.as_view(), 
        name='ffwc_hydrograph_visualization'
    ),


    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
