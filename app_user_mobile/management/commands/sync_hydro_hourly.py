import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.timezone import make_aware
from data_load.models import Station, WaterLevelObservation
from datetime import datetime

class Command(BaseCommand):
    help = 'Syncs water level data from FFWC API by Hourly Range'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--update', action='store_true')
        group.add_argument('--fill_missing', action='store_true')
        parser.add_argument('--station_code', type=str, required=True)
        parser.add_argument('--hours', type=int, required=True)

    def handle(self, *args, **options):
        station_code = options['station_code']
        hours = options['hours']
        
        try:
            station = Station.objects.get(station_code=station_code)
        except Station.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Station {station_code} not found."))
            return

        url = f"{settings.FFWC_BASE_URL}/station_wise_data_by_hour_range.php"
        headers = {"Authorization": f"Bearer {settings.FFWC_TOKEN}"}
        payload = {"station_id": station_code, "hour": hours}

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=20)
            data_list = response.json().get('data', [])
            
            if not data_list:
                self.stdout.write(f"--- No hourly data for {station.name} ({station_code}) ---")
                return

            count = 0
            for item in data_list:
                aware_dt = make_aware(datetime.strptime(item['datetime'], '%d-%m-%Y %H:%M:%S'))
                value = item['value']

                if options['update']:
                    WaterLevelObservation.objects.update_or_create(
                        station_id=station, observation_date=aware_dt,
                        defaults={'water_level': value}
                    )
                    status_text = "Updated"
                else:
                    obj, created = WaterLevelObservation.objects.get_or_create(
                        station_id=station, observation_date=aware_dt,
                        defaults={'water_level': value}
                    )
                    status_text = "Inserted" if created else "Skipped"

                self.stdout.write(f"[{status_text}] {station.name} | {item['datetime']} | {value}m")
                count += 1
            self.stdout.write(self.style.SUCCESS(f"Finished {station.name}: {count} records."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"API Error for {station_code}: {str(e)}"))