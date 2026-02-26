from django.urls import path
from app_water_watch_mobile.water_level_input.views import (
    WaterLevelStationForMobileUserViewSet,
    BulkWaterLevelCreateAPIView,
    Last7DaysWaterLevelAPIView,
    WaterLevelUpdateAPIView,
    DeleteWaterLevelInputAPIView,
)
from app_water_watch_mobile.rf_level_input.views import (
    RFLevelStationForMobileUserViewSet,
    BulkRFLevelCreateAPIView,
    Last7DaysRFLevelAPIView,
    RFLevelUpdateAPIView,
    DeleteRFLevelInputAPIView,
)

from app_water_watch_mobile.water_level_input_web.views import (
    WaterLevelInputListAPIView,
)
from app_water_watch_mobile.rf_level_input_web.views import (
    RFLevelInputListAPIView,
)
from app_water_watch_mobile.dropdown_api_mobile_user.views import (
    MobileAuthUserListView,
)




urlpatterns = [
    #####################################################################################
    #####################################################################################
    ### API endpoints for Dropdown
    #####################################################################################
    #####################################################################################
    path('v1/mobile_user_list/', MobileAuthUserListView.as_view(), name='mobile_user_list'),
    
    #####################################################################################
    ### API endpoints for managing water level inputs from mobile users.
    #####################################################################################
    path('waterlevel/loggedin-user-stations/', WaterLevelStationForMobileUserViewSet.as_view(), name='loggedin-user-stations'),
    path('waterlevel/bulk-create/', BulkWaterLevelCreateAPIView.as_view(), name='mobile-waterlevel-bulk-create'),
    path('waterlevel/last-7-days/', Last7DaysWaterLevelAPIView.as_view(), name='last-7-days-waterlevel'),
    path('waterlevel/<int:pk>/update/', WaterLevelUpdateAPIView.as_view(), name='mobile-waterlevel-update'),
    path('waterlevel/<int:pk>/delete/', DeleteWaterLevelInputAPIView.as_view(), name='mobile-waterlevel-delete'),
    
    #####################################################################################
    ### API endpoints for managing Rainfall level inputs from mobile users.
    #####################################################################################
    path('rflevel/loggedin-user-stations/', RFLevelStationForMobileUserViewSet.as_view(), name='rflevel-loggedin-user-stations'),
    path('rflevel/bulk-create/', BulkRFLevelCreateAPIView.as_view(), name='rflevel-mobile-waterlevel-bulk-create'),
    path('rflevel/last-7-days/', Last7DaysRFLevelAPIView.as_view(), name='rflevel-last-7-days-waterlevel'),
    path('rflevel/<int:pk>/update/', RFLevelUpdateAPIView.as_view(), name='rflevel-mobile-waterlevel-update'),
    path('rflevel/<int:pk>/delete/', DeleteRFLevelInputAPIView.as_view(), name='rflevel-mobile-waterlevel-delete'),
    
    
    #####################################################################################
    #####################################################################################
    ### API endpoints for managing water level inputs from WEB users.
    #####################################################################################
    #####################################################################################
    path(
        'v1/water_level_inputs_list_with_filter/',
        WaterLevelInputListAPIView.as_view(), 
        name='water_level_inputs_list_with_filter'
    ),
    
    #####################################################################################
    #####################################################################################
    ### API endpoints for managing Rainfall level inputs from WEB users.
    #####################################################################################
    #####################################################################################
    path(
        'v1/rf_level_inputs_list_with_filter/', 
        RFLevelInputListAPIView.as_view(), 
        name='rf_level_inputs_list_with_filter'
    ),
]
