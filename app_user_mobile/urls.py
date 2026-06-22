
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .api_views import vendor_wl_push_api

from app_user_mobile.views import (
    SendOTPView, VerifyOTPView,
    UpdateProfileView, UserProfileView,
    SimpleFCMTokenLocationAPI,

    VendorWLPushAPIView,
    VendorRainfallPushAPIView,

    VendorWLHourlyPushAPIView,
    VendorRainfallHourlyPushAPIView
)

from .views import get_hydro_data, get_hydro_hourly_data,get_sms_list

urlpatterns = [
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    
    path('mobile_user_profile_update/', UpdateProfileView.as_view(), name='mobile_user_profile_update'),
    path('mobile_user_profile_details/', UserProfileView.as_view(), name='mobile_user_profile_details'),
    
    path('v1/update_location_by_fcm_token/', SimpleFCMTokenLocationAPI.as_view(), name='update_location_by_fcm_token'),
    
    
    path('hydro-data/', get_hydro_data, name='hydro_data_api'),
    path('hydro-hourly/', get_hydro_hourly_data, name='hydro_hourly_api'),


    path('sms-list/', get_sms_list, name='sms_list_api'),


    # POST APIs for Vendors
    path('push-wl-data/', VendorWLPushAPIView.as_view(), name='vendor-push-wl'),
    path('push-rainfall-data/', VendorRainfallPushAPIView.as_view(), name='vendor-push-rainfall'),

    path('push-wl-hourly/', VendorWLHourlyPushAPIView.as_view(), name='vendor-push-wl-hourly'),
    path('push-rainfall-hourly/', VendorRainfallHourlyPushAPIView.as_view(), name='vendor-push-rainfall-hourly'),

    

    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)