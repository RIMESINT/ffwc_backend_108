import requests
import json
import time
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import UpdateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
import paramiko
import shlex

from data_load.models import RainfallStation, RainfallObservation
from django.utils.dateparse import parse_date


from django.conf import settings
from django.http import JsonResponse

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


# class SendOTPView(APIView):
#     def post(self, request):
#         serializer = SendOTPSerializer(data=request.data)
#         if serializer.is_valid():
#             mobile_number = serializer.validated_data['mobile_number']
            
#             mobile_user_count = MobileAuthUser.objects.filter(
#                 mobile_number = mobile_number
#             ).count()
#             if mobile_user_count < 1:
#                 return Response({
#                     'message': f'{mobile_number} is unauthorized. Please contact with Admin',  
#                 }, status=status.HTTP_200_OK)
            
#             # Generate OTP
#             otp_instance = OTP.generate_otp(mobile_number)
            
#             with open(ECMWF_BASE_URL / 'env.json', 'r') as envf:
#                 env_ = json.load(envf)
#             BULK_SMS_CONF = env_['bulk_sms_send']
#             url = BULK_SMS_CONF["URL"]    
#             api_key = BULK_SMS_CONF["API_KEY"]    
#             senderid = BULK_SMS_CONF["SENDER_ID"] 
            
#             sms_client = BulkSMSClient(
#                 api_key=api_key,
#                 senderid=senderid,
#                 url=url
#             )

#             # response = sms_client.send_otp("017XXXXXXXX", "123456")
#             response = sms_client.send_otp(mobile_number, otp_instance.otp)
#             response_dict = json.loads(response)
#             # print(response_dict)
            
