import logging
from datetime import datetime, timedelta
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.db import transaction
from django.utils import timezone

from data_load import models

logger = logging.getLogger(__name__)

# District mapping for consistency
DISTRICT_NAME_MAPPING = {
    "moulvi bazar": "Maulvibazar",
    "moulvibazar": "Maulvibazar",
    "kishoreganj": "Kishorganj",
    "brahmmonbaria": "Brahmanbaria",
    "chapai nawabganj": "Chapainawabganj",
}

class Command(BaseCommand):
    help = 'Generates 7-day alerts: Observed for today, Forecast for future dates.'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, nargs='?', help='Start Date YYYY-MM-DD (Defaults to today)')

    def calculate_flood_level(self, water_level, danger_level):
        """
        Severe:  WL >= DL + 1.0m
        Flood:   WL >= DL
        Warning: DL - 0.5m <= WL < DL
        Normal:  WL < DL - 0.5m
        """
        try:
            wl = float(water_level) if water_level is not None else None
            dl = float(danger_level) if danger_level is not None else None
        except (ValueError, TypeError):
            return "na"

        if dl is None or dl <= 0 or wl is None or wl < 0:
            return "na"
        
        if wl >= (dl + 1.0):
            return "severe"
        elif wl >= dl:
            return "flood"
        elif wl >= (dl - 0.5):
            return "warning"
        else:
            return "normal"

    def handle(self, *args, **options):
        # 1. Setup Start Date
        date_str = options['date']
        start_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        
        # 2. Identify all districts to ensure full coverage in the API
        # We fetch from WaterLevel Stations
        all_districts = models.Station.objects.filter(district__isnull=False).exclude(district='').values_list('district', flat=True).distinct()
        master_district_list = sorted(list(set(
            DISTRICT_NAME_MAPPING.get(d.lower().strip(), d).title() for d in all_districts
        )))

        # Cache Alert Types and severity ranking
        alert_map = {alert.alert_type: alert for alert in models.WaterlevelAlert.objects.all()}
        type_labels = {"severe": "Severe Flood", "flood": "Flood", "warning": "Warning", "normal": "Normal", "na": "N/A"}
        severity_rank = {"severe": 4, "flood": 3, "warning": 2, "normal": 1, "na": 0}

        # 3. Loop through 7-Day Window
        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            is_today = (current_date == timezone.now().date())
            
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"\n>>> Date: {current_date} | Mode: {'OBSERVED' if is_today else 'FORECAST'}"
            ))

            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))

            # --- STRICT DATA SEPARATION ---
            if is_today:
                # Strictly Observed for today
                qs = models.WaterLevelObservation.objects.filter(observation_date__range=(day_start, day_end))
            else:
                # Strictly Forecast for future dates
                qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
            
            # Aggregate Peak WL for the day
            data_dict = {
                item['station_id__station_id']: item['max_wl'] 
                for item in qs.values('station_id__station_id').annotate(max_wl=Max('water_level'))
            }

            # 4. Process Stations by District
            stations = models.Station.objects.filter(
                district__isnull=False, danger_level__isnull=False
            ).exclude(district='').values('station_id', 'district', 'danger_level')

            district_max_status = defaultdict(lambda: "na")

            for station in stations:
                raw_dist = station['district'].lower().strip()
                norm_name = DISTRICT_NAME_MAPPING.get(raw_dist, raw_dist).title()
                
                wl = data_dict.get(station['station_id'])
                status = self.calculate_flood_level(wl, station['danger_level'])
                
                # Highest Severity Logic
                if severity_rank[status] > severity_rank[district_max_status[norm_name]]:
                    district_max_status[norm_name] = status

            # 5. Database Commit
            with transaction.atomic():
                # Refresh data for the current_date
                models.DistrictFloodAlert.objects.filter(alert_date=current_date).delete()

                created_count = 0
                for display_name in master_district_list:
                    # Logic: If no data was found, we use 'na' for future dates
                    # If you prefer 'normal', change status_key default here.
                    status_key = district_max_status.get(display_name, "na")
                    
                    alert_obj = alert_map.get(type_labels[status_key])
                    if alert_obj:
                        models.DistrictFloodAlert.objects.create(
                            alert_date=current_date,
                            district_name=display_name,
                            alert_type=alert_obj
                        )
                        created_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"   Saved {created_count} districts."))

        self.stdout.write(self.style.SUCCESS("\nGeneration complete: Strictly Observed (Today) + Forecast (Future)."))