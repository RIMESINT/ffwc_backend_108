import os
from datetime import datetime, timedelta

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from django.conf import settings
from django.core.management import BaseCommand
from rioxarray.exceptions import NoDataInBounds

# Import the correct model
# NOTE: Ensure this model exists and is correctly configured in your Django project.
from data_load.models import UKMetMonsoonBasinWiseFlashFloodForecast

# --- Static Data Dictionaries ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon',13:'amalshid'
}

#    10: {0: [24, 48.5], 1: [48, 67.5], 2: [72, 81.8], 3: [120, 104.2], 4: [168, 122.3], 5: [240, 144.8]},

STATION_THRESHOLDS = {
    1: {0: [24, 96.9], 1: [48, 162.8], 2: [72, 220.6], 3: [120, 323.4], 4: [168, 416.1], 5: [240, 543.4]},
    2: {0: [24, 62.9], 1: [48, 92.9], 2: [72, 116.7], 3: [120, 155.5], 4: [168, 188.0], 5: [240, 229.7]},
    3: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    4: {0: [24, 25.0], 1: [48, 40.5], 2: [72, 53.5], 3: [120, 76.0], 4: [168, 96.0], 5: [240, 123.0]},
    5: {0: [24, 52.7], 1: [48, 65.8], 2: [72, 75.0], 3: [120, 88.4], 4: [168, 98.5], 5: [240, 110.5]},
    6: {0: [24, 33.5], 1: [48, 51.8], 2: [72, 66.9], 3: [120, 92.3], 4: [168, 114.1], 5: [240, 142.9]},
    7: {0: [24, 41.4], 1: [48, 59.1], 2: [72, 72.8], 3: [120, 94.7], 4: [168, 112.6], 5: [240, 135.3]},
    8: {0: [24, 28.8], 1: [48, 35.8], 2: [72, 40.6], 3: [120, 47.7], 4: [168, 53.0], 5: [240, 59.3]},
    9: {0: [24, 14.0], 1: [48, 22.0], 2: [72, 30.0], 3: [120, 44.0], 4: [168, 56.0], 5: [240, 73.0]},
    10: {0: [24, 58.20], 1: [48, 76.29], 2: [72, 89.34], 3: [120, 109.05], 4: [168, 124.35], 5: [240, 142.92]},
    # 11: {0: [24, 9.7], 1: [48, 28.2], 2: [72, 52.6], 3: [120, 115.3], 4: [168, 193.4], 5: [240, 334.5]},
    11: {0: [24, 36.88], 1: [48, 60.99], 2: [72, 81.87], 3: [120, 118.63], 4: [168, 151.45], 5: [240, 196.20]},
    12: {0: [24, 30.5], 1: [48, 40.5], 2: [72, 47.7], 3: [120, 58.8], 4: [168, 67.4], 5: [240, 77.9]},
    13: {0: [24, 13.04], 1: [48, 22.34], 2: [72, 30.61], 3: [120, 45.52], 4: [168, 59.12],5: [240, 77.99]}
}

