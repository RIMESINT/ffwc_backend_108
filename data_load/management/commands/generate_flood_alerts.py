import logging
from datetime import datetime, timedelta, date
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.db import transaction
from django.utils import timezone

from data_load import models

logger = logging.getLogger(__name__)

INTERNAL_FLOOD_LEVEL_KEYS = ["normal", "warning", "flood", "severe", "na"]

DISTRICT_NAME_MAPPING = {
    "moulvi bazar": "Maulvibazar",
    "moulvibazar": "Maulvibazar",
    "kishoreganj": "Kishorganj",
    "brahmmonbaria": "Brahmanbaria",
    "chapai nawabganj": "Chapainawabganj",
}

class Command(BaseCommand):
    help = 'Generates flood alerts. Shows DL and WL for debugging.'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, nargs='?', help='YYYY-MM-DD')

    def calculate_flood_level(self, water_level, danger_level):
        # Treat 0.0 as invalid/missing danger level to prevent false Severe alerts
        if danger_level is None or danger_level <= 0 or water_level is None or water_level < 0:
            return "na"
        
        if water_level >= danger_level + 1:
            return "severe"
        elif water_level >= danger_level:
            return "flood"
        elif water_level >= danger_level - 0.5:
            return "warning"
        else:
            return "normal"

    def handle(self, *args, **options):
        # 1. Fetch skip settings
        try:
            restricted_qs = models.DistrictFloodAlertAutoUpdate.objects.filter(
                auto_update=True
            ).values_list('district_name', flat=True)
            do_not_update_set = {name.lower().strip() for name in restricted_qs}
            
            # Ensure mapped names are also in the skip set
            for name in list(do_not_update_set):
                for key, val in DISTRICT_NAME_MAPPING.items():
                    if name == key or name == val.lower():
                        do_not_update_set.add(key)
                        do_not_update_set.add(val.lower())
        except Exception as e:
            logger.critical(f"Settings error: {e}")
            return

        # 2. Setup
        date_str = options['date']
        start_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
        
        all_waterlevel_alerts = models.WaterlevelAlert.objects.all()
        alert_map = {alert.alert_type: alert for alert in all_waterlevel_alerts}
        type_strings = {"severe": "Severe Flood", "flood": "Flood", "warning": "Warning", "normal": "Normal", "na": "N/A"}

        stations = models.Station.objects.filter(
            district__isnull=False, danger_level__isnull=False, station_id__isnull=False
        ).exclude(district='').values('station_id', 'district', 'danger_level', 'name')

        # 3. Processing
        for day_offset in range(1): # Limit to 1 day for debug if needed
            current_date = start_date + timedelta(days=day_offset)
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n>>> Processing Date: {current_date}"))
            
            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))

            # Fetch water levels
            qs = models.WaterLevelObservation.objects.filter(observation_date__range=(day_start, day_end))
            if not qs.exists():
                qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
            
            latest_data = qs.values('station_id__station_id').annotate(max_wl=Max('water_level'))
            data_dict = {item['station_id__station_id']: item['max_wl'] for item in latest_data}

            district_alerts = defaultdict(lambda: {"severe": 0, "flood": 0, "warning": 0, "normal": 0, "na": 0})

            for station in stations:
                raw_district = station['district'].lower().strip()
                normalized_name = DISTRICT_NAME_MAPPING.get(raw_district, station['district']).lower().strip()
                
                sid = station['station_id']
                status = "na"
                wl_val = "N/A"
                dl_val = float(station['danger_level'])

                if sid in data_dict and data_dict[sid] is not None:
                    wl_val = float(data_dict[sid])
                    status = self.calculate_flood_level(wl_val, dl_val)
                    district_alerts[normalized_name][status] += 1
                else:
                    district_alerts[normalized_name]["na"] += 1

                # Progress Print with WL and DL
                if status == "normal":
                    status_str = self.style.SUCCESS(status.upper())
                elif status in ["flood", "severe"]:
                    status_str = self.style.ERROR(status.upper())
                else:
                    status_str = status.upper()

                # ADDED DL TO PRINT FOR DEBUGGING
                self.stdout.write(
                    f"  Station: {sid:<6} | {station['name'][:12]:<12} | "
                    f"Dist: {normalized_name.capitalize():<15} | "
                    f"WL: {str(wl_val):>6} | DL: {str(dl_val):>6} | Status: {status_str}"
                )

            # 4. Save
            with transaction.atomic():
                for district_key, levels in district_alerts.items():
                    if district_key in do_not_update_set:
                        self.stdout.write(self.style.NOTICE(f"  [SKIP] {district_key.capitalize()} (auto_update=1)"))
                        continue

                    max_level = "na"
                    for lvl in ["severe", "flood", "warning", "normal"]:
                        if levels[lvl] > 0:
                            max_level = lvl
                            break
                    
                    db_label = type_strings[max_level]
                    alert_obj = alert_map.get(db_label)

                    if alert_obj:
                        final_name = DISTRICT_NAME_MAPPING.get(district_key, district_key).capitalize()
                        if final_name.lower() == "maulvibazar": final_name = "Maulvibazar"

                        models.DistrictFloodAlert.objects.update_or_create(
                            alert_date=current_date,
                            district_name=final_name,
                            defaults={'alert_type': alert_obj}
                        )
                        self.stdout.write(f"  [DB UPDATE] {final_name} -> {db_label}")