#             return Response({
#                 'message': 'OTP sent successfully',
#                 'otp': otp_instance.otp,  # Remove this in production
#                 'sender_response': response_dict,  # Remove this in production
#             }, status=status.HTTP_200_OK)
            
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SendOTPView(APIView):
    def gen_client_trans_id(self):
        return f"TXN{int(time.time() * 1000)}"

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mobile_number = serializer.validated_data['mobile_number']
        
        if MobileAuthUser.objects.filter(mobile_number=mobile_number).count() < 1:
            return Response({
                'message': f'{mobile_number} is unauthorized.'
            }, status=status.HTTP_403_FORBIDDEN)


        otp_instance = OTP.generate_otp(mobile_number)
        otp_text = f"Your OTP is: {otp_instance.otp}"

   
        try:
            with open(ECMWF_BASE_URL / 'env.json', 'r') as envf:
                env_ = json.load(envf)
            gp_conf = env_['gp_sms_conf']
            ssh_conf = env_['bdserver_site_235_ssh_conf']
        except Exception as e:
            return Response({'error': str(e)}, status=500)


        payload_json = json.dumps({
            "username": gp_conf["username"],
            "password": gp_conf["password"],
            "apicode": gp_conf["apicode"],
            "msisdn": [str(mobile_number)],
            "countrycode": "880",
            "cli": gp_conf["cli"],
            "messagetype": "1",
            "message": otp_text,
            "clienttransid": self.gen_client_trans_id(),
            "bill_msisdn": gp_conf["bill_msisdn"],
            "tran_type": gp_conf["tran_type"],
            "request_type": gp_conf["request_type"],
            "rn_code": gp_conf["rn_code"]
        })


        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=ssh_conf["HOST"],
                username=ssh_conf["USER"],
                password=ssh_conf["PASSWORD"],
                look_for_keys=False,
                allow_agent=False,
                timeout=20
            )

            curl_cmd = f"curl -s -X POST {gp_conf['url']} -H 'Content-Type: application/json' -d {shlex.quote(payload_json)}"
            stdin, stdout, stderr = ssh.exec_command(curl_cmd)
            response_raw = stdout.read().decode().strip()
            ssh.close()

            if not response_raw:
                return Response({'message': 'No response from Gateway'}, status=502)

            gp_data = json.loads(response_raw)
            status_info = gp_data.get('statusInfo', {})
            

            raw_code = status_info.get('statusCode', '0')
            description = status_info.get('errordescription', '')
            

            is_success = (raw_code == "1000")
            
            mapped_response = {
                "response_code": int(raw_code),
                "success_message": description if is_success else "",
                "error_message": "" if is_success else description
            }

            return Response({
                "message": "OTP sent successfully" if is_success else "OTP sending failed",
                "otp": otp_instance.otp,
                "sender_response": mapped_response
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": "Bridge connection error",
                "sender_response": {
                    "response_code": 500,
                    "success_message": "",
                    "error_message": str(e)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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





# Leotech-Rimes-SMS - API VIEW


def get_hydro_data(request):
    """
    Fetches Hydro Data. 
    URL format: /api/hydro-data/?station_id=SW351&from_date=2026-03-01&to_date=2026-03-15
    """
    # 1. Capture query parameters
    station_id = request.GET.get('station_id')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # 2. Validation: Ensure no parameters are missing
    if not all([station_id, from_date, to_date]):
        return JsonResponse({
            "error": "Missing required query parameters",
            "required": ["station_id", "from_date", "to_date"]
        }, status=400)

    # 3. Setup External Request
    url = f"{settings.FFWC_BASE_URL}/station_wise_data_by_date_range.php"
    headers = {"Authorization": f"Bearer {settings.FFWC_TOKEN}"}
    payload = {
        "station_id": station_id,
        "from_date": from_date,
        "to_date": to_date
    }

    try:
        # FFWC expects form-data (data=payload)
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        return JsonResponse(response.json(), safe=False)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": "FFWC API connection failed", "details": str(e)}, status=502)

def get_hydro_hourly_data(request):
    """
    Acts as a proxy to fetch hourly data from FFWC API.
    URL format: /api/hydro-hourly/?station_id=SW351&hour=72
    """
    # 1. Capture query parameters from the user's request
    station_id = request.GET.get('station_id')
    hour = request.GET.get('hour', 72) # Default to 72 if not provided

    # 2. Validation
    if not station_id:
        return JsonResponse({
            "error": "Missing required query parameter: station_id"
        }, status=400)

    # 3. Setup External Request to FFWC
    # Using the hourly endpoint provided in your Postman example
    url = f"{settings.FFWC_BASE_URL}/station_wise_data_by_hour_range.php"
    headers = {"Authorization": f"Bearer {settings.FFWC_TOKEN}"}
    payload = {
        "station_id": station_id,
        "hour": hour
    }

    try:
        # Send POST request to FFWC (FFWC APIs usually expect data/form-data)
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        
        # Return the exact JSON response from FFWC back to the user
        return JsonResponse(response.json(), safe=False)
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            "error": "FFWC API connection failed", 
            "details": str(e)
        }, status=502)


def get_sms_list(request):
    """
    Fetches SMS list.
    URL format: /api/sms-list/?source=01751330394&datefrom=2025-01-01&dateto=2026-04-08
    """
    # 1. Capture query parameters
    source = request.GET.get('source')
    date_from = request.GET.get('datefrom')
    date_to = request.GET.get('dateto')

    # 2. Validation
    if not all([source, date_from, date_to]):
        return JsonResponse({
            "error": "Missing required query parameters",
            "required": ["source", "datefrom", "dateto"]
        }, status=400)

    # 3. Setup External Request
    url = f"{settings.SMS_BASE_URL}/sms/list"
    payload = {
        "userid": settings.SMS_USERID,
        "apikey": settings.SMS_APIKEY,
        "source": source,
        "datefrom": date_from,
        "dateto": date_to
    }

    try:
        # SMS API expects raw JSON (json=payload)
        response = requests.post(url, json=payload, timeout=15)
        return JsonResponse(response.json(), safe=False)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": "SMS Gateway unreachable", "details": str(e)}, status=502)




