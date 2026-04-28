# data_load/tasks.py
import csv
from datetime import datetime
import io
import pytz
from django.conf import settings
from celery import shared_task
from django.db import transaction # Import transaction for atomicity
from datetime import timedelta
import pytz
import time

import logging

from celery import shared_task, states # Import states
from celery.exceptions import Ignore # To ignore task if error
from celery_progress.backend import ProgressRecorder # Assuming django-celery-results is installed
import pandas as pd # Import pandas here
import re # Import re for regex parsing
from django.db import transaction

from decimal import Decimal, InvalidOperation

from .models import (
    WaterLevelObservation, RainfallObservation, Station, RainfallStation, 
    WaterLevelForecast, FfwcLastUpdateDate ,
    FfwcLastUpdateDateExperimental, WaterLevelObservationExperimentals,WaterLevelForecastsExperimentals
)

from django.db.utils import IntegrityError 

# Import utilities
from .utils import normalize_datetime # Import normalize_datetime
from django.utils import timezone
logger = logging.getLogger(__name__)





# --- Helper function from previous context ---
def update_last_update_date():
    """
    Updates the FfwcLastUpdateDate with the current date.
    Ensures only one record exists.
    """
    try:
        current_time_utc = timezone.now()
        target_timezone = pytz.timezone(settings.TIME_ZONE) # Use Django's configured TIME_ZONE

        # Convert the UTC time to the target local timezone
        current_time_local = current_time_utc.astimezone(target_timezone)

        last_update_date_to_store = current_time_local.date() #
        entry_date_to_store_aware = current_time_local #

        # entry_date_utc = current_time_utc + timedelta(hours=6)
        # current_date = current_time_utc.date()

        FfwcLastUpdateDate.objects.all().delete()
        FfwcLastUpdateDate.objects.create(
            last_update_date=last_update_date_to_store,
            entry_date=entry_date_to_store_aware
            )
        logger.info("FfwcLastUpdateDate updated successfully.")
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message_for_log = f'An unexpected error occurred: {e}\n{error_traceback}'
        logger.error(error_message_for_log)

        # Ensure progress is set for UI before exiting
        # (Use e.__class__.__name__ for a concise error type)
        progress_recorder.set_progress(100, 100, description=f"Error: {e.__class__.__name__}")
        self.update_state(state=states.FAILURE, meta={'message': str(e), 'percent': 100})

    return None # <-- This is the CRITICAL part. It MUST be 'return None'.
        # logger.error(f"Error updating FfwcLastUpdateDate: {e}", exc_info=True)



def ffwc_last_update_date_experimental():
    """
    Updates the FfwcLastUpdateDateExperimental with the current date.
    Ensures only one record exists.
    """
    try:
        # Align this with update_last_update_date for consistency
        current_time_utc = timezone.now() #
        target_timezone = pytz.timezone(settings.TIME_ZONE) #
        current_time_local = current_time_utc.astimezone(target_timezone) #
        
        last_update_date_to_store = current_time_local.date() # Get local date

        FfwcLastUpdateDateExperimental.objects.all().delete()
        # Use the locally derived date for consistency
        FfwcLastUpdateDateExperimental.objects.create(last_update_date=last_update_date_to_store) #
        logger.info("FfwcLastUpdateDateExperimental updated successfully.")
    except Exception as e:
        logger.error(f"Error updating FfwcLastUpdateDateExperimental: {e}", exc_info=True)


def update_last_update_date():
    """
    Updates the FfwcLastUpdateDate with the current date.
    """
    try:
        current_time_utc = timezone.now()
        target_timezone = pytz.timezone(settings.TIME_ZONE)
        current_time_local = current_time_utc.astimezone(target_timezone)

        FfwcLastUpdateDate.objects.all().delete()
        FfwcLastUpdateDate.objects.create(
            last_update_date=current_time_local.date(),
            entry_date=current_time_local
        )
        logger.info("FfwcLastUpdateDate updated successfully.")
    except Exception as e:
        logger.error(f"Error updating FfwcLastUpdateDate: {e}", exc_info=True)

