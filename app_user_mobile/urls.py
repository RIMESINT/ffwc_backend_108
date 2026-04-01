
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from app_user_mobile.views import (
    SendOTPView, VerifyOTPView,
    UpdateProfileView, UserProfileView,
    SimpleFCMTokenLocationAPI,
)



urlpatterns = [
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    
    path('mobile_user_profile_update/', UpdateProfileView.as_view(), name='mobile_user_profile_update'),
    path('mobile_user_profile_details/', UserProfileView.as_view(), name='mobile_user_profile_details'),
    
    path('v1/update_location_by_fcm_token/', SimpleFCMTokenLocationAPI.as_view(), name='update_location_by_fcm_token'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)