class Command(BaseCommand):
    help = 'Generates UKMet Deterministic Flash Flood Forecasts with fallback logic.'

    def add_arguments(self, parser):
        parser.add_argument(
            'date', nargs='?', type=str,
            help='Forecast initialization date (YYYY-MM-DD). If omitted, tries today then yesterday.'
        )

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        
        if date_input:
            self.stdout.write(self.style.SUCCESS(f"Running forecast for specified date: {date_input}"))
            self.run_forecast_for_date(date_input)
        else:
            today_str = datetime.now().strftime('%Y-%m-%d')
            self.stdout.write(self.style.SUCCESS(f"No date provided. Attempting to run for today: {today_str}"))
            
            success = self.run_forecast_for_date(today_str)
            
            if not success:
                yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                self.stdout.write(self.style.WARNING(f"\nCould not find complete data for today. Falling back to yesterday: {yesterday_str}"))
                self.run_forecast_for_date(yesterday_str)

    def get_daily_forecast_rainfall(self, station_name, given_date):
        """Processes the deterministic forecast file to get daily rainfall totals."""
        basin_json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        station_gdf = gpd.read_file(basin_json_path, crs="epsg:4326")

        date_str_nodash = given_date.replace('-', '')
        # NOTE: Update the forecast path based on your actual project structure.
        forecast_file = os.path.join(settings.BASE_DIR, 'UkMET_deterministic', f'ukmet_det_{date_str_nodash}', f'precip_{date_str_nodash}.nc')
        # forecast_file = os.path.join(settings.BASE_DIR, 'UkMET_deterministic', f'ukmet_det_{date_str_nodash}', f'precip_raw_{date_str_nodash}.nc')
        
        try:
            with xr.open_dataset(forecast_file) as ds:
                vars_to_drop = [v for v in ['latitude_bnds', 'longitude_bnds', 'time_bnds', 'forecast_period_bnds'] if v in ds.variables]
                ds = ds.drop_vars(vars_to_drop)
                ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                
                clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True)
                weights = np.cos(np.deg2rad(clipped.latitude))
                weighted_mean_ds = clipped.weighted(weights).mean(dim=["longitude", "latitude"])
                
                # --- CORRECTED DAILY AGGREGATION LOGIC ---
                daily_rainfall = {}
                # The 'tp' variable is assumed to be cumulative precipitation in meters
                # We need to calculate the interval precipitation and convert to mm
                for day, group in weighted_mean_ds.groupby('time.dayofyear'):
                    group = group.sortby('time')
                    # Convert cumulative values from meters to mm
                    cumulative_values = group['tp'].values
                    # cumulative_values = group['tp'].values * 1000 
                    # cumulative_values = group['thickness_of_rainfall_amount'].values * 1000 
                    
                    
                    # Calculate interval precipitation (diff)
                    # Use cumulative_values[0] as the first interval if the forecast starts at a non-zero time step
                    interval_precip = np.diff(cumulative_values, prepend=cumulative_values[0]) 
                    interval_precip[interval_precip < 0] = 0 # Handle potential non-monotonic data issues
                    
                    date_str = pd.to_datetime(group['time'].values[0]).strftime('%Y-%m-%d')
                    daily_rainfall[date_str] = np.sum(interval_precip).round(4)
                return daily_rainfall

        except (FileNotFoundError, NoDataInBounds):
            self.stdout.write(self.style.WARNING(f"  Forecast file not found or basin is outside bounds for {given_date}."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  An error occurred processing forecast for {station_name}: {e}"))
            
        return {}

    def get_observed_rainfall(self, station_name, given_date):
        """Gets the last 10 days of observed rainfall for a basin."""
        daily_precip = {}
        given_datetime = datetime.strptime(given_date, "%Y-%m-%d")
        basin_json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        station_gdf = gpd.read_file(basin_json_path, crs="epsg:4326")

        for i in range(1, 11): # Look back 10 days
            obs_date = given_datetime - timedelta(days=i)
            filename = f"{obs_date.year}{obs_date.timetuple().tm_yday:03d}.nc"
            # NOTE: Update the observed data path based on your actual project structure.
            # filepath = os.path.join(settings.BASE_DIR, "observed", filename)
            filepath = os.path.join("observed", filename)
            try:
                with xr.open_dataset(filepath) as ds:
                    ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                    clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True)
                    weights = np.cos(np.deg2rad(clipped.lat))
                    # The observed value is already the daily total in mm (assumed from first.py)
                    daily_precip[obs_date.strftime('%Y-%m-%d')] = clipped['precipitation'].weighted(weights).mean().item()
            except Exception:
                pass # Silently skip missing observed files
        return daily_precip

    # ⬅️ --- MODIFIED FOR BACKWARD-LOOKING CUMULATIVE SUM ---
    def calculate_flash_flood_forecast(self, combined_rainfall, thresholds, given_date):
        """
        Calculates **backward-looking** cumulative rainfall against thresholds, 
        matching the logic of first.py by summing the past X days (observed + forecast).
        """
        if not combined_rainfall:
            return {}

        threshold_df = pd.DataFrame.from_dict(thresholds, orient='index', columns=['Hours', 'Thresholds'])
        
        # Identify the dates for which we need to calculate a result
        forecast_start_date = pd.to_datetime(given_date)
        all_combined_dates = sorted(pd.to_datetime(list(combined_rainfall.keys())))
        
        # Process dates are the forecast dates (start date and subsequent days)
        process_dates = [d for d in all_combined_dates if d >= forecast_start_date]
        
        forecast_results = {}
        for process_date in process_dates:
            cumulative_rainfall = {}
            
            for index, (hour, _) in threshold_df.iterrows():
                days_to_sum = int(hour / 24)
                
                # Create the range of PAST dates (backward-looking), including the process_date (day 0)
                # This mirrors the logic: for day N, sum rainfall from Day N, Day N-1, Day N-2, ...
                summation_range = [process_date - timedelta(days=i) for i in range(days_to_sum)]
                
                # Sum values from the combined_rainfall dictionary for these past dates
                daily_sum = sum(combined_rainfall.get(d.strftime('%Y-%m-%d'), 0) for d in summation_range)
                cumulative_rainfall[index] = round(daily_sum, 2)
                
            forecast_results[process_date.strftime('%Y-%m-%d')] = cumulative_rainfall

        return {"Hours": threshold_df['Hours'].to_dict(), "Thresholds": threshold_df['Thresholds'].to_dict(), **forecast_results}

    def save_to_database(self, data_dict, prediction_date, basin_id):
        """Transforms and saves the forecast data to the database."""
        if not data_dict or "Hours" not in data_dict: return
        rows = []
        for date_key, values in data_dict.items():
            if date_key in ["Hours", "Thresholds"]: continue
            for index, value in values.items():
                rows.append({'prediction_date': prediction_date, 'basin_id': basin_id, 'hours': data_dict["Hours"][index], 'thresholds': data_dict["Thresholds"][index], 'date': datetime.strptime(date_key, "%Y-%m-%d").date(), 'value': value})
        if not rows: return
        
        # Delete old records
        count, _ = UKMetMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
        self.stdout.write(f"  Deleted {count} old records for basin {basin_id}.")
        
        # Insert new records
        forecast_objects = [UKMetMonsoonBasinWiseFlashFloodForecast(**row) for row in rows]
        UKMetMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(forecast_objects)
        self.stdout.write(f"  Successfully inserted {len(forecast_objects)} new records.")

    def run_forecast_for_date(self, date_input):
        """
        Runs the entire forecast generation process for a single given date.
        Returns True if data for at least one basin was successfully processed, otherwise False.
        """
        self.stdout.write(self.style.SUCCESS(f'--- Starting Generation for: {date_input} ---'))
        at_least_one_basin_succeeded = False

        for basin_id, station_name in STATION_DICT.items():
            self.stdout.write(f"\n- Processing Basin ID: {basin_id} ({station_name})")
            try:
                # 1. Get forecast rainfall
                forecast_rainfall = self.get_daily_forecast_rainfall(station_name, date_input)
                if not forecast_rainfall:
                    self.stdout.write(self.style.WARNING("  No forecast data could be processed. Skipping basin."))
                    # Note: We continue even if forecast is missing, as observed data can still be used for backward look.
                    # However, if forecast is missing, the combined rainfall may be empty for future dates.

                # 2. Get observed rainfall for historical context
                observed_rainfall = self.get_observed_rainfall(station_name, date_input)

                # 3. Combine observed and forecast data (Forecast overrides observed for overlapping dates)
                combined_rainfall = {**observed_rainfall, **forecast_rainfall}
                # combined_rainfall = {**forecast_rainfall,**observed_rainfall}

                # 4. Calculate the flash flood forecast (Backward-Looking)
                thresholds = STATION_THRESHOLDS[basin_id]
                response = self.calculate_flash_flood_forecast(combined_rainfall, thresholds, date_input)

                # 5. Save results to the database
                if response and len(response) > 2: # Check if it contains more than just Hours/Thresholds keys
                    self.save_to_database(response, date_input, basin_id)
                    at_least_one_basin_succeeded = True
                else:
                    self.stdout.write(self.style.WARNING(f"  No flash flood data calculated for basin {basin_id}."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  An unexpected error occurred: {e}"))
                # import traceback
                # traceback.print_exc() # Uncomment for debugging
        
        if at_least_one_basin_succeeded:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Forecast Generation Finished for {date_input}.'))
        else:
            self.stdout.write(self.style.ERROR(f'\n❌ Forecast Generation Failed for {date_input}. No data found or processed.'))
        
        return at_least_one_basin_succeeded