import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.timezone import make_aware
from data_load.models import RainfallStation, RainfallObservation
from datetime import datetime

class Command(BaseCommand):
    help = 'Syncs rainfall data from FFWC API by Hourly Range'

    def add_arguments(self, parser):
        # Mutual exclusion group for the sync mode
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--update', action='store_true', help='Update/Replace existing records')
        group.add_argument('--fill_missing', action='store_true', help='Only insert missing records')
        
        # Required arguments passed from the Admin View
        parser.add_argument('--station_code', type=str, required=True, help='Rainfall Station Code (e.g., CL128)')
        parser.add_argument('--hours', type=int, required=True, help='Number of hours to look back')

    def handle(self, *args, **options):
        station_code = options['station_code']
        hours = options['hours']
        
        # 1. Look up the Rainfall Station
        try:
            station = RainfallStation.objects.get(station_code=station_code)
        except RainfallStation.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Rainfall Station {station_code} not found."))
            return

        # 2. Setup FFWC Hourly Endpoint
        url = f"{settings.FFWC_BASE_URL}/station_wise_data_by_hour_range.php"
        headers = {"Authorization": f"Bearer {settings.FFWC_TOKEN}"}
        payload = {
            "station_id": station_code, 
            "hour": hours
        }

        try:
            # 3. Make the API Request
            response = requests.post(url, headers=headers, data=payload, timeout=20)
            response.raise_for_status() # Ensure we catch HTTP errors
            data_list = response.json().get('data', [])
            
            if not data_list:
                self.stdout.write(f"--- No hourly rainfall data for {station.name} ({station_code}) ---")
                return

            count = 0
            # 4. Iterate through data and save to RainfallObservation
            for item in data_list:
                # Convert API string to timezone-aware datetime
                naive_dt = datetime.strptime(item['datetime'], '%d-%m-%Y %H:%M:%S')
                aware_dt = make_aware(naive_dt)
                value = item['value']

                if options['update']:
                    # Mode: Update (Overwrites existing data for this specific timestamp)
                    obj, created = RainfallObservation.objects.update_or_create(
                        station_id=station,
                        observation_date=aware_dt,
                        defaults={'rainfall': value}
                    )
                    status_text = "Updated" if not created else "Inserted"
                else:
                    # Mode: Fill Missing (Skips if record already exists)
                    obj, created = RainfallObservation.objects.get_or_create(
                        station_id=station,
                        observation_date=aware_dt,
                        defaults={'rainfall': value}
                    )
                    status_text = "Inserted" if created else "Skipped"

                # 5. Write progress to stdout (captured by our Admin Console)
                self.stdout.write(
                    f"[{status_text}] {station.name} ({station_code}) | {item['datetime']} | {value}mm"
                )
                count += 1

            self.stdout.write(self.style.SUCCESS(f"Finished {station.name}: {count} rainfall records processed."))

        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Network error for {station_code}: {str(e)}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"System Error for {station_code}: {str(e)}"))