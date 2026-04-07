import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.timezone import make_aware
from data_load.models import RainfallStation, RainfallObservation
from datetime import datetime

class Command(BaseCommand):
    help = 'Syncs rainfall data from FFWC API'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--update', action='store_true')
        group.add_argument('--fill_missing', action='store_true')
        
        parser.add_argument('--station_code', type=str, required=True)
        parser.add_argument('--from_date', type=str, required=True)
        parser.add_argument('--to_date', type=str, required=True)

    def handle(self, *args, **options):
        station_code = options['station_code']
        from_date = options['from_date']
        to_date = options['to_date']
        
        try:
            station = RainfallStation.objects.get(station_code=station_code)
        except RainfallStation.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Rainfall Station {station_code} not found."))
            return

        url = f"{settings.FFWC_BASE_URL}/station_wise_data_by_date_range.php"
        headers = {"Authorization": f"Bearer {settings.FFWC_TOKEN}"}
        payload = {"station_id": station_code, "from_date": from_date, "to_date": to_date}

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=20)
            data_list = response.json().get('data', [])
            
            if not data_list:
                self.stdout.write(f"--- No rainfall data for {station.name} ({station_code}) ---")
                return

            if options['update']:
                RainfallObservation.objects.filter(
                    station_id=station,
                    observation_date__date__range=[from_date, to_date]
                ).delete()

            count = 0
            for item in data_list:
                aware_dt = make_aware(datetime.strptime(item['datetime'], '%d-%m-%Y %H:%M:%S'))
                value = item['value']

                if options['update']:
                    RainfallObservation.objects.create(
                        station_id=station,
                        observation_date=aware_dt,
                        rainfall=value
                    )
                    status_text = "Inserted"
                else:
                    obj, created = RainfallObservation.objects.update_or_create(
                        station_id=station,
                        observation_date=aware_dt,
                        defaults={'rainfall': value}
                    )
                    status_text = "Created" if created else "Updated"

                self.stdout.write(f"[{status_text}] {station.name} | {item['datetime']} | {value}mm")
                count += 1

            self.stdout.write(self.style.SUCCESS(f"Finished {station.name}: {count} rainfall records."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"API Error for {station_code}: {str(e)}"))