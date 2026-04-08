from django.urls import path, include,re_path
from rest_framework.routers import DefaultRouter
from . import views as views

from indian_stations import views as transView

from indian_stations.views import TransboundaryRiverDataView

from data_load.views import (
    # rainfall_by_station,
    # rainfall_by_station_and_date,
    # rainfall_sum_by_station_and_year,
    # rainfall_avg_by_station_and_year,
    
    FfwcStations2025ListViewsAPIs, 
    StationUpdateView,
    FfwcStations2025BulkUpdateView,
    
    BulletinRelatedManueViewSet,
)  




router = DefaultRouter()

router.register(r'user-auth', views.UserViewSet, basename='user')
router.register(r'update-date',views.updateDateViewSet,basename='update')

router.register(r'station-basins', views.BasinViewSet)

router.register(r'units', views.UnitViewSet)

router.register(r'stations', views.StationsViewSet, basename='stations')
router.register(r'v2-mobile-stations-2025', views.StationSummaryViewMobileV1ViewSet, basename='v2-mobile-stations-2025')
router.register(r'stations-2025', views.StationViewSet, basename='stations-2025')
router.register(r'rainfall-stations', views.RainfallStationViewSet)


router.register(r'water-level-forecasts', views.WaterLevelForecastViewSet)
# router.register(r'five-days-forecast', views.FiveDaysForecastWaterlevelViewSet, basename='five-days-forecast')

router.register(r'flood-alert-disclaimer', views.FloodAlertDisclaimerViewSet)

router.register(r'messages', views.MessagesViewSet)
router.register(r'scroller-messages', views.ScrollerMessagesViewSet)
router.register(r'second-scroller-messages', views.SecondScrollerMessagesViewSet)


router.register(r'observed', views.ObservedWaterlevelViewSet, basename='observed-waterlevel')
router.register(r'modified-observed', views.ModifiedObservedViewSet, basename='modified-observed')

router.register(r'water-level-observations', views.WaterLevelObservationViewSet)
router.register(r'three-days-observed', views.ThreeDaysObservedWaterlevelViewSet, basename='three-days-observed')
router.register(r'annotate-observed-trend', views.AnnotatedObservedTrendViewSet, basename='observed-trend')
router.register(r'recent-observed', views.RecentObservedWaterlevelViewSet, basename='recent-observed')

router.register(r'rainfall-observations', views.RainfallObservationViewSet)
router.register(r'observed-rainfall', views.ObservedRainfallViewSet, basename='observed-rainfall')
router.register(r'three-days-observed-rainfall',views.ThreeDaysObservedRainfallViewSet,basename='three-days-rainfall')


router.register(r'monsoon-config',views.monsoonConfigViewSet,basename='monsoon-config')

router.register(r'morning-observed',views.MorningWaterlevelViewSet,basename='morning-observed')
router.register(r'afternoon-observed',views.AfternoonWaterlevelViewSet,basename='afternoon-observed')
router.register(r'historical-waterlevel', views.HistoricalWaterlevelViewSet, basename='historical-waterlevel')

router.register(r'bulletins_pdf_manues', BulletinRelatedManueViewSet, basename='bulletins_pdf_manues')


# router.register(r'observed-rainfall-by-date/(?P<date_str>[^/.]+)', views.ObservedRainfallByDateViewSet, basename='rainfall-observations')


# router.register(r'about', view.about_page, basename='about')

from .views import ScheduledTaskListView, ScheduledTaskCreateView,ScheduledTaskUpdateView,ScheduledTaskToggleView
from .views import JsonEntryListView,JsonEntryCreateView,JsonEntryRetrieveUpdateDestroyView

