import requests
import json

from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import UpdateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta


from app_user_mobile.models import (
    MobileAuthUser, OTP,
    FCMTokenWiseUpdatedLatLon,
)
from app_user_mobile.serializers import (
    SendOTPSerializer, VerifyOTPSerializer, MobileUserSerializer,
    UpdateProfileSerializer, MobileAuthUserSerializer,
)
from app_user_mobile.authentication import (
    MobileJWTAuthentication,
    
)

from django.conf import settings
ECMWF_BASE_URL = settings.BASE_DIR








class BulkSMSClient:   
    
    def __init__(self, api_key, senderid, url):
        self.api_key = api_key
        self.senderid = senderid
        self.url = url

    def send_otp(self, mobile, otp):
        number = str(mobile)
        message = f"Your FFWC Mobile Application OTP Code Is: {otp}"

        data = {
            "api_key": self.api_key,
            "senderid": self.senderid,
            "number": number,
            "message": message
        }

        try:
            response = requests.post(self.url, data=data, verify=False)
            return response.text
        except requests.exceptions.RequestException as e:
            print("Error sending OTP:", e)
            return None


class SendOTPView(APIView):
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            mobile_number = serializer.validated_data['mobile_number']
            
            mobile_user_count = MobileAuthUser.objects.filter(
                mobile_number = mobile_number
            ).count()
            if mobile_user_count < 1:
                return Response({
                    'message': f'{mobile_number} is unauthorized. Please contact with Admin',  
                }, status=status.HTTP_200_OK)
            
            # Generate OTP
            otp_instance = OTP.generate_otp(mobile_number)
            
            with open(ECMWF_BASE_URL / 'env.json', 'r') as envf:
                env_ = json.load(envf)
            BULK_SMS_CONF = env_['bulk_sms_send']
            url = BULK_SMS_CONF["URL"]    
            api_key = BULK_SMS_CONF["API_KEY"]    
            senderid = BULK_SMS_CONF["SENDER_ID"] 
            
            sms_client = BulkSMSClient(
                api_key=api_key,
                senderid=senderid,
                url=url
            )

            # response = sms_client.send_otp("017XXXXXXXX", "123456")
            response = sms_client.send_otp(mobile_number, otp_instance.otp)
            response_dict = json.loads(response)
            # print(response_dict)
            
            return Response({
                'message': 'OTP sent successfully',
                'otp': otp_instance.otp,  # Remove this in production
                'sender_response': response_dict,  # Remove this in production
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            mobile_number = serializer.validated_data['mobile_number']
            
            # Get or create the user
            user, created = MobileAuthUser.objects.get_or_create(
                mobile_number=mobile_number
            )
            
            if created:
                user.is_verified = True
                user.save()
            
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            if hasattr(user, 'mobile_number'):
                access_token['user_type'] = 'mobile'
                access_token['mobile_number'] = user.mobile_number
            
            if 'lat' in request.data or 'long' in request.data or 'fcm_token' in request.data:
                user_serializer = MobileUserSerializer(
                    user, 
                    data=request.data, 
                    partial=True
                )
                if user_serializer.is_valid():
                    user_serializer.save()
            
            return Response({
                'refresh': str(refresh),
                'access': str(access_token),
                'user': MobileUserSerializer(user).data,
                'is_new_user': created
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
"""
    #######################################################################################
    ### PUT API for updating profile fields of MobileAuthUser
    #######################################################################################
"""
class UpdateProfileView(UpdateAPIView):
    """
        API endpoint to update user profile information.
        All fields are optional in the update.
    """
    queryset = MobileAuthUser.objects.all()
    serializer_class = UpdateProfileSerializer
    authentication_classes = [MobileJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # Ensure users can only update their own profile
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # Allow partial updates
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return the complete user data after update
        user_serializer = MobileAuthUserSerializer(instance)
        return Response(user_serializer.data, status=status.HTTP_200_OK)

class UserProfileView(RetrieveAPIView):
    """
        API endpoint to retrieve user profile information.
    """
    serializer_class = MobileAuthUserSerializer
    authentication_classes = [MobileJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    



"""
    #######################################################################################
    ### PUT API for updating Lat,Lon according to FCM-Token of MobileAuthUser
    #######################################################################################
"""
class SimpleFCMTokenLocationAPI(APIView):
    """
        Simple API to create/update FCM token location
    """
    
    def post(self, request):
        fcm_token = request.data.get('fcm_token')
        lat = request.data.get('lat')
        long = request.data.get('long')
        
        if not fcm_token:
            return Response(
                {"error": "FCM token is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # This will update if exists, create if doesn't exist
        location_record, created = FCMTokenWiseUpdatedLatLon.objects.update_or_create(
            fcm_token=fcm_token,
            defaults={
                'lat': lat,
                'long': long
            }
        )
        
        message = "created" if created else "updated"
        
        return Response({
            "message": f"Location {message} successfully",
            "fcm_token": location_record.fcm_token,
            "lat": location_record.lat,
            "long": location_record.long
        }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)