@shared_task(bind=True)
def process_observations_csv(self, csv_data_string, timezone_name):
    try:
        lines = io.StringIO(csv_data_string).readlines()
        if len(lines) < 3:
            return {'status': 'failed', 'message': 'CSV file is empty or missing rows.'}

        # 1. Clean Headers
        raw_headers = lines[1].strip().split(';')
        cleaned_csv_headers = [h.strip() for h in raw_headers]
        data_rows = lines[2:]
        reader = csv.DictReader(data_rows, fieldnames=cleaned_csv_headers, delimiter=';')
        
        # 2. Maps from Admin-defined DB headers
        wl_map = {s.ffdata_header.strip(): s for s in Station.objects.exclude(ffdata_header__isnull=True).exclude(ffdata_header='')}
        rf_map = {rs.header.strip(): rs for rs in RainfallStation.objects.exclude(header__isnull=True).exclude(header='')}

        tz = pytz.timezone(timezone_name or settings.TIME_ZONE)
        wl_in, wl_up, rf_in, rf_up = 0, 0, 0, 0
        total_rows = len(data_rows)
        all_console_logs = []

        with transaction.atomic():
            for i, row in enumerate(reader):
                date_str = row.get('YYYY-MM-DD HH:MM:SS')
                if not date_str: continue
                
                try:
                    observation_date = tz.localize(datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M:%S'))
                except: continue

                # --- Process Water Level ---
                for csv_header, station_obj in wl_map.items():
                    val = row.get(csv_header)
                    if val and val.strip() != '-9999' and val.strip() != '':
                        num_val = float(val.strip())
                        qs = WaterLevelObservation.objects.filter(station_id=station_obj, observation_date=observation_date)
                        
                        if qs.exists():
                            obj = qs.first()
                            obj.water_level = num_val
                            obj.save()
                            wl_up += 1
                            all_console_logs.append(f"WL: {station_obj.name} | {date_str} | {num_val}m | Updated (Correction)")
                        else:
                            WaterLevelObservation.objects.create(station_id=station_obj, observation_date=observation_date, water_level=num_val)
                            wl_in += 1
                            all_console_logs.append(f"WL: {station_obj.name} | {date_str} | {num_val}m | Created")

                # --- Process Rainfall ---
                for csv_header, rf_station_obj in rf_map.items():
                    val = row.get(csv_header)
                    if val and val.strip() != '-9999' and val.strip() != '':
                        num_val = float(val.strip())
                        qs = RainfallObservation.objects.filter(station_id=rf_station_obj, observation_date=observation_date)
                        
                        if qs.exists():
                            obj = qs.first()
                            obj.rainfall = num_val
                            obj.save()
                            rf_up += 1
                            all_console_logs.append(f"RF: {rf_station_obj.name} | {date_str} | {num_val}mm | Updated (Correction)")
                        else:
                            RainfallObservation.objects.create(station_id=rf_station_obj, observation_date=observation_date, rainfall=num_val)
                            rf_in += 1
                            all_console_logs.append(f"RF: {rf_station_obj.name} | {date_str} | {num_val}mm | Created")

                # Push to frontend every 5 rows
                if i % 5 == 0 or i == total_rows - 1:
                    self.update_state(state='PROGRESS', meta={
                        'current': i + 1, 
                        'total': total_rows, 
                        'percent': int(((i + 1) / total_rows) * 100),
                        'console_logs': all_console_logs, 
                        'message': f'Processing row {i+1}...'
                    })

        update_last_update_date()
        result_message = f'Success! WL: {wl_in+wl_up}, RF: {rf_in+rf_up} processed.'
        
        return {
            'status': 'completed', 
            'message': result_message,
            'console_logs': all_console_logs 
        }
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise e

# @shared_task(bind=True)
# def process_observations_csv(self, csv_data_string, timezone_name):
#     """
#     Celery task to process CSV data for Water Level and Rainfall Observations.
#     """
#     try:
#         decoded_file = io.StringIO(csv_data_string).readlines()
#         if not decoded_file:
#             return {'status': 'failed', 'message': 'Uploaded CSV file is empty.'}

#         decoded_file_iterator = iter(decoded_file)
#         next(decoded_file_iterator)  # Skip Row 1 (Metadata/Header info)

#         csv_reader = csv.DictReader(decoded_file_iterator, delimiter=';')
#         rows = list(csv_reader) 
#         total_rows = len(rows)
        
#         try:
#             tz = pytz.timezone(timezone_name)
#         except pytz.UnknownTimeZoneError:
#             tz = pytz.timezone(settings.TIME_ZONE)

#         # Pre-fetch station mappings
#         station_header_map = {s.ffdata_header: s for s in Station.objects.all() if s.ffdata_header}
#         rainfall_station_header_map = {rs.header: rs for rs in RainfallStation.objects.all() if rs.header}

#         water_level_observations_to_process = []
#         rainfall_observations_to_process = []

#         # Counters
#         wl_in, wl_up, wl_sk = 0, 0, 0
#         rf_in, rf_up, rf_sk = 0, 0, 0

#         # Phase 1: Parse Data
#         for i, row in enumerate(rows):
#             if i % 10 == 0: # Update progress every 10 rows
#                 self.update_state(state='PROGRESS', meta={
#                     'current': i, 'total': total_rows, 'percent': int((i/total_rows)*50), 
#                     'message': f'Parsing row {i} of {total_rows}'
#                 })

#             try:
#                 # Use the column name exactly as it appears in your snippet
#                 naive_date = datetime.strptime(row['YYYY-MM-DD HH:MM:SS'], '%Y-%m-%d %H:%M:%S')
#                 observation_date = tz.localize(naive_date)
#             except (KeyError, ValueError):
#                 continue

#             for header, value in row.items():
#                 if value == '-9999' or not value:
#                     continue
                
#                 # Check for Water Level (handles both suffixes)
#                 if header.endswith('-3h-WL') or header.endswith('-3hr-WL'):
#                     try:
#                         val = float(value)
#                         station = station_header_map.get(header)
#                         if station:
#                             water_level_observations_to_process.append({
#                                 'station_id': station,
#                                 'observation_date': observation_date,
#                                 'water_level': val
#                             })
#                         else:
#                             wl_sk += 1
#                     except ValueError:
#                         wl_sk += 1

#                 # Check for Rainfall
#                 elif header.startswith('RF-'):
#                     try:
#                         val = float(value)
#                         rf_station = rainfall_station_header_map.get(header)
#                         if rf_station:
#                             rainfall_observations_to_process.append({
#                                 'station_id': rf_station,
#                                 'observation_date': observation_date,
#                                 'rainfall': val
#                             })
#                         else:
#                             rf_sk += 1
#                     except ValueError:
#                         rf_sk += 1

#         # Phase 2: Bulk Upsert
#         with transaction.atomic():
#             self.update_state(state='PROGRESS', meta={'percent': 60, 'message': 'Processing Water Levels...'})
            
#             # Water Level Logic
#             for data in water_level_observations_to_process:
#                 obj, created = WaterLevelObservation.objects.update_or_create(
#                     station_id=data['station_id'],
#                     observation_date=data['observation_date'],
#                     defaults={'water_level': data['water_level']}
#                 )
#                 if created: wl_in += 1
#                 else: wl_up += 1

#             self.update_state(state='PROGRESS', meta={'percent': 80, 'message': 'Processing Rainfall...'})
            
#             # Rainfall Logic
#             for data in rainfall_observations_to_process:
#                 obj, created = RainfallObservation.objects.update_or_create(
#                     station_id=data['station_id'],
#                     observation_date=data['observation_date'],
#                     defaults={'rainfall': data['rainfall']}
#                 )
#                 if created: rf_in += 1
#                 else: rf_up += 1

#         update_last_update_date() 
        
#         result_message = (
#             f"WL: {wl_in} inserted, {wl_up} updated, {wl_sk} skipped. "
#             f"RF: {rf_in} inserted, {rf_up} updated, {rf_sk} skipped."
#         )
#         self.update_state(state='SUCCESS', meta={'message': result_message, 'percent': 100})
#         return {'status': 'completed', 'message': result_message}

#     except Exception as e:
#         logger.error(f"Upload failed: {e}", exc_info=True)
#         # self.update_state(state=states.FAILURE, meta={'message': str(e), 'percent': 100})
#         raise e
#         # return None

        
# --- import_forecast_files task ---

@shared_task(bind=True)
def import_forecast_files(self, duration, forecastDF_dict, stationNameToIdDict, station_name):
    """
    Celery task to import water level forecast data from a single DataFrame.
    Performs bulk upsert operations, replacing old data for same dates.
    """
    progress_recorder = ProgressRecorder(self)
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    total_processed_rows = 0

    try:
        # --- (Existing code for data parsing and preprocessing) ---
        update_last_update_date()
        logger.info(f"Starting import_forecast_files task for station: {station_name}")
        progress_recorder.set_progress(5, 100, description="Converting data to DataFrame")
        forecastDF = pd.DataFrame(forecastDF_dict)
        pattern_one = r"(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(\d{1,2}):(\d{2})"
        pattern_two = r"\b(20[0-2][0-9])[-/](0[1-9]|1[0-2])[-/](0[1-9]|[0-3][0-9])\s+([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\b"
        progress_recorder.set_progress(10, 100, description=f"Processing station '{station_name}'...")
        station_id_for_df = stationNameToIdDict.get(station_name)
        if station_id_for_df is None:
            error_msg = f"Station '{station_name}' not found..."
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            raise Ignore()
        forecastDF['st_id'] = station_id_for_df
        forecast_columns = [col for col in forecastDF.columns.tolist() if col.endswith('-for')]
        if not forecast_columns:
            error_msg = f"No forecast columns found..."
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            raise Ignore()
        stationHeader = forecast_columns[0]
        forecastDF = forecastDF[['YYYY-MM-DD HH:MM:SS', stationHeader, 'st_id']].copy()
        forecastDF.rename(columns={'YYYY-MM-DD HH:MM:SS': 'forecast_date', stationHeader: 'water_level'}, inplace=True)
        forecastDF = forecastDF[forecastDF['water_level'] != -9999.0].dropna(subset=['water_level', 'forecast_date'])
        total_rows_after_filter = len(forecastDF)
        if total_rows_after_filter == 0:
            logger.warning(f"No valid data to process...")
            progress_recorder.set_progress(100, 100, description="No valid data to process")
            self.update_state(state=states.SUCCESS, meta={'message': f"No valid data for station {station_name}"})
            return {"inserted_rows": 0, "updated_rows": 0, "skipped_rows": 0, "state": states.SUCCESS}
        forecastDF.reset_index(drop=True, inplace=True)
        parsed_forecast_data = []
        tz = pytz.timezone(settings.TIME_ZONE)
        for index, row in forecastDF.iterrows():
            dateTimeString = str(row['forecast_date']).strip()
            try:
                dt_obj = None
                match_one = re.match(pattern_one, dateTimeString)
                match_two = re.match(pattern_two, dateTimeString)
                if match_one:
                    day, month, year = map(int, match_one.groups()[:3])
                    hour, minute = map(int, match_one.groups()[3:])
                    if year < 100:
                        year += 2000 if year <= datetime.now().year % 100 + 10 else 1900
                    dt_obj = datetime(year, month, day, hour, minute)
                elif match_two:
                    dt_obj = datetime.strptime(dateTimeString, '%Y-%m-%d %H:%M:%S')
                else:
                    logger.warning(f"Invalid date format at row {index} for {station_name}: {dateTimeString}")
                    skipped_count += 1
                    continue
                dt_obj_aware = tz.localize(dt_obj, is_dst=None)
                normalized_dt = normalize_datetime(dt_obj_aware)
                parsed_forecast_data.append({
                    'station_id_val': row['st_id'],
                    'forecast_date': normalized_dt,
                    'water_level': float(row['water_level'])
                })
            except (ValueError, AttributeError) as e:
                logger.warning(f"Date/value parsing error at row {index} for {station_name}: {dateTimeString}, error: {str(e)}")
                skipped_count += 1
                continue
            progress_recorder.set_progress(
                20 + int((index + 1) * 20 / total_rows_after_filter),
                100,
                description=f"Parsed {index + 1}/{total_rows_after_filter} dates for {station_name}"
            )
        if not parsed_forecast_data:
            logger.warning(f"No valid forecast data to process...")
            progress_recorder.set_progress(100, 100, description="No valid forecast data to process")
            self.update_state(state=states.SUCCESS, meta={'message': f"No valid forecast data for {station_name}"})
            return {"inserted_rows": 0, "updated_rows": 0, "skipped_rows": 0, "state": states.SUCCESS}
        total_processed_rows = len(parsed_forecast_data)

        # --- Phase 3: Bulk Upsert into database (FINAL LOGIC) ---
        progress_recorder.set_progress(40, 100, description=f"Performing database operations for {station_name}...")
        
        # We need a single, isolated transaction to avoid race conditions
        with transaction.atomic():


            station_ids_to_fetch = {data['station_id_val'] for data in parsed_forecast_data}
            station_objects_map = {s.station_id: s for s in Station.objects.filter(station_id__in=station_ids_to_fetch)}
    
            forecast_instances = []
            for i, fc_data in enumerate(parsed_forecast_data):
                station_obj = station_objects_map.get(fc_data['station_id_val'])
                if not station_obj:
                    logger.warning(f"Station with ID {fc_data['station_id_val']} not found for forecast. Skipping.")
                    skipped_count += 1
                    continue
                forecast_instances.append(
                    WaterLevelForecast(
                        station_id=station_obj,
                        forecast_date=fc_data['forecast_date'],
                        water_level=fc_data['water_level']
                    )
                )

            if forecast_instances:
                # First, try to insert all records, ignoring conflicts
                WaterLevelForecast.objects.bulk_create(forecast_instances, ignore_conflicts=True)

                # Now, identify and update the records that already existed
                keys_to_update = {(f.station_id.station_id, f.forecast_date): f.water_level for f in forecast_instances}
                
                # Fetch only the objects that need an update
                existing_objects_to_update = WaterLevelForecast.objects.filter(
                    station_id__station_id__in=[f.station_id.station_id for f in forecast_instances],
                    forecast_date__in=[f.forecast_date for f in forecast_instances]
                ).select_related('station_id')

                records_to_bulk_update = []
                for obj in existing_objects_to_update:
                    key = (obj.station_id.station_id, obj.forecast_date)
                    new_water_level = keys_to_update.get(key)
                    if new_water_level is not None and obj.water_level != new_water_level:
                        obj.water_level = new_water_level
                        records_to_bulk_update.append(obj)
                
                if records_to_bulk_update:
                    updated_count = WaterLevelForecast.objects.bulk_update(records_to_bulk_update, fields=['water_level'])
                inserted_count = len(forecast_instances) - len(records_to_bulk_update)


            progress_recorder.set_progress(90, 100, description=f"Database operations complete for {station_name}.")

        result_message = (
            f"Processed {station_name}: {inserted_count} inserted, "
            f"{updated_count} updated, {skipped_count} skipped."
        )
        logger.info(result_message)
        progress_recorder.set_progress(100, 100, description=result_message)
        self.update_state(
            state=states.SUCCESS,
            meta={
                'message': result_message,
                'inserted': inserted_count,
                'updated': updated_count,
                'skipped': skipped_count,
                'total_processed': total_processed_rows
            }
        )
        return {
            "inserted_rows": inserted_count,
            "updated_rows": updated_count,
            "skipped_rows": skipped_count,
            "total_rows": total_processed_rows,
            "state": states.SUCCESS
        }

    except Ignore:
        logger.warning(f"Task for {station_name} ignored based on task logic.")
        self.update_state(state=states.REVOKED, meta={'message': f"Task for {station_name} ignored."})
        return None

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message_for_log = f"Task for {station_name} failed: {e}\n{error_traceback}"
        logger.error(error_message_for_log)
        progress_recorder.set_progress(100, 100, description=f"Error: {e}")
        self.update_state(state=states.FAILURE, meta={'message': str(e)})

        return None

@shared_task(bind=True)
def import_experimental_forecast_files(self, duration, forecastDF_dict, stationNameToIdDict, station_name):
    # ... (all your data parsing and processing code remains the same) ...
    progress_recorder = ProgressRecorder(self)
    inserted_forecast_count = 0
    updated_forecast_count = 0
    inserted_observation_count = 0
    updated_observation_count = 0
    skipped_rows_count = 0
    total_initial_rows = 0

    logger.info(f"Task started for station: {station_name}. Duration: {duration}")

    try:
        ffwc_last_update_date_experimental()

        logger.info(f"Starting import_experimental_forecast_files task for station: {station_name}")
        progress_recorder.set_progress(5, 100, description="Converting data to DataFrame")

        forecastDF = pd.DataFrame(forecastDF_dict)
        total_initial_rows = len(forecastDF)
        logger.debug(f"Initial DataFrame has {total_initial_rows} rows. Columns: {forecastDF.columns.tolist()}")

        # --- Date Parsing Regex Patterns (REVISED ORDER FOR PRIORITY) ---
        pattern_two = r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2}):(\d{2})"
        pattern_one = r"(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(\d{1,2}):(\d{2})"

        progress_recorder.set_progress(10, 100, description=f"Processing experimental data for station '{station_name}'...")

        station_id_for_df = stationNameToIdDict.get(station_name)
        if station_id_for_df is None:
            error_msg = f"Station '{station_name}' not found in stationNameToIdDict or has None ID."
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            return None
        logger.debug(f"Station '{station_name}' mapped to ID: {station_id_for_df}")


        # Ensure 'st_id' column is present for both forecast and observation processing
        forecastDF['st_id'] = station_id_for_df

        # --- Identify experimental forecast columns based on suffixes. ---
        min_col = next((col for col in forecastDF.columns.tolist() if col.endswith('-16')), None)
        max_col = next((col for col in forecastDF.columns.tolist() if col.endswith('-84')), None)
        mean_col = next((col for col in forecastDF.columns.tolist() if col.endswith('-Mean')), None)
        logger.debug(f"Identified forecast columns: Min='{min_col}', Max='{max_col}', Mean='{mean_col}'")


        # --- Identify observation column ---
        observation_col_name_expected = f"{station_name}-obs"
        actual_observation_col = next((col for col in forecastDF.columns.tolist() if col.lower() == observation_col_name_expected.lower()), None)
        logger.info(f"Searching for observation column '{observation_col_name_expected}'. Found: '{actual_observation_col}'")
        if not actual_observation_col:
            logger.warning(f"Observation column '{observation_col_name_expected}' not found in DataFrame for station '{station_name}'. Observations will not be processed.")


        # --- MODIFIED COLUMN PRESENCE CHECK FOR FORECASTS ---
        if not mean_col:
            error_msg = (
                f"Missing essential experimental forecast column '{station_name}-Mean' for station '{station_name}'. "
                f"Found: Min='{min_col}', Max='{max_col}', Mean='{mean_col}'. Task requires Mean column."
            )
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            return None

        # Build list of columns to select from DataFrame for both forecast and observation.
        columns_to_select = ['YYYY-MM-DD HH:MM:SS', mean_col, 'st_id']
        if min_col: columns_to_select.append(min_col)
        if max_col: columns_to_select.append(max_col)
        # Ensure actual_observation_col is added only if found and not already in the list
        if actual_observation_col and actual_observation_col not in columns_to_select:
             columns_to_select.append(actual_observation_col)
        logger.debug(f"Final columns selected from DataFrame: {columns_to_select}")

        # Validate all columns_to_select exist in the original DataFrame
        missing_cols_in_df = [col for col in columns_to_select if col not in forecastDF.columns.tolist()]
        if missing_cols_in_df:
            error_msg = f"Critical error: Required columns {missing_cols_in_df} are missing in the input DataFrame. Available: {forecastDF.columns.tolist()}"
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            return None


        forecastDF = forecastDF[columns_to_select].copy()

        # Rename columns for consistency with model fields
        rename_map = {'YYYY-MM-DD HH:MM:SS': 'date_time', mean_col: 'waterlevel_mean'}
        if min_col: rename_map[min_col] = 'waterlevel_min'
        if max_col: rename_map[max_col] = 'waterlevel_max'

        # Only add to rename_map if actual_observation_col was found
        if actual_observation_col:
            rename_map[actual_observation_col] = 'waterlevel_obs'

        forecastDF.rename(columns=rename_map, inplace=True)
        logger.debug(f"DataFrame columns after renaming: {forecastDF.columns.tolist()}")
        logger.debug(f"First 5 rows of processed DataFrame:\n{forecastDF.head()}")


        # Drop rows with missing 'date_time' as it's essential for all records
        forecastDF = forecastDF.dropna(subset=['date_time'])
        logger.debug(f"DataFrame has {len(forecastDF)} rows after dropping rows with missing 'date_time'.")


        total_rows_after_filter = len(forecastDF)
        if total_rows_after_filter == 0:
            logger.warning(f"No valid data (with dates) to process after initial filtering for station {station_name}")
            progress_recorder.set_progress(100, 100, description="No valid data to process")
            self.update_state(state=states.SUCCESS, meta={'message': f"No valid data (with dates) for station {station_name}"})
            return {"inserted_rows": 0, "updated_rows": 0, "skipped_rows": skipped_rows_count, "total_rows": total_initial_rows, "state": states.SUCCESS}

        forecastDF.reset_index(drop=True, inplace=True)

        # --- Date parsing and timezone handling ---
        parsed_data = []
        obs_none_count = 0
        obs_valid_count = 0

        for index, row in forecastDF.iterrows():
            dateTimeString = str(row['date_time']).strip()
            try:
                dt_obj_naive = None
                match_two = re.match(pattern_two, dateTimeString)
                match_one = re.match(pattern_one, dateTimeString)

                if match_two:
                    dt_obj_naive = datetime.strptime(dateTimeString, '%Y-%m-%d %H:%M:%S')
                elif match_one:
                    dt_obj_naive = datetime.strptime(dateTimeString, '%d/%m/%y %H:%M')
                else:
                    logger.warning(f"Invalid date format at row {index} for {station_name}: {dateTimeString}. Skipping row.")
                    skipped_rows_count += 1
                    continue

                if dt_obj_naive.tzinfo is None:
                    dt_obj_aware = pytz.utc.localize(dt_obj_naive)
                else:
                    dt_obj_aware = dt_obj_naive.astimezone(pytz.utc)

                normalized_dt = normalize_datetime(dt_obj_aware)
                normalized_dt = normalized_dt.replace(second=0)

                def to_decimal_or_none(value):
                    if pd.isna(value) or (isinstance(value, (int, float)) and value == -9999.0):
                        return None
                    try:
                        return Decimal(str(round(float(value), 2)))
                    except (ValueError, TypeError, InvalidOperation):
                        return None

                waterlevel_obs_val = None
                if 'waterlevel_obs' in row:
                    waterlevel_obs_val = to_decimal_or_none(row['waterlevel_obs'])

                record = {
                    'station_id_val': row['st_id'],
                    'date_time': normalized_dt,
                    'waterlevel_min': to_decimal_or_none(row.get('waterlevel_min')),
                    'waterlevel_max': to_decimal_or_none(row.get('waterlevel_max')),
                    'waterlevel_mean': to_decimal_or_none(row.get('waterlevel_mean')),
                    'waterlevel_obs': waterlevel_obs_val,
                }
                parsed_data.append(record)

                if waterlevel_obs_val is None:
                    obs_none_count += 1
                else:
                    obs_valid_count += 1

            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(f"Date/value parsing error at row {index} for {station_name}: {dateTimeString}, Error: {str(e)}. Skipping row.")
                skipped_rows_count += 1
                continue

            progress_recorder.set_progress(
                20 + int((index + 1) * 20 / total_rows_after_filter),
                100,
                description=f"Parsed {index + 1}/{total_rows_after_filter} dates for {station_name}"
            )
        logger.info(f"Finished parsing data. Total rows parsed: {len(parsed_data)}. Valid observations: {obs_valid_count}, None observations: {obs_none_count}.")


        if not parsed_data:
            logger.warning(f"No valid data to process after parsing for station {station_name}")
            progress_recorder.set_progress(100, 100, description="No valid data to process")
            self.update_state(state=states.SUCCESS, meta={'message': f"No valid data for station {station_name}"})
            return {"inserted_rows": 0, "updated_rows": 0, "skipped_rows": skipped_rows_count, "total_rows": total_initial_rows, "state": states.SUCCESS}

        total_processed_rows = len(parsed_data)
    
        progress_recorder.set_progress(40, 100, description=f"Performing database operations for {station_name}...")
    
        with transaction.atomic():
            station_ids_to_fetch = {data['station_id_val'] for data in parsed_data}
            station_objects_map = {s.station_id: s for s in Station.objects.filter(station_id__in=station_ids_to_fetch)}
            logger.debug(f"Fetched station objects with IDs: {list(station_objects_map.keys())}")


            # --- Lists for Forecast Data ---
            experimental_forecasts_for_create = []
            experimental_forecasts_for_update_list = [] # Will be populated if existing conflicts

            existing_experimental_forecast_objects = WaterLevelForecastsExperimentals.objects.filter(
                station_id__station_id__in=station_ids_to_fetch,
                forecast_date__in=[data['date_time'] for data in parsed_data]
            ).select_related('station_id')

            existing_experimental_forecast_map = {
                (obj.station_id.station_id, obj.forecast_date): obj
                for obj in existing_experimental_forecast_objects
            }
            logger.debug(f"Found {len(existing_experimental_forecast_objects)} existing experimental forecasts in DB for lookup.")


            # --- Lists for Observation Data ---
            experimental_observations_for_create = []
            experimental_observations_for_update_list = [] # Will be populated if existing conflicts

            existing_experimental_observation_objects = WaterLevelObservationExperimentals.objects.filter(
                station_id__station_id__in=station_ids_to_fetch,
                observation_date__in=[data['date_time'] for data in parsed_data]
            ).select_related('station_id')

            existing_experimental_observation_map = {
                (obj.station_id.station_id, obj.observation_date): obj
                for obj in existing_experimental_observation_objects
            }
            logger.debug(f"Found {len(existing_experimental_observation_objects)} existing experimental observations in DB for lookup.")


            for i, data_row in enumerate(parsed_data):
                station_obj = station_objects_map.get(data_row['station_id_val'])
                if not station_obj:
                    logger.warning(f"Station with ID {data_row['station_id_val']} not found for experimental data. Skipping row.")
                    skipped_rows_count += 1
                    continue

                common_key = (data_row['station_id_val'], data_row['date_time'])

                # --- Process Forecast Data ---
                if data_row['waterlevel_mean'] is not None:
                    if common_key in existing_experimental_forecast_map:
                        obj_to_update = existing_experimental_forecast_map[common_key]
                        if (obj_to_update.waterlevel_min != data_row['waterlevel_min'] or
                            obj_to_update.waterlevel_max != data_row['waterlevel_max'] or
                            obj_to_update.waterlevel_mean != data_row['waterlevel_mean']):

                            obj_to_update.waterlevel_min = data_row['waterlevel_min']
                            obj_to_update.waterlevel_max = data_row['waterlevel_max']
                            obj_to_update.waterlevel_mean = data_row['waterlevel_mean']
                            experimental_forecasts_for_update_list.append(obj_to_update)
                            logger.debug(f"Forecast for {common_key} added to update list.")
                    else:
                        experimental_forecasts_for_create.append(
                            WaterLevelForecastsExperimentals(
                                station_id=station_obj,
                                forecast_date=data_row['date_time'],
                                waterlevel_min=data_row['waterlevel_min'],
                                waterlevel_max=data_row['waterlevel_max'],
                                waterlevel_mean=data_row['waterlevel_mean']
                            )
                        )
                        logger.debug(f"Forecast for {common_key} added to create list.")
                else:
                    logger.debug(f"Skipping forecast processing for {common_key} as waterlevel_mean is None.")


                # --- Process Observation Data ---
                if data_row['waterlevel_obs'] is not None:
                    if common_key in existing_experimental_observation_map:
                        obj_to_update = existing_experimental_observation_map[common_key]
                        if obj_to_update.water_level != data_row['waterlevel_obs']:
                            obj_to_update.water_level = data_row['waterlevel_obs']
                            experimental_observations_for_update_list.append(obj_to_update)
                            logger.debug(f"Observation for {common_key} added to update list.")
                    else:
                        experimental_observations_for_create.append(
                            WaterLevelObservationExperimentals(
                                station_id=station_obj,
                                observation_date=data_row['date_time'],
                                water_level=data_row['waterlevel_obs']
                            )
                        )
                        logger.debug(f"Observation for {common_key} added to create list.")
                else:
                    logger.debug(f"Skipping observation processing for {common_key} as waterlevel_obs is None.")


                progress_recorder.set_progress(
                    40 + int((i + 1) * 50 / total_processed_rows),
                    100,
                    description=f"Preparing {i + 1}/{total_processed_rows} records for DB for {station_name}"
                )

            # --- Perform Bulk Operations for Forecasts ---
            if experimental_forecasts_for_create:
                logger.info(f"Attempting bulk_create for {len(experimental_forecasts_for_create)} experimental forecasts.")
                WaterLevelForecastsExperimentals.objects.bulk_create(experimental_forecasts_for_create, ignore_conflicts=True)
                inserted_forecast_count = len(experimental_forecasts_for_create)

            if experimental_forecasts_for_update_list:
                logger.info(f"Attempting bulk_update for {len(experimental_forecasts_for_update_list)} experimental forecasts.")
                updated_forecast_count = WaterLevelForecastsExperimentals.objects.bulk_update(
                    experimental_forecasts_for_update_list,
                    fields=['waterlevel_min', 'waterlevel_max', 'waterlevel_mean']
                )
                logger.debug(f"Bulk_update completed for forecasts. Actual updated: {updated_forecast_count}")
            else:
                logger.info("No experimental forecasts needed updating.")


            # --- Perform Bulk Operations for Observations ---
            if experimental_observations_for_create:
                logger.info(f"Attempting bulk_create for {len(experimental_observations_for_create)} experimental observations.")
                WaterLevelObservationExperimentals.objects.bulk_create(experimental_observations_for_create, ignore_conflicts=True)
                inserted_observation_count = len(experimental_observations_for_create)
            if experimental_observations_for_update_list:
                logger.info(f"Attempting bulk_update for {len(experimental_observations_for_update_list)} experimental observations.")
                updated_observation_count = WaterLevelObservationExperimentals.objects.bulk_update(
                    experimental_observations_for_update_list,
                    fields=['water_level']
                )
                logger.debug(f"Bulk_update completed for observations. Actual updated: {updated_observation_count}")
            else:
                logger.info("No experimental observations needed updating.")

            progress_recorder.set_progress(90, 100, description=f"Database operations complete for {station_name}.")

        result_message = (
            f"Processed Experimental Data for {station_name}: "
            f"Forecasts: {inserted_forecast_count} inserted, {updated_forecast_count} updated. "
            f"Observations: {inserted_observation_count} inserted, {updated_observation_count} updated. "
            f"Total skipped rows (parsing errors/missing stations): {skipped_rows_count}. "
            f"Total file rows: {total_initial_rows}."
        )
        logger.info(result_message)

        self.update_state(
            state=states.SUCCESS,
            meta={
                'message': result_message,
                'inserted_forecasts': inserted_forecast_count,
                'updated_forecasts': updated_forecast_count,
                'inserted_observations': inserted_observation_count,
                'updated_observations': updated_observation_count,
                'skipped_rows': skipped_rows_count,
                'total_rows': total_initial_rows
            }
        )
        return {
            "inserted_forecasts": inserted_forecast_count,
            "updated_forecasts": updated_forecast_count,
            "inserted_observations": inserted_observation_count,
            "updated_observations": updated_observation_count,
            "skipped_rows": skipped_rows_count,
            "total_rows": total_initial_rows,
            "state": states.SUCCESS
        }

    except Ignore:
        logger.warning(f"Task for {station_name} ignored based on task logic.")
        self.update_state(state=states.REVOKED, meta={'message': f"Task for {station_name} ignored."})
        return None

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message_for_log = f"Task for {station_name} failed: {e}\n{error_traceback}"
        logger.error(error_message_for_log)

        self.update_state(state=states.FAILURE, meta={'message': str(e), 'percent': 100})

        return None

        