urlpatterns = [
    path('', include(router.urls)),


    path('station-by-name/<slug:station_name>/', views.station_by_name, name='station_by_name'),

    path('observed-rainfall-by-date/<str:date_str>/', views.ObservedRainfallByDateView.as_view(), name='observed-rainfall-by-date'),
    path('fourty-days-rainfall-by-station-and-date/<slug:station_id>/<slug:start_date>', 
        views.ObservedRainfallViewSet.as_view({
            'get': 'fourty_days_rainfall_by_station_and_date'
        }),
        name='forty-days-rainfall-by-station-and-date'
    ),

    re_path(r'^rainfall-by-station/(?P<station_id>\d+)/$', views.RainfallByStationViewSet.as_view({'get': 'list'}), name='rainfall-by-station'),
    path('rainfall/station/<int:st_id>/year/<int:year>/', views.rainfall_sum_by_station_and_year, name='rainfall_by_station_and_year'),
    path('rainfall-sum-by-station-and-year/<int:st_id>/<int:year>/',  views.rainfall_sum_by_station_and_year, name='rainfall_by_station_and_year'),
    
    path('short-range-station-by-basin/<int:basin_id>/', views.ShortRangeStationByBasinView.as_view(), name='short-range-stations-by-basin'),
    path('short-range-station-by-division/<str:division_name>/',views.ShortRangeStationByDivisionView.as_view(),name='short-range-stations-by-division'),

    path('medium-range-station-by-basin/<int:basin_id>/', views.MediumRangeStationByBasinView.as_view(), name='medium-range-stations-by-basin'),
    path('medium-range-station-by-division/<str:division_name>/',views.MediumRangeStationByDivisionView.as_view(),name='medium-range-stations-by-division'),


    path('station-by-id/<int:station_id>/',views.StationByIdView.as_view(),name='station-by-id'),

    path('experimental-stations/', views.get_experimental_stations, name='experimental_stations'),
    path('medium-range-station/', views.get_medium_range_stations, name='medium_range_stations'),
    path('extended-range-station/', views.get_extended_range_stations, name='extended_range_stations'),

    re_path(r'^observed-waterlevel-by-station-and-date/(?P<station_id>\d+)/(?P<date>\d{4}-\d{2}-\d{2})/$',
        views.ObservedWaterlevelByStationAndDateViewSet.as_view({'get': 'list'}),name='observed-waterlevel-by-station-and-date'
    ),

    path('observed-waterlevel-sum-by-station-and-year/<int:st_id>/<int:year>/', views.waterlevel_sum_by_station_and_year, name='waterlevel-sum-by-station-and-year'),

    path('seven-days-observed-waterlevel-by-station/<int:st_id>/', 
        views.WaterLevelObservationViewSet.as_view({'get': 'sevenDaysObservedWaterLevelByStation'}),name='seven-days-observed-waterlevel-by-station'),
    
    path('observed-for-medium-range-forecast-by-station/<int:st_id>/', views.WaterLevelObservationExperimentalsView.as_view(), name='observed-for-medium-range-forecast-by-station'),
    # path('observed-for-medium-range-forecast-by-station/<int:st_id>/', 
    #     views.WaterLevelObservationViewSet.as_view({'get': 'experimentalObservedWaterLevelByStation'}),name='observed-for-medium-range-forecast-by-station'),
    
    # This path `path('waterlevel/station/<int:st_id>/year/<int:year>/',
    # views.WaterLevelByStationAndYearView.as_view(), name='waterlevel_by_station_and_year')` is
    # defining a URL pattern in Django.
    # path('waterlevel/station/<int:st_id>/year/<int:year>/', views.WaterLevelByStationAndYearView.as_view(), name='waterlevel_by_station_and_year'),
    path('old-observed-waterlevel-by-station-and-year/<slug:st_id>/<slug:year>',views.WaterLevelByStationAndYearView.as_view(), name='waterlevel_by_station_and_year'),

    re_path(r'^five-days-forecast-waterlevel/(?P<date>\d{4}-\d{2}-\d{2})?/?$',
        views.FiveDaysForecastWaterlevelViewSet.as_view({'get': 'list'}),name='five-days-forecast'
    ),

    re_path(r'^seven-days-forecast-waterlevel-24-hours/(?P<date>\d{4}-\d{2}-\d{2})?/?$',
        views.SevenDaysForecastWaterlevel24HoursViewSet.as_view({'get': 'list'}),name='seven-days-forecast-waterlevel-24-hours'
    ),

    re_path(r'^ten-days-forecast-waterlevel-24-hours/(?P<date>\d{4}-\d{2}-\d{2})?/?$',
        views.TenDaysForecastWaterlevel24HoursViewSet.as_view({'get': 'list'}),name='ten-days-forecast-waterlevel-24-hours'
    ),



    path('seven-days-forecast-waterlevel-by-station/<int:station_id>/', 
        views.WaterLevelForecastViewSet.as_view({'get': 'seven_days_forecast_by_station'}),name='seven-days-forecast-waterlevel-by-station'),
    path('forecast-waterlevel-by-station/<int:station_id>/', 
        views.WaterLevelForecastViewSet.as_view({'get': 'forecast_waterlevel_by_station'}),name='forecast-waterlevel-by-station'),

    path('medium-range-forecast-by-station/<int:st_id>/', views.WaterLevelForecastsExperimentalsView.as_view(),name='medium-range-forecast-by-station'), 



    path('district-flood-alerts/', views.district_flood_alerts, name='district-flood-alerts'),
    path('district-flood-alerts-by-date/<str:date>/', views.district_flood_alerts_by_date, name='district-flood-alerts-by-date'),
    path('district-flood-alerts-forecast-by-date/<str:date>/', views.district_flood_alerts_forecast_by_date, name='district-flood-alerts-forecast-by-date'),
    path('district-flood-alerts-observed-forecast-by-available-dates/<str:date>/', views.district_flood_observed_and_forecast_alerts_by_available_dates, name='district-flood-alerts-observed-forecast-by-available-dates'),


    path('district-flood-alerts-observed-forecast-by-observed-dates/<str:date>/', views.district_flood_observed_and_forecast_alerts_by_observed_date, name='district-flood-alerts-observed-forecast-by-observed-dates'),
    path('district-flood-alerts-observed-forecast-by-observed-dates-grouped-by-disrcits/<str:date>/', views.district_flood_observed_and_forecast_alerts_by_observed_date_grouped_by_districts, name='district-flood-alerts-observed-forecast-by-observed-dates-grouped-by-disrcits'),
    
    # path('nearby-district-flood-alerts-by-date-and-radius/<str:date>/<float:nearby_radius>/', views.nearby_district_flood_alerts_by_date_and_radius, name='nearby_district_flood_alerts_by_date_and_radius'),


    # re_path(r'^district-flood-alerts-observed-forecast-by-observed-dates/(?P<date>\d{4}-\d{2}-\d{2})/$',
    #     views.district_flood_alerts_observed_forecast_by_observed_dates,name='district-flood-alerts-observed-forecast-by-observed-dates'
    # ),



    path('basins/', views.ThresholdBasinsListCreateView.as_view(), name='basin-list-create'),
    path('monsoon-basin-wise-flash-flood/<slug:forecast_date>/<int:basin_id>',views.MonsoonFlashFlood,name='monsoon-basin-flash-flood'),
    path('monsoon-probabilistic-flash-flood/<slug:givenDate>/<int:basin_id>',views.MonsoonProbabilisticFlashFlood,name='monsoon-probabilistic-flash-flood'),


    # Premonsoon URLS
    path('new-basin-wise-flash-flood/<slug:forecast_date>/<int:basin_id>',views.NewFlashFlood,name='new-basin-flash-flood'),
    path('new-probabilistic-flash-flood/<slug:givenDate>/<int:basin_id>',views.NewProbabilisticFlashFlood,name='new-probabilistic-flash-flood'),


    path('ukmet-monsoon-basin-wise-flash-flood/<slug:forecast_date>/<int:basin_id>',views.UkMetMonsoonFlashFlood,name='ukmet-monsoon-basin-flash-flood'),
    path('ukmet-pre-monsoon-basin-wise-flash-flood/<slug:forecast_date>/<int:basin_id>',views.UkMetPreMonsoonFlashFlood,name='ukmet-pre-monsoon-basin-flash-flood'),

    path('ukmet-monsoon-probabilistic-flash-flood/<slug:givenDate>/<int:basin_id>',views.UKMetMonsoonProbabilisticFlashFlood,name='ukmet-monsoon-probabilistic-flash-flood'),
    path('ukmet-pre-monsoon-probabilistic-flash-flood/<slug:givenDate>/<int:basin_id>',views.UKMetPreMonsoonProbabilisticFlashFlood,name='ukmet-pre-monsoon-probabilistic-flash-flood'),

    path('bmd-wrf-forecast/<str:forecast_date>/<int:basin_id>/', views.BMDWRFMonsoonFlashFlood, name='bmd-wrf-monsoon-flash-flood'),
    path('bmd-wrf-pre-monsoon-forecast/<str:forecast_date>/<int:basin_id>/', views.BMDWRFPreMonsoonFlashFlood, name='bmd-wrf-pre-monsoon-flash-flood'),


    path('threshold-based-flash-flood-model-options/', views.ThresholdBasedFlasFloodDorecastModelOptionsView, name='threshold-based-flash-flood-model-options'),


    path('about/', views.about_page, name='about_page'),
    # path('', views.about_page, name='about_page'),


    path('floodmaps/', views.floodmaps_data, name='floodmaps_data'),
    path('flood-summary/', views.flood_summary_view, name='flood-summary'),
    path('flood-report/', views.flood_monitoring_report, name='flood-report'),

    




    # Transboundary Station DSS views
    path('insert-user-ffwc-stations',views.InsertUserStationView.as_view(), name = 'insert-user-ffwc-stations'),
    path('get-delete-id-from-profile/<int:profile_id>/<int:station_id>',views.DeleteProfileID,name='delete-profile-id'),
    path('delete-user-ffwc-stations/<int:pk>',views.deleteProfileStationsByUserId,name='delete-stations'),

    path('insert-user-indian-stations',views.InsertUserIndianStationView.as_view()),
    path('get-delete-id-from-indian-profile/<int:profile_id>/<int:station_id>',views.DeleteIndianProfileID,name='delete-indian-profile-id'),
    path('delete-user-indian-stations/<int:pk>',views.deleteProfileIndianStationsByUserId,name='delete-indian-stations'),

    

    # path('trans-river-data-from-database/<str:st_code>/<str:end_date>/', TransboundaryRiverDataView.as_view(), name='trans_river_data_from_database_with_date'),
    path('trans-river-data-from-database/<str:station_code>/<current_date>', transView.get_indian_station_water_data, name='indian_station_water_data'),
    
    
    
    #######################################################################################
    ### ADDED BY: SHAIF    | DATE: 2025-08-13
    ### REQUESTED BY: JOBAYER
    #######################################################################################
    # path('rainfall-sum-by-station-and-year/<slug:st_id>/<slug:year>', rainfall_sum_by_station_and_year),
    
    #######################################################################################
    ### ADDED BY: SHAIF | DATE: 2025-08-14
    ### ASSIGNED BY: SAJIB BHAI
    ####################################################################################### 
    path(
        'v1/web_id_wise_serial_ffwc_stations_2025/', 
        FfwcStations2025ListViewsAPIs.as_view(), 
        name='web_id_wse_serial_ffwc_stations_2025'
    ),
    path(
        'v1/web_id_wise_serial_update_ffwc_stations_2025/<int:station_id>/', 
        StationUpdateView.as_view(), 
        name='web_id_wise_serial_update_ffwc_stations_2025'
    ),
    path(
        'v1/web_id_wise_serial_bulk_update_ffwc_stations_2025/', 
        FfwcStations2025BulkUpdateView.as_view(), 
        name='web_id_wise_serial_bulk_update_ffwc_stations_2025'
    ),


    path(
        'v1/water_level_list_view/', 
        views.WaterlevelAlertListView.as_view(), 
        name='water_level_list_view'
    ),

   path(
        'v1/district-alerts/update/<int:id>/', 
        views.update_district_flood_alert,
        name='district-alerts-update' 
    ),

    path(
        'v1/ens_model_choices_list/<int:station_id>/<str:date>/', 
        views.EnsModelChoiceListAPI.as_view(), 
        name='ens_model_choices_list'
    ),



        # Endpoint for GET (listing all tasks)
    path('scheduled-tasks/', ScheduledTaskListView.as_view(), name='scheduled-task-list'),
    
    # Endpoint for POST (creating a new task)
    path('scheduled-tasks/create/', ScheduledTaskCreateView.as_view(), name='scheduled-task-create'),

    path('scheduled-tasks/update/<int:pk>/', ScheduledTaskUpdateView.as_view(), name='scheduled-task-update'),
    path('scheduled-tasks/toggle/<int:pk>/', ScheduledTaskToggleView.as_view(), name='scheduled-task-toggle'),

    path('district-flood-alerts-updates/', views.DistrictFloodAlertListView.as_view(), name='district-flood-alerts-updates'),
    path('update-district-flood-alerts-auto-updates/update/<str:district_name>/',  views.UpdateDistrictAutoUpdateView.as_view(), name='update-district-flood-alerts-auto-updates'),

    # Endpoint to GET the list of all entries
    path('entries/', JsonEntryListView.as_view(), name='entry-list'),
    # Endpoint to POST a new entry
    path('entries/create/', JsonEntryCreateView.as_view(), name='entry-create'),
    # Endpoint for a specific item (GET, PATCH, DELETE)
    path('entries/<int:pk>/', JsonEntryRetrieveUpdateDestroyView.as_view(), name='entry-detail'),



    path('rapid_discharge_forecast/80/', views.get_ensemble_percentiles_json, name='dalia_ensemble_percentiles'),
    path('rapid_discharge_all_models/80/', views.get_allmodels_percentiles_json, name='dalia_all_models_percentiles'),


    path('flow-path/<str:lat>/<str:lng>',views.FlowPath,name='flow-path'),
    path('user-defined-basin/<str:lat>/<str:lng>',views.UserDefinedBasin,name='user-defined-basin'),
    path('sub-basin-precipitation/<str:lat>/<str:lng>',views.SubBasinPrecipiation,name='sub-basin-precipitation'),




   # Endpoint for the full data
    path('basin-wise-forecast/cumilla/latest/', views.get_latest_cumilla_forecast, name='cumilla_latest'),
    # Endpoint to see ONLY the date/metadata
    path('bsin-wise-forecast/cumilla/info/', views.get_forecast_metadata, name='cumilla_info'),

    # Amalshid
    path('basin-wise-forecast/amalshid/latest/', views.get_latest_amalshid_forecast, name='amalshid_latest'),
    
    # Sylhet
    path('basin-wise-forecast/sylhet/latest/', views.get_latest_sylhet_forecast, name='sylhet_latest'),
    
    # Sunamganj
    path('basin-wise-forecast/sunamganj/latest/', views.get_latest_sunamganj_forecast, name='sunamganj_latest'),

    # Parshuram (Feni River)
    path('basin-wise-forecast/parshuram/latest/', views.get_latest_parshuram_forecast, name='parshuram_latest'),
    
    path('basin-wise-forecast/dalia/latest/', views.get_latest_dalia_forecast, name='dalia_latest'),
    
]