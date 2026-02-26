from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from userauth.models import UserAuthProfile, UserAuthProfileStations, UserAuthProfileIndianStations
from data_load.models import Station
from indian_stations.models import IndianStations

# Serializer for User Details
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')

# Serializer for Registration
class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=User.objects.all())])
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'is_active': {'read_only': True},
            'is_staff': {'read_only': True},
            'is_superuser': {'read_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            is_active=False  # Match other project
        )
        user.set_password(validated_data['password'])
        user.save()
        UserAuthProfile.objects.create(user=user)  # Create profile
        return user


# Serializer for Stations
class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ('id', 'station_id', 'name')

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    userProfileStations = serializers.SerializerMethodField()
    userProfileIndianStations = serializers.SerializerMethodField()

    class Meta:
        model = UserAuthProfile
        fields = ('id', 'user', 'userProfileStations', 'userProfileIndianStations')

    def get_userProfileStations(self, obj):
        station_ids = UserAuthProfileStations.objects.filter(profile_id=obj.id).values_list('station_id', flat=True)
        stations = Station.objects.filter(id__in=station_ids)
        return StationSerializer(stations, many=True).data

    def get_userProfileIndianStations(self, obj):
        indian_station_ids = UserAuthProfileIndianStations.objects.filter(profile_id=obj.id).values_list('indianstations_id', flat=True)
        indian_stations = IndianStations.objects.filter(id__in=indian_station_ids)
        return IndianStationsSerializer(indian_stations, many=True).data
        

class UserAuthProfileStationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAuthProfileStations
        fields = ('id', 'profile_id', 'station_id')

class UserAuthProfileIndianStationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAuthProfileIndianStations
        fields = ('id', 'profile_id', 'indianstations_id')