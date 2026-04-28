import logging
from datetime import datetime, timedelta
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.db import transaction
from django.utils import timezone
from decimal import Decimal # Added for type checking if needed
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
    help = 'Generates alerts with shell tracing and fixed decimal/float math.'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, nargs='?', help='YYYY-MM-DD')

    def calculate_flood_level(self, water_level, danger_level):
        try:
            # Force everything to float to avoid TypeError
            wl = float(water_level) if water_level is not None else None
            dl = float(danger_level) if danger_level is not None else None
        except (ValueError, TypeError):
            return "na"

        if dl is None or dl <= 0 or wl is None or wl < 0:
            return "na"
        
        # Priority Logic
        if wl >= (dl + 1.0):
            return "severe"
        elif wl >= dl:
            return "flood"
        elif wl >= (dl - 0.5):
            return "warning"
        else:
            return "normal"

    def handle(self, *args, **options):
        date_str = options['date']
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        
        day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))

        # Get Peak Values
        qs = models.WaterLevelObservation.objects.filter(observation_date__range=(day_start, day_end))
        if not qs.exists():
            qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
        
        data_dict = {
            item['station_id__station_id']: item['max_wl'] 
            for item in qs.values('station_id__station_id').annotate(max_wl=Max('water_level'))
        }

        stations = models.Station.objects.filter(
            district__isnull=False, danger_level__isnull=False
        ).exclude(district='').values('station_id', 'district', 'danger_level', 'name')

        district_max_status = defaultdict(lambda: "na")
        severity_rank = {"severe": 4, "flood": 3, "warning": 2, "normal": 1, "na": 0}

        # --- SHELL TRACE START ---
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- TRACING NETROKONA STATIONS FOR {target_date} ---"))
        
        for station in stations:
            raw_dist = station['district'].lower().strip()
            norm_name = DISTRICT_NAME_MAPPING.get(raw_dist, raw_dist).lower().strip()
            
            sid = station['station_id']
            # Convert DL to float immediately
            dl = float(station['danger_level']) if station['danger_level'] else 0.0
            # Get WL and convert to float immediately
            raw_wl = data_dict.get(sid)
            wl = float(raw_wl) if raw_wl is not None else None
            
            status = self.calculate_flood_level(wl, dl)

            # Trace for Netrokona
            if norm_name == "netrokona":
                # Calculation is now float - float
                diff = (wl - dl) if wl is not None else 0.0
                color = self.style.ERROR if status in ['flood', 'severe'] else self.style.WARNING if status == 'warning' else self.style.SUCCESS
                
                self.stdout.write(
                    f"Station: {sid:<6} | Name: {station['name']:<15} | "
                    f"WL: {str(wl) if wl is not None else 'N/A':>6} | DL: {str(dl):>6} | Diff: {diff:>6.2f}m | "
                    f"Result: {color(status.upper())}"
                )

            if severity_rank[status] > severity_rank[district_max_status[norm_name]]:
                district_max_status[norm_name] = status

        self.stdout.write(self.style.MIGRATE_HEADING("--- END OF TRACE ---\n"))

        # Database Update
        with transaction.atomic():
            alert_map = {alert.alert_type: alert for alert in models.WaterlevelAlert.objects.all()}
            type_labels = {"severe": "Severe Flood", "flood": "Flood", "warning": "Warning", "normal": "Normal", "na": "N/A"}

            # Clear old records for this date
            models.DistrictFloodAlert.objects.filter(alert_date=target_date).delete()

            for dist_key, max_status in district_max_status.items():
                db_label = type_labels[max_status]
                alert_obj = alert_map.get(db_label)
                if alert_obj:
                    # Title case the key or use mapping to ensure Maulvibazar etc.
                    display_name = DISTRICT_NAME_MAPPING.get(dist_key, dist_key).title()
                    models.DistrictFloodAlert.objects.create(
                        alert_date=target_date,
                        district_name=display_name,
                        alert_type=alert_obj
                    )
        
        self.stdout.write(self.style.SUCCESS(f"Finished processing alerts for {target_date}"))