from django.core.management import call_command
@shared_task(bind=True) # bind=True is essential to get 'self'
def generate_rainfall_map_task(self):
    progress_recorder = ProgressRecorder(self)
    total_steps = 100 # Estimate total steps for your command's work

    logger.info("Starting rainfall distribution map generation")
    
    try:
        # Simulate progress for demonstration
        for i in range(total_steps):
            # Replace this with actual progress reporting from your command if possible
            # If your command itself doesn't report granular progress, you might just
            # update at key stages or after a certain amount of processing.
            # For now, we simulate.
            time.sleep(0.1) # Simulate work
            progress_recorder.set_progress(i + 1, total_steps, description=f'Processing step {i+1}/{total_steps}...')

        # Call your actual management command here
        call_command('generate_rainfall_distribution_map')
        
        # Ensure progress is marked as 100% when complete
        progress_recorder.set_progress(total_steps, total_steps, description="Rainfall map generation completed!")
        
        logger.info("Rainfall distribution map generation completed")
        return {'status': 'SUCCESS', 'message': 'Rainfall distribution map generated successfully!'}
    except Exception as e:
        logger.error(f"Error in rainfall distribution map task: {str(e)}")
        # Report failure and a custom message
        progress_recorder.set_progress(total_steps, total_steps, description=f"Task failed: {str(e)}")
        return {'status': 'FAILURE', 'message': f'Error generating map: {str(e)}'}


