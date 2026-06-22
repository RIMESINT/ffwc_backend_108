import logging
from datetime import datetime, timedelta
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import Max, Sum, F
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
    help = 'Generates 7-day alerts using Forecasts with Trend Fallback (WL Rise + Rainfall).'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, nargs='?', help='YYYY-MM-DD')

    def calculate_flood_level(self, water_level, danger_level):
        try:
            wl, dl = float(water_level), float(danger_level)
        except (ValueError, TypeError): return "na"
        if dl <= 0 or wl < 0: return "na"
        
        if wl >= (dl + 1.0): return "severe"
        elif wl >= dl: return "flood"
        elif wl >= (dl - 0.5): return "warning"
        return "normal"

    def handle(self, *args, **options):
        # 1. Setup Dates
        date_str = options['date']
        start_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        
        # 2. Pre-fetch Data for Trend Analysis
        # Get last 24h rainfall per district
        yesterday = timezone.now() - timedelta(days=1)
        rain_data = models.RainfallObservation.objects.filter(observation_date__gte=yesterday).values('station_id__district').annotate(total_rf=Sum('rainfall'))
        rain_map = {item['station_id__district'].lower().strip(): float(item['total_rf']) for item in rain_data if item['station_id__district']}

        # Get all districts from Rainfall Stations to ensure coverage
        raw_districts = models.RainfallStation.objects.values_list('district', flat=True).distinct()
        master_district_list = sorted(list(set(DISTRICT_NAME_MAPPING.get(d.lower().strip(), d).title() for d in raw_districts if d)))

        # 3. Cache Alert Types
        alert_map = {alert.alert_type: alert for alert in models.WaterlevelAlert.objects.all()}
        type_labels = {"severe": "Severe Flood", "flood": "Flood", "warning": "Warning", "normal": "Normal", "na": "N/A"}
        severity_rank = {"severe": 4, "flood": 3, "warning": 2, "normal": 1, "na": 0}

        # 4. Loop 7 Days
        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            self.stdout.write(f"\nProcessing {current_date}...")

            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))

            # Fetch primary WL data
            if day_offset == 0:
                qs = models.WaterLevelObservation.objects.filter(observation_date__range=(day_start, day_end))
            else:
                qs = models.WaterLevelForecast.objects.filter(forecast_date__range=(day_start, day_end))

            data_dict = {item['station_id__station_id']: item['max_wl'] for item in qs.values('station_id__station_id').annotate(max_wl=Max('water_level'))}

            # 5. Process Districts
            stations = models.Station.objects.filter(district__isnull=False, danger_level__isnull=False).values('station_id', 'district', 'danger_level')
            district_max_status = defaultdict(lambda: "na")

            for st in stations:
                raw_dist = st['district'].lower().strip()
                norm_name = DISTRICT_NAME_MAPPING.get(raw_dist, raw_dist).title()
                
                wl = data_dict.get(st['station_id'])
                
                if wl is not None:
                    # Case A: We have data (Observed or Forecast)
                    status = self.calculate_flood_level(wl, st['danger_level'])
                elif day_offset > 0:
                    # Case B: Future Date with NO Forecast data -> Check Trends
                    district_rain = rain_map.get(raw_dist, 0.0)
                    
                    # Trend Logic: If Rainfall > 100mm in last 24h, set Warning
                    if district_rain > 100:
                        status = "warning"
                    else:
                        status = "normal" # Default to Normal instead of N/A
                else:
                    status = "na"

                if severity_rank[status] > severity_rank[district_max_status[norm_name]]:
                    district_max_status[norm_name] = status

            # 6. Database Commit
            with transaction.atomic():
                models.DistrictFloodAlert.objects.filter(alert_date=current_date).delete()
                for display_name in master_district_list:
                    status_key = district_max_status.get(display_name, "normal")
                    alert_obj = alert_map.get(type_labels[status_key])
                    if alert_obj:
                        models.DistrictFloodAlert.objects.create(
                            alert_date=current_date,
                            district_name=display_name,
                            alert_type=alert_obj
                        )
        
        self.stdout.write(self.style.SUCCESS("Success: Generated alerts with trend fallback."))