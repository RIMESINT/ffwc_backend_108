from datetime import datetime, timedelta

from django.http import JsonResponse

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import IndianStations, IndianWaterLevelObservations
from .serializers import IndianStationsSerializer, IndianWaterLevelObservationsSerializer

from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import APIException






class IndianStationsViewSet(viewsets.ModelViewSet):
    queryset = IndianStations.objects.all()
    serializer_class = IndianStationsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class IndianWaterLevelObservationsViewSet(viewsets.ModelViewSet):
    queryset = IndianWaterLevelObservations.objects.all()
    serializer_class = IndianWaterLevelObservationsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class TransboundaryRiverDataView(generics.ListAPIView):
    serializer_class = IndianWaterLevelObservationsSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        station_code = self.kwargs['st_code']
        end_date_str = self.kwargs.get('end_date') # Use .get() to safely check for optional parameter

        filter_start_date = None

        if end_date_str:
            # If end_date is provided in the URL
            try:
                # Parse the date string into a datetime object
                # Subtract 15 days from this provided date
                filter_start_date = datetime.strptime(end_date_str, '%Y-%m-%d') - timedelta(days=15)
            except ValueError:
                # Raise an error if the provided date format is invalid
                raise APIException("Invalid date format. Please use YYYY-MM-DD.")
        else:
            # If end_date is NOT provided, calculate based on the latest record
            try:
                latest_record_time = IndianWaterLevelObservations.objects.latest('data_time').data_time
                # Subtract 15 days from the latest record's data_time
                filter_start_date = latest_record_time - timedelta(days=15)
            except IndianWaterLevelObservations.DoesNotExist:
                # If no observations exist at all, return an empty queryset
                return IndianWaterLevelObservations.objects.none()

        # Ensure filter_start_date is set before filtering
        if filter_start_date is None:
            return IndianWaterLevelObservations.objects.none()

        # Filter the queryset
        queryset = IndianWaterLevelObservations.objects.filter(
            station__station_code=station_code,
            data_time__gte=filter_start_date
        ).order_by('data_time')

        return queryset
    
    
import requests
def get_indian_station_water_data(request, station_code,current_date): 
    """
    Fetches water level data from the external API, transforms it,
    and returns it as a JSON response, associating with station_id from DB.
    The station_code is now dynamic, taken from the URL.
    """
    api_url = f"https://cwcdata.ffwc.gov.bd/cwcdata/st_data.php?st_id={station_code}" # Use the dynamic station_code

    try:
        # Fetch the corresponding IndianStations object from your database first
        indian_station = IndianStations.objects.get(station_code=station_code) # Use the dynamic station_code
        station_id_from_db = indian_station.id
    except IndianStations.DoesNotExist:
        return JsonResponse({"error": f"Station with code '{station_code}' not found in local database."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Error accessing local database for station '{station_code}': {e}"}, status=500)

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        raw_data = response.json()
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"Error fetching data from external API for station '{station_code}': {e}"}, status=500)
    except ValueError:
        return JsonResponse({"error": f"Invalid JSON response from external API for station '{station_code}'"}, status=500)
    except Exception as e:
        # Catch any other unexpected errors during API call or JSON parsing
        return JsonResponse({"error": f"An unexpected error occurred processing external API data for station '{station_code}': {e}"}, status=500)

    transformed_data = []
    for entry in raw_data:
        try:
            data_time_str = entry['id']['dataTime']
            if not data_time_str.endswith('Z'):
                # Assuming the external API's time is UTC, or you want to treat it as such.
                data_time_iso = datetime.fromisoformat(data_time_str).isoformat(timespec='seconds') + 'Z'
            else:
                data_time_iso = data_time_str

            transformed_data.append({
                "station_id": station_id_from_db, # Use the ID from your local DB
                "station_code": entry['stationCode'],
                "data_time": data_time_iso,
                "waterlevel": f"{entry['dataValue']:.2f}" # Format to two decimal places
            })
        except KeyError as e:
            print(f"Warning: Skipping entry due to missing key in external API response for station '{station_code}': {e} in {entry}")
            continue
        except (TypeError, ValueError) as e:
            print(f"Warning: Skipping entry due to data conversion error in external API response for station '{station_code}': {e} in {entry}")
            continue
        except Exception as e:
            # Catch any other unexpected errors during data transformation
            print(f"Warning: An unexpected error occurred during data transformation for station '{station_code}': {e} in {entry}")
            continue

    return JsonResponse(transformed_data, safe=False)