from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, viewsets, generics, status,serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from userauth.models import UserAuthProfile, UserAuthProfileStations, UserAuthProfileIndianStations
from data_load.models import Station
from indian_stations.models import IndianStations
from .serializers import UserSerializer, RegisterSerializer,UserAuthProfileStationsSerializer
from urllib.parse import unquote

import requests
from decouple import config


from . import models  

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['firstName']=user.first_name
        token['lastName']=user.last_name
        token['dateJoined']=str(user.date_joined)
        token['lastLogin']=str(user.last_login)

        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class=MyTokenObtainPairSerializer


@api_view(['GET'])
def hello_auth(request):
    return Response({"Hello": "User"})

@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({"error": "Please provide both username and password"}, status=status.HTTP_400_BAD_REQUEST)
    user = authenticate(username=username, password=password)
    if not user:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    refresh = RefreshToken.for_user(user)
    serializer = UserSerializer(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": serializer.data
    }, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def userById(self, request, **kwargs):
        user_id = int(self.kwargs['user_id'])
        try:
            queryset = User.objects.filter(id=user_id).values().first()  # Use User instead of AuthUser
            if queryset:
                return Response(queryset)
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def userStatusByUser(self, request, **kwargs):
        username = unquote(self.kwargs['username'])
        try:
            queryset = User.objects.filter(username=username).values().first()  # Use User instead of AuthUser
            if queryset:
                user_status = {
                    'id': queryset['id'],
                    'is_active': queryset['is_active'],
                    'is_staff': queryset['is_staff'],
                    'is_superuser': queryset['is_superuser']
                }
                return Response(user_status)
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def getUserProfileId(self, request, **kwargs):
        user_id = int(self.kwargs['user_id'])
        try:
            profile_query = UserAuthProfile.objects.filter(user_id=user_id).values().first()
            if profile_query:
                profile_id = profile_query['id']
                return Response({'profile_id': profile_id})
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def userProfileByUserId(self, request, **kwargs):
        user_id = int(self.kwargs['user_id'])
        try:
            profile_query = UserAuthProfile.objects.filter(user_id=user_id).values().first()
            if not profile_query:
                return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
            profile_id = profile_query['id']
            ffwc_station_query = UserAuthProfileStations.objects.filter(profile_id=profile_id).values_list('station_id', flat=True)
            indian_station_query = UserAuthProfileIndianStations.objects.filter(profile_id=profile_id).values_list('indianstations_id', flat=True)
            list_of_user_station = {
                'ffwc_stations': list(ffwc_station_query),
                'indian_stations': list(indian_station_query),
            }
            return Response(list_of_user_station)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

user_by_id = UserViewSet.as_view({'get': 'userById'})
user_status = UserViewSet.as_view({'get': 'userStatusByUser'})
user_profile = UserViewSet.as_view({'get': 'userProfileByUserId'})
profile_id = UserViewSet.as_view({'get': 'getUserProfileId'})

class RegisterUserAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)



@api_view(['GET'])
def obtain_external_token(request):
    """
    Authenticate with external API using credentials from environment variables.
    Returns the token as a JSON response.
    Example: /api/obtain-token/
    """
    login_url = "https://swh.bwdb.gov.bd/auth/login"
    
    # Retrieve credentials from environment variables
    credentials = {
        "username": config("API_USERNAME"),
        "password": config("API_PASSWORD")
    }

    try:
        # Send POST request to external login endpoint
        response = requests.post(login_url, json=credentials, timeout=10)
        
        if response.status_code == 200:
            # Extract token from response
            token = response.json().get("token")
            if not token:
                logger.error("Token not found in response: %s", response.text)
                return Response({"error": "Token not found in response"}, status=400)
            return Response({"token": token}, status=200)
        else:
            logger.error("Failed to obtain token: %s, %s", response.status_code, response.text)
            return Response({"error": "Failed to authenticate", "details": response.text}, status=response.status_code)
    
    except requests.exceptions.RequestException as e:
        logger.error("Request failed: %s", str(e))
        return Response({"error": "Request failed", "details": str(e)}, status=500)

# class InsertUserStationView(generics.CreateAPIView):
#     permission_classes = (AllowAny,)
#     serializer_class = UserAuthProfileStationsSerializer





