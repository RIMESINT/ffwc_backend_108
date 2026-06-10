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
    help = 'Generates a 7-day window of alerts with shell tracing and fixed decimal/float math.'

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
        base_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        
        # Performance optimization: Query assets that do not change over date metrics outside the loop
        stations = list(models.Station.objects.filter(
            district__isnull=False, danger_level__isnull=False
        ).exclude(district='').values('station_id', 'district', 'danger_level', 'name'))

        alert_map = {alert.alert_type: alert for alert in models.WaterlevelAlert.objects.all()}
        type_labels = {"severe": "Severe Flood", "flood": "Flood", "warning": "Warning", "normal": "Normal", "na": "N/A"}
        severity_rank = {"severe": 4, "flood": 3, "warning": 2, "normal": 1, "na": 0}

        self.stdout.write(self.style.WARNING(f"Starting 7-day calculation sequence from: {base_date}\n"))

        # Loop through a 7-day timeline window
        for day_offset in range(7):
            target_date = base_date + timedelta(days=day_offset)
            
            day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))

            # Priority Engine:
            # Day 0 (Base Date): Prefer Observed readings. Fall back to forecasts if unavailable.
            # Day 1-6 (Future): Target the Forecast database explicitly.
            if day_offset == 0:
                qs = models.WaterLevelObservation.objects.filter(observation_date__range=(day_start, day_end))
                if not qs.exists():
                    qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
            else:
                qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
            
            # Map structural inputs 
            data_dict = {
                item['station_id__station_id']: item['max_wl'] 
                for item in qs.values('station_id__station_id').annotate(max_wl=Max('water_level'))
            }

            # Reset severity data mapping cleanly for each iteration date tracking
            district_max_status = defaultdict(lambda: "na")

            # --- SHELL TRACE START ---
            self.stdout.write(self.style.MIGRATE_HEADING(f"--- TRACING NETROKONA STATIONS FOR {target_date} ---"))
            
            for station in stations:
                raw_dist = station['district'].lower().strip()
                norm_name = DISTRICT_NAME_MAPPING.get(raw_dist, raw_dist).lower().strip()
                
                sid = station['station_id']
                dl = float(station['danger_level']) if station['danger_level'] else 0.0
                raw_wl = data_dict.get(sid)
                wl = float(raw_wl) if raw_wl is not None else None
                
                status = self.calculate_flood_level(wl, dl)

                # Trace logs for Netrokona
                if norm_name == "netrokona":
                    diff = (wl - dl) if wl is not None else 0.0
                    color = self.style.ERROR if status in ['flood', 'severe'] else self.style.WARNING if status == 'warning' else self.style.SUCCESS
                    
                    self.stdout.write(
                        f"Station: {sid:<6} | Name: {station['name']:<15} | "
                        f"WL: {str(wl) if wl is not None else 'N/A':>6} | DL: {str(dl):>6} | Diff: {diff:>6.2f}m | "
                        f"Result: {color(status.upper())}"
                    )

                if severity_rank[status] > severity_rank[district_max_status[norm_name]]:
                    district_max_status[norm_name] = status

            self.stdout.write(self.style.MIGRATE_HEADING(f"--- END OF TRACE FOR {target_date} ---\n"))

            # Isolated transactional database updates per processing date loop
            with transaction.atomic():
                # Clear old records specifically for this targeted date iteration block
                models.DistrictFloodAlert.objects.filter(alert_date=target_date).delete()

                created_count = 0
                for dist_key, max_status in district_max_status.items():
                    db_label = type_labels[max_status]
                    alert_obj = alert_map.get(db_label)
                    if alert_obj:
                        display_name = DISTRICT_NAME_MAPPING.get(dist_key, dist_key).title()
                        models.DistrictFloodAlert.objects.create(
                            alert_date=target_date,
                            district_name=display_name,
                            alert_type=alert_obj
                        )
                        created_count += 1
            
                self.stdout.write(self.style.SUCCESS(f"Successfully processed & saved {created_count} alerts for {target_date}."))

        self.stdout.write(self.style.SUCCESS(f"\nAll 7 days have been successfully populated into the system context."))