@shared_task(bind=True)
def generate_flood_alerts_task(self):
    """
    Celery task to run the 'generate_flood_alerts' management command.
    """
    progress_recorder = ProgressRecorder(self)
    total_steps = 100 # Adjust this based on your command's workload

    logger.info("Starting flood alerts generation")

    try:
        # You can customize the progress updates if your command has distinct stages.
        # For a simple command, a single progress update at the beginning and end is fine.
        progress_recorder.set_progress(10, total_steps, description='Initializing flood alerts command...')

        # Call the management command
        call_command('generate_flood_alerts')

        # Set final progress and success message
        progress_recorder.set_progress(total_steps, total_steps, description="Flood alerts generation completed!")
        
        logger.info("Flood alerts generation completed.")
        return {'status': 'SUCCESS', 'message': 'Flood alerts generated successfully!'}
    except Exception as e:
        logger.error(f"Error in flood alerts task: {str(e)}")
        # On failure, set progress to 100% with an error message
        progress_recorder.set_progress(total_steps, total_steps, description=f"Task failed: {str(e)}")
        # Return a failure status and message
        return {'status': 'FAILURE', 'message': f'Error generating flood alerts: {str(e)}'}



@shared_task
def generate_flood_alerts_task():
    """
    A background task to run the generate_flood_alerts management command.
    """
    try:
        logger.info("Starting flood alert generation task.")
        call_command('generate_flood_alerts') 
        logger.info("Flood alert generation task completed.")
    except Exception as e:
        logger.error(f"Error in flood alert generation task: {str(e)}")
        raise