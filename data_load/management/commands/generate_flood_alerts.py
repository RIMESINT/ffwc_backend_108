import logging
from datetime import datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo  # Built-in since Python 3.9
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

# Administrative business rule caps to prevent unrepresentative alert levels
DISTRICT_MAX_ALLOWED_STATUS = {
    "gaibandha": "warning",   # Gaibandha should not be flood (Max allowed: Warning)
    "bagerhat": "warning",    # Bagerhat should not be flooded (Max allowed: Warning)
    "khulna": "warning",      # Khulna should not be flooded (Max allowed: Warning)
    "chattogram": "flood",    # Chattogram should not be severe flooded (Max allowed: Flood)
}

class Command(BaseCommand):
    help = 'Generates alerts: Day 0 uses observed (all stations), Days 1-6 use forecast (five_days_forecast=1 only).'

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
        
        # Exact threshold rules
        if wl > (dl + 1.0): return "severe"
        elif wl > dl: return "flood"
        elif wl > (dl - 0.5): return "warning"
        else: return "normal"

    def handle(self, *args, **options):
        # 1. Force the timezone context explicitly to Bangladesh Standard Time (BST)
        tz_dhaka = ZoneInfo("Asia/Dhaka")
        today_date = timezone.now().astimezone(tz_dhaka).date()
        
        date_str = options['date']
        base_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else today_date
        
        # 2. Fetch the exact baseline station pool used by StationViewSet
        self.stdout.write(self.style.WARNING("Loading base station pool matching StationViewSet..."))
        db_stations = models.Station.objects.all().order_by('station_serial_no')

        # 3. Build structural configuration map from valid Station metadata records
        station_meta_map = {}
        for station in db_stations:
            if not station.district or station.danger_level is None or station.station_id is None:
                continue

            raw_dist = station.district.lower().strip()
            norm_name = DISTRICT_NAME_MAPPING.get(raw_dist, raw_dist).lower().strip()
            
            station_meta_map[station.station_id] = {
                'station_id': station.station_id,
                'name': station.name,
                'danger_level': station.danger_level,
                'district_name': norm_name,
                'display_name': station.district.strip().title(),
                'lat': station.latitude,
                'lon': station.longitude,
                'five_days_forecast': getattr(station, 'five_days_forecast', 0)  # Captured to filter inside loop
            }
        
        self.stdout.write(self.style.SUCCESS(f"Successfully mapped {len(station_meta_map)} alert-ready stations."))

        alert_map = {alert.alert_type: alert for alert in models.WaterlevelAlert.objects.all()}
        type_labels = {
            "severe": "Severe Flood", 
            "flood": "Flood", 
            "warning": "Warning", 
            "normal": "Normal"
        }
        severity_rank = {"severe": 4, "flood": 3, "warning": 2, "normal": 1, "na": 0}

        # Fetch the baseline global database update tracking date entry
        most_recent_entry = models.FfwcLastUpdateDate.objects.order_by('-last_update_date').first()
        last_update_date = most_recent_entry.last_update_date if most_recent_entry else None

        # 4. Step through the 7-day timeline execution window
        for day_offset in range(7):
            target_date = base_date + timedelta(days=day_offset)
            query_date = target_date
            
            # Formulate chronological target database query paths
            if target_date <= today_date:
                use_observed = True
                if target_date == today_date and last_update_date != today_date:
                    if last_update_date:
                        query_date = last_update_date
                        mode_label = f"OBSERVED (FALLBACK TO {last_update_date})"
                    else:
                        mode_label = "OBSERVED"
                else:
                    mode_label = "OBSERVED"
            else:
                use_observed = False
                mode_label = "FORECAST"

            day_start = timezone.make_aware(datetime.combine(query_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(query_date, datetime.max.time()))

            if use_observed:
                qs = models.WaterLevelObservation.objects.filter(observation_date__range=(day_start, day_end))
            else:
                qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))
            
            data_dict = {
                item['station_id__station_id']: item['max_wl'] 
                for item in qs.values('station_id__station_id').annotate(max_wl=Max('water_level'))
            }

            if not data_dict:
                self.stdout.write(self.style.NOTICE(f"No metric source entries found for {target_date} ({mode_label}), skipping."))
                continue

            district_max_status = {}
            district_display_names = {}
            district_station_contributions = defaultdict(list)

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- TRACING DATA FOR {target_date} ({mode_label}) ---"))

            for sid, meta in station_meta_map.items():
                # CRITICAL CHANGE: Only apply five_days_forecast filter for future days (Forecast Mode)
                if not use_observed and meta['five_days_forecast'] != 1:
                    continue

                norm_dist = meta['district_name']
                district_display_names[norm_dist] = meta['display_name']

                wl_val = data_dict.get(sid)
                dl = float(meta['danger_level'])
                
                if wl_val is not None:
                    wl = float(wl_val)
                    raw_status = self.calculate_flood_level(wl, dl)
                    status = raw_status

                    # Intercept mathematical output and apply regional ceiling caps
                    if norm_dist in DISTRICT_MAX_ALLOWED_STATUS:
                        max_allowed = DISTRICT_MAX_ALLOWED_STATUS[norm_dist]
                        if severity_rank[raw_status] > severity_rank[max_allowed]:
                            status = max_allowed
                else:
                    wl = None
                    status = "na"

                district_station_contributions[norm_dist].append({
                    'name': meta['name'], 
                    'sid': sid, 
                    'wl': wl, 
                    'dl': dl, 
                    'status': status,
                    'lat': meta['lat'],
                    'lon': meta['lon']
                })

                if status != "na":
                    if norm_dist not in district_max_status or severity_rank[status] > severity_rank[district_max_status[norm_dist]]:
                        district_max_status[norm_dist] = status

            # Output trace verification reporting logs
            for dist, contributions in district_station_contributions.items():
                final_status = district_max_status.get(dist, "N/A")
                self.stdout.write(f"District: {district_display_names[dist]} | Combined Max State: {final_status.upper()}")
                for c in contributions:
                    wl_display = f"{c['wl']:>6.2f}m" if c['wl'] is not None else "   N/A"
                    self.stdout.write(
                        f"  -> Station: {c['name']:<15} ({c['sid']}) | Lat/Lon: ({c['lat']:.3f}, {c['lon']:.3f}) | "
                        f"WL: {wl_display} | DL: {c['dl']:>6.2f}m | Result: {c['status'].upper()}"
                    )

            # 5. Transactional Database Commits
            with transaction.atomic():
                models.DistrictFloodAlert.objects.filter(alert_date=target_date).delete()
                
                created_count = 0
                for dist_key, max_status in district_max_status.items():
                    if max_status in type_labels:
                        db_label = type_labels[max_status]
                        alert_obj = alert_map.get(db_label)
                        
                        if alert_obj:
                            models.DistrictFloodAlert.objects.create(
                                alert_date=target_date,
                                district_name=district_display_names[dist_key],
                                alert_type=alert_obj
                            )
                            created_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"Successfully processed & saved {created_count} alerts for {target_date}."))

        self.stdout.write(self.style.SUCCESS(f"\nAll 7 days have been successfully populated into the system context."))