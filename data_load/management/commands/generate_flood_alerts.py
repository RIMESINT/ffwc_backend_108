import logging
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.db import transaction
from django.utils import timezone
from data_load import models

logger = logging.getLogger(__name__)

DISTRICT_NAME_MAPPING = {
    "moulvi bazar": "Maulvibazar",
    "moulvibazar": "Maulvibazar",
    "kishoreganj": "Kishorganj",
    "brahmmonbaria": "Brahmanbaria",
    "chapai nawabganj": "Chapainawabganj",
}

class Command(BaseCommand):
    help = 'Generates alerts filtered by API stations, replaces old records, and traces calculations.'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, nargs='?', help='YYYY-MM-DD')

    def calculate_flood_level(self, water_level, danger_level):
        try:
            wl = float(water_level) if water_level is not None else None
            dl = float(danger_level) if danger_level is not None else None
        except (ValueError, TypeError):
            return "na"
        if dl is None or dl <= 0 or wl is None or wl < 0:
            return "na"
        if wl > (dl + 1.0): return "severe"
        elif wl >= dl: return "flood"
        elif wl >= (dl - 0.5): return "warning"
        else: return "normal"

    def handle(self, *args, **options):
        # 1. Fetch permitted station IDs from the external API
        api_url = "http://0.0.0.0:8006/data_load/recent-observed/"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            permitted_station_ids = set(response.json().keys())
            self.stdout.write(self.style.SUCCESS(f"API Sync: Loaded {len(permitted_station_ids)} active stations."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch API data: {e}"))
            return

        date_str = options['date']
        base_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        
        # 2. Filter base stations by those in API
        stations = list(models.Station.objects.filter(
            station_id__in=permitted_station_ids,
            district__isnull=False, 
            danger_level__isnull=False
        ).exclude(district='').values('station_id', 'district', 'danger_level', 'name'))

        alert_map = {alert.alert_type: alert for alert in models.WaterlevelAlert.objects.all()}
        type_labels = {"severe": "Severe Flood", "flood": "Flood", "warning": "Warning", "normal": "Normal", "na": "N/A"}
        severity_rank = {"severe": 4, "flood": 3, "warning": 2, "normal": 1, "na": 0}

        # 3. Process 7-day window
        for day_offset in range(7):
            target_date = base_date + timedelta(days=day_offset)
            day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))

            if day_offset == 0:
                qs = models.WaterLevelObservation.objects.filter(observation_date__range=(day_start, day_end))
                if not qs.exists():
                    qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
            else:
                qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
            
            data_dict = {
                item['station_id__station_id']: item['max_wl'] 
                for item in qs.values('station_id__station_id').annotate(max_wl=Max('water_level'))
            }

            if not data_dict:
                self.stdout.write(self.style.NOTICE(f"No forecast/observed data for {target_date}, skipping."))
                continue

            district_max_status = {}
            district_station_contributions = defaultdict(list)

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- TRACING DATA FOR {target_date} ---"))

            for station in stations:
                sid = station['station_id']
                if sid not in data_dict:
                    continue 

                raw_dist = station['district'].lower().strip()
                norm_name = DISTRICT_NAME_MAPPING.get(raw_dist, raw_dist).lower().strip()
                
                dl = float(station['danger_level']) if station['danger_level'] else 0.0
                wl = float(data_dict[sid])
                status = self.calculate_flood_level(wl, dl)

                district_station_contributions[norm_name].append({
                    'name': station['name'], 'sid': sid, 'wl': wl, 'dl': dl, 'status': status
                })

                if norm_name not in district_max_status or severity_rank[status] > severity_rank[district_max_status[norm_name]]:
                    district_max_status[norm_name] = status

            # Print Trace Report
            for dist, contributions in district_station_contributions.items():
                self.stdout.write(f"District: {dist.title()} | Final Severity: {district_max_status[dist].upper()}")
                for c in contributions:
                    self.stdout.write(f"  -> Station: {c['name']:<15} | WL: {c['wl']:>6}m | DL: {c['dl']:>6}m | Result: {c['status'].upper()}")

            # Transactional Update (Replace existing)
            if district_max_status:
                with transaction.atomic():
                    models.DistrictFloodAlert.objects.filter(alert_date=target_date).delete()
                    for dist_key, max_status in district_max_status.items():
                        db_label = type_labels[max_status]
                        alert_obj = alert_map.get(db_label)
                        if alert_obj:
                            models.DistrictFloodAlert.objects.create(
                                alert_date=target_date,
                                district_name=DISTRICT_NAME_MAPPING.get(dist_key, dist_key).title(),
                                alert_type=alert_obj
                            )
                    self.stdout.write(self.style.SUCCESS(f"Saved {len(district_max_status)} district alerts for {target_date}."))