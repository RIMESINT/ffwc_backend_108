import logging
from datetime import datetime, timedelta, date
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.db import transaction

# Make sure all necessary models are imported
from data_load import models
logger = logging.getLogger(__name__)

INTERNAL_FLOOD_LEVEL_KEYS = ["normal", "warning", "flood", "severe", "na"]

class Command(BaseCommand):
    help = 'Generates and stores district flood alerts for a given date. Defaults to the current date if no date is provided.'

    def add_arguments(self, parser):
        parser.add_argument(
            'date',
            type=str,
            nargs='?',
            help='Date in YYYY-MM-DD format (e.g., 2025-07-02). Defaults to current date if not provided.'
        )

    def calculate_flood_level(self, water_level, danger_level):
        if danger_level is None or water_level is None or water_level < 0:
            return "na"
        elif water_level >= danger_level + 1:
            return "severe"
        elif water_level >= danger_level:
            return "flood"
        elif water_level >= danger_level - 0.5:
            return "warning"
        else:
            return "normal"

    def handle(self, *args, **options):
        # CHANGE 1: Fetch all districts with auto_update set to True.
        # We get their names and convert them to a lowercase set for efficient lookups.
        try:
            districts_to_update_qs = models.DistrictFloodAlertAutoUpdate.objects.filter(
                auto_update=True
            ).values_list('district_name', flat=True)
            auto_update_districts_set = {name.lower().strip() for name in districts_to_update_qs}
            logger.info(f"Found {len(auto_update_districts_set)} districts enabled for auto-update.")
        except Exception as e:
            logger.critical(f"Could not fetch auto-update district settings. Error: {e}")
            self.stderr.write(self.style.ERROR("Could not fetch auto-update district settings. Aborting."))
            return
        
        if not auto_update_districts_set:
            logger.warning("No districts are configured for auto-update. Exiting.")
            self.stdout.write(self.style.SUCCESS("No districts configured for auto-update. Task complete."))
            return

        date_str = options['date']
        # ... (rest of the initial setup code is the same)
        if date_str:
            try:
                start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                logger.info(f"Processing flood alerts for specified start date: {start_date}")
            except ValueError:
                logger.error(f"Invalid date format: {date_str}")
                self.stderr.write(self.style.ERROR(f"Invalid date format. Use YYYY-MM-DD (e.g., 2025-07-02)."))
                return
        else:
            # If no date is provided, use the current date
            start_date = date.today()
            logger.info(f"No date specified. Processing flood alerts for current date: {start_date}")

        all_waterlevel_alerts = models.WaterlevelAlert.objects.all()
        waterlevel_alerts_by_type_string = {
            alert.alert_type: alert for alert in all_waterlevel_alerts
        }

        internal_key_to_db_alert_type = {}
        for internal_key in INTERNAL_FLOOD_LEVEL_KEYS:
            if internal_key == "severe":
                expected_db_type = "Severe Flood"
            elif internal_key == "na":
                expected_db_type = "N/A"
            else:
                expected_db_type = internal_key.capitalize()

            if expected_db_type in waterlevel_alerts_by_type_string:
                internal_key_to_db_alert_type[internal_key] = expected_db_type
            else:
                error_msg = (
                    f"Critical Error: WaterlevelAlert for type '{expected_db_type}' "
                    f"(derived from internal key '{internal_key}') not found in database. "
                    "Please ensure your WaterlevelAlert table is correctly populated."
                )
                logger.critical(error_msg)
                self.stderr.write(self.style.ERROR(error_msg))
                return

        stations = models.Station.objects.filter(
            district__isnull=False,
            danger_level__isnull=False,
            station_id__isnull=False
        ).exclude(
            district=''
        ).values('station_id', 'name', 'district', 'danger_level')

        if not stations:
            logger.error("No valid station data found with non-null district and danger_level")
            self.stderr.write(self.style.ERROR("No valid station data found."))
            return

        logger.info(f"Found {len(stations)} valid stations")

        latest_forecast = models.WaterLevelForecast.objects.aggregate(Max('forecast_date'))
        latest_forecast_date = latest_forecast['forecast_date__max']
        logger.info(f"Latest forecast date: {latest_forecast_date}")

        max_days = 7
        if latest_forecast_date:
            forecast_end_date = latest_forecast_date.date() if isinstance(latest_forecast_date, datetime) else latest_forecast_date
            forecast_start_date = start_date + timedelta(days=1)
            days_available = (forecast_end_date - forecast_start_date).days + 1
            max_forecast_days = min(6, max(0, days_available))
            max_days = min(max_days, 1 + max_forecast_days)
        else:
            max_days = 1
            logger.warning("No forecast data available, limiting to observed data")

        for day_offset in range(max_days):
            current_date = start_date + timedelta(days=day_offset)
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
            self.stdout.write(f"Processing day {day_offset}: {day_start.date()}")
            logger.debug(f"Processing day {day_offset}: {day_start} to {day_end}")

            district_alerts = defaultdict(lambda: {"severe": 0, "flood": 0, "warning": 0, "normal": 0, "na": 0})

            latest_data = []
            if day_offset == 0:
                try:
                    # Attempt to get observed data for the current date
                    latest_data = models.WaterLevelObservation.objects.filter(
                        observation_date__range=(day_start, day_end),
                        station_id__isnull=False,
                        station_id__station_id__in=[s['station_id'] for s in stations]
                    ).values('station_id__station_id').annotate(
                        max_waterlevel=Max('water_level')
                    ).values('station_id__station_id', 'max_waterlevel')

                    if not latest_data:
                        logger.warning(f"No observed data for {day_start.date()}, trying forecast data for the same day.")
                        # If no observed data, try to get forecast data
                        latest_data = models.WaterLevelForecast.objects.filter(
                            forecast_date__range=(day_start, day_end),
                            station_id__isnull=False,
                            station_id__station_id__in=[s['station_id'] for s in stations]
                        ).values('station_id__station_id').annotate(
                            max_waterlevel=Max('water_level')
                        ).values('station_id__station_id', 'max_waterlevel')

                        if latest_data:
                            self.stdout.write(f"Using forecast data for {day_start.date()} for day {day_offset}")
                        else:
                            logger.warning(f"No forecast data available for {day_start.date()}, trying previous day's observed data.")
                            # Fall back to previous day's observed data
                            prev_day_start = day_start - timedelta(days=1)
                            prev_day_end = day_end - timedelta(days=1)
                            latest_data = models.WaterLevelObservation.objects.filter(
                                observation_date__range=(prev_day_start, prev_day_end),
                                station_id__isnull=False,
                                station_id__station_id__in=[s['station_id'] for s in stations]
                            ).values('station_id__station_id').annotate(
                                max_waterlevel=Max('water_level')
                            ).values('station_id__station_id', 'max_waterlevel')
                            if latest_data:
                                self.stdout.write(f"Using observed data from {prev_day_start.date()} for day {day_offset}")
                                current_date = prev_day_start.date() # Update current_date to reflect the data's date

                except Exception as e:
                    logger.error(f"Error fetching data for day 0: {str(e)}")
                    latest_data = []
            else:
                # For subsequent days, always use forecast data
                latest_data = models.WaterLevelForecast.objects.filter(
                    forecast_date__range=(day_start, day_end),
                    station_id__isnull=False,
                    station_id__station_id__in=[s['station_id'] for s in stations]
                ).values('station_id__station_id').annotate(
                    max_waterlevel=Max('water_level')
                ).values('station_id__station_id', 'max_waterlevel')

            logger.info(f"Found {len(latest_data)} data records for {current_date}")

            data_dict = {item['station_id__station_id']: item for item in latest_data}

            for station in stations:
                station_id = station['station_id']
                district_name = station['district'].lower().strip()
                if not district_name:
                    continue

                if station_id in data_dict:
                    data = data_dict[station_id]
                    try:
                        water_level = float(data['max_waterlevel'])
                        danger_level = float(station['danger_level'])
                        flood_level = self.calculate_flood_level(water_level, danger_level)
                        district_alerts[district_name][flood_level] += 1
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Invalid data for station {station_id}: {str(e)}")
                        district_alerts[district_name]["na"] += 1
                else:
                    district_alerts[district_name]["na"] += 1

            with transaction.atomic():
                for district, levels in district_alerts.items():
                    # CHANGE 2: Check if the current district is in our auto-update set.
                    # If not, skip it and move to the next one.
                    if district not in auto_update_districts_set:
                        logger.debug(f"Skipping alert for '{district.capitalize()}' as it is not enabled for auto-update.")
                        continue
                        
                    max_level_key = "na"
                    for level_key in ["severe", "flood", "warning", "normal"]:
                        if levels[level_key] > 0:
                            max_level_key = level_key
                            break

                    alert_type_string_from_db = internal_key_to_db_alert_type.get(max_level_key)

                    if not alert_type_string_from_db:
                        logger.error(f"Logic Error: Unrecognized internal key '{max_level_key}'. Skipping alert for {district}.")
                        self.stderr.write(self.style.ERROR(f"Unrecognized alert key '{max_level_key}'. Skipping district: {district}"))
                        continue

                    alert_type_obj = waterlevel_alerts_by_type_string.get(alert_type_string_from_db)

                    if not alert_type_obj:
                        logger.critical(f"FATAL: WaterlevelAlert object for type '{alert_type_string_from_db}' not found in pre-fetched data. Investigate database state.")
                        self.stderr.write(self.style.ERROR(f"FATAL: Missing WaterlevelAlert for '{alert_type_string_from_db}'. Cannot save alert for {district}."))
                        continue

                    try:
                        district_alert_obj, created = models.DistrictFloodAlert.objects.update_or_create(
                            alert_date=current_date,
                            district_name=district.capitalize(),
                            defaults={'alert_type': alert_type_obj}
                        )
                        action = "Created" if created else "Updated"
                        self.stdout.write(f"{action} alert for {district.capitalize()} on {current_date}: {alert_type_string_from_db}")
                    except Exception as e:
                        logger.error(f"Error storing/updating alert for {district.capitalize()} on {current_date}: {str(e)}")
                        self.stderr.write(self.style.ERROR(f"Error storing/updating alert for {district.capitalize()} on {current_date}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("District flood alert generation complete."))