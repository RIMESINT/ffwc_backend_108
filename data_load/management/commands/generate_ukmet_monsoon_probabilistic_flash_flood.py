import os
from datetime import datetime, timedelta

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from django.conf import settings
from django.core.management import BaseCommand
from rioxarray.exceptions import NoDataInBounds

# Make sure this import path is correct for your project structure
from data_load.models import UKMetMonsoonProbabilisticFlashFloodForecast

# --- Static Data (can be moved to a separate config file if desired) ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon',13:'amalshid'
}

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
    """
    Generates UKMet Probabilistic Basin-Wise Flash Flood Forecasts.
    Implements a fallback logic: tries today's date first, and if no data is found,
    automatically retries with yesterday's date.
    """
    help = 'Generate Probabilistic Basin Wise Flash Flood Forecasts with fallback logic.'

    def add_arguments(self, parser):
        parser.add_argument(
            'date', nargs='?', type=str,
            help='Forecast initialization date (YYYY-MM-DD). If omitted, tries today then yesterday.'
        )

    # ✅ --- MODIFIED `handle` METHOD ---
    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        
        if date_input:
            # If a specific date is provided, run for that date only.
            self.stdout.write(self.style.SUCCESS(f"Running forecast for specified date: {date_input}"))
            self.run_forecast_for_date(date_input)
        else:
            # If no date is provided, try today first.
            today_str = datetime.now().strftime('%Y-%m-%d')
            self.stdout.write(self.style.SUCCESS(f"No date provided. Attempting to run for today: {today_str}"))
            
            success = self.run_forecast_for_date(today_str)
            
            # If the run for today was not successful (e.g., no data found), fall back to yesterday.
            if not success:
                yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                self.stdout.write(self.style.WARNING(f"\nCould not find complete data for today. Falling back to yesterday: {yesterday_str}"))
                self.run_forecast_for_date(yesterday_str)

    # --- (All other helper functions remain the same as the previous version) ---
    def get_basin_data(self, basin_id):
        """Loads basin-specific metadata like name, thresholds, and geometry."""
        station_name = STATION_DICT[basin_id]
        thresholds = STATION_THRESHOLDS[basin_id]
        json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        return station_name, thresholds, gpd.read_file(json_path, crs="epsg:4326")

    def get_observed_rainfall(self, station_gdf, given_date):
        """Computes mean rainfall for the last 10 days from observed data files."""
        daily_precip = {}
        given_datetime = datetime.strptime(given_date, "%Y-%m-%d")
        for i in range(1, 11):
            obs_date = given_datetime - timedelta(days=i)
            filename = f"{obs_date.year}{obs_date.timetuple().tm_yday:03d}.nc"
            filepath = os.path.join(settings.BASE_DIR, "observed", filename)
            try:
                with xr.open_dataset(filepath) as ds:
                    ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                    clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True)
                    weights = np.cos(np.deg2rad(clipped.lat))
                    daily_precip[obs_date.strftime('%Y-%m-%d')] = clipped['precipitation'].weighted(weights).mean().item()
            except Exception:
                self.stdout.write(self.style.WARNING(f"Could not process observed file: {filename}"))
        return pd.DataFrame(list(daily_precip.items()), columns=['Date', 'Rainfall'])

    def compute_daily_rainfall_from_forecast(self, clipped_forecast):
        """Correctly converts cumulative hourly forecast data into daily totals."""
        daily_rainfall = {}
        # Ensure we are using the internal name we assigned in the step above
        var_name = 'thickness_of_rainfall_amount'
        
        for day, group in clipped_forecast.groupby('time.dayofyear'):
            group = group.sortby('time')
            # Assuming 'tp' is in meters, * 1000 converts to mm
            cumulative_values = group[var_name].values * 1000
            
            # Get the difference between steps to find interval rainfall
            interval_precip = np.diff(cumulative_values, prepend=cumulative_values[0])
            interval_precip[interval_precip < 0] = 0 # Handle resets if any
            
            date_str = pd.to_datetime(group['time'].values[0]).strftime('%Y-%m-%d')
            daily_rainfall[date_str] = np.sum(interval_precip)
        return daily_rainfall
        

    def process_ensemble_member(self, station_gdf, forecast_dir, filename):
            """Processes a single forecast file with flexible variable and coordinate names."""
            filepath = os.path.join(forecast_dir, filename)
            try:
                with xr.open_dataset(filepath) as ds:
                    # 1. Flexible Coordinate Detection
                    x_dim = "longitude" if "longitude" in ds.coords else "lon"
                    y_dim = "latitude" if "latitude" in ds.coords else "lat"
                    
                    vars_to_drop = [v for v in ['latitude_bnds', 'longitude_bnds', 'time_bnds', 'forecast_period_bnds', 'lat_bnds', 'lon_bnds'] if v in ds.variables]
                    ds = ds.drop_vars(vars_to_drop)
                    
                    ds.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim, inplace=True).rio.write_crs("epsg:4326", inplace=True)
                    
                    # 2. Clipping with Error Handling
                    try:
                        clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True)
                    except NoDataInBounds:
                        # If clipping fails, we return None and it skips this member
                        return None

                    # 3. Flexible Variable Detection (Look for 'tp' or the old long name)
                    target_var = None
                    for var in ['tp', 'thickness_of_rainfall_amount', 'precipitation']:
                        if var in clipped:
                            target_var = var
                            break
                    
                    if target_var is None:
                        self.stdout.write(self.style.ERROR(f"      No precip variable found in {filename}. Available: {list(clipped.data_vars)}"))
                        return None

                    # 4. Weighted Mean Calculation
                    weights = np.cos(np.deg2rad(clipped[y_dim]))
                    weighted_mean_ds = clipped[target_var].weighted(weights).mean(dim=[x_dim, y_dim])
                    
                    # Convert back to dataset for compute_daily_rainfall_from_forecast compatibility
                    result_ds = weighted_mean_ds.to_dataset(name='thickness_of_rainfall_amount')
                    return self.compute_daily_rainfall_from_forecast(result_ds)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"      Error in {filename}: {str(e)}"))
            return None

    # def process_ensemble_member(self, station_gdf, forecast_dir, filename):
    #     """Processes a single forecast file (e.g., precip_EN00.nc)."""
    #     filepath = os.path.join(forecast_dir, filename)
    #     try:
    #         with xr.open_dataset(filepath) as ds:
    #             vars_to_drop = [v for v in ['latitude_bnds', 'longitude_bnds', 'time_bnds', 'forecast_period_bnds'] if v in ds.variables]
    #             ds = ds.drop_vars(vars_to_drop)
    #             ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True).rio.write_crs("epsg:4326", inplace=True)
    #             clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True)
    #             weights = np.cos(np.deg2rad(clipped.latitude))
    #             weighted_mean_ds = clipped.weighted(weights).mean(dim=["longitude", "latitude"])
    #             return self.compute_daily_rainfall_from_forecast(weighted_mean_ds)
    #     except (FileNotFoundError, NoDataInBounds, Exception) as e:
    #         # Silently handle errors for individual files; the calling function will check for overall success.
    #         pass
    #     return None

    def calculate_exceedance_probability(self, all_member_rainfall, thresholds, given_date):
        """Calculates the probability of exceeding rainfall thresholds."""
        if not all_member_rainfall: return {}
        num_successful_members = len(all_member_rainfall)
        threshold_df = pd.DataFrame.from_dict(thresholds, orient='index', columns=['Hours', 'Threshold'])
        combined_df = pd.DataFrame(all_member_rainfall).fillna(0)
        forecast_dates = [d for d in pd.to_datetime(combined_df.columns) if d >= pd.to_datetime(given_date)]
        probability_results = {}
        for process_date in sorted(forecast_dates):
            daily_probabilities = {}
            for index, (hour, threshold) in threshold_df.iterrows():
                days_to_sum = int(hour / 24)
                end_date = process_date + timedelta(days=days_to_sum - 1)
                summation_cols = [d.strftime('%Y-%m-%d') for d in pd.date_range(start=process_date, end=end_date) if d.strftime('%Y-%m-%d') in combined_df.columns]
                if not summation_cols: continue
                cumulative_sums = combined_df[summation_cols].sum(axis=1)
                exceedance_count = (cumulative_sums > threshold).sum()
                daily_probabilities[index] = round((exceedance_count / num_successful_members) * 100, 2)
            if daily_probabilities: probability_results[process_date.strftime('%Y-%m-%d')] = daily_probabilities
        return {"Hours": threshold_df['Hours'].to_dict(), "Thresholds": threshold_df['Threshold'].to_dict(), **probability_results}

    def save_to_database(self, data_dict, prediction_date, basin_id):
        """Transforms the result and saves it to the database."""
        if not data_dict or "Hours" not in data_dict: return
        rows = []
        for date_key, values in data_dict.items():
            if date_key in ["Hours", "Thresholds"]: continue
            for index, value in values.items():
                rows.append({'prediction_date': prediction_date, 'basin_id': basin_id, 'hours': data_dict["Hours"][index], 'thresholds': data_dict["Thresholds"][index], 'date': datetime.strptime(date_key, "%Y-%m-%d").date(), 'value': value if pd.notna(value) else 0.0})
        if not rows: return
        UKMetMonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
        self.stdout.write(f"Deleted old records for basin {basin_id} on {prediction_date}.")
        forecast_objects = [UKMetMonsoonProbabilisticFlashFloodForecast(**row) for row in rows]
        UKMetMonsoonProbabilisticFlashFloodForecast.objects.bulk_create(forecast_objects)
        self.stdout.write(f"Successfully inserted {len(forecast_objects)} new records.")

    # ✅ --- `main` is renamed and now returns a success status ---
    def run_forecast_for_date(self, date_input):

        self.stdout.write(self.style.SUCCESS(f'--- Starting Generation for: {date_input} ---'))
        at_least_one_basin_succeeded = False
        
        for basin_id, station_name in STATION_DICT.items():
            self.stdout.write(f"\n- Processing Basin ID: {basin_id} ({station_name})")
            try:
                _, thresholds, station_gdf = self.get_basin_data(basin_id)
                date_str_nodash = date_input.replace('-', '')
                forecast_dir = os.path.join(settings.BASE_DIR, 'UkMET_ensemble', f'ukmet_ens_{date_str_nodash}')
                filenames = [f'precip_EN{i:02d}.nc' for i in range(18)]
                
                all_member_rainfall = [res for filename in filenames if (res := self.process_ensemble_member(station_gdf, forecast_dir, filename)) is not None]

                if not all_member_rainfall:
                    self.stdout.write(self.style.WARNING("  No valid ensemble members found for this basin."))
                    continue
                
                response = self.calculate_exceedance_probability(all_member_rainfall, thresholds, date_input)

                if response:
                    self.save_to_database(response, date_input, basin_id)
                    at_least_one_basin_succeeded = True
                else:
                    self.stdout.write(self.style.WARNING(f"  No response generated for basin {basin_id}."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  An unexpected error occurred: {e}"))
                import traceback
                traceback.print_exc()

        if at_least_one_basin_succeeded:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Forecast Generation Finished for {date_input}.'))
        else:
            self.stdout.write(self.style.ERROR(f'\n❌ Forecast Generation Failed for {date_input}. No data found or processed.'))
        
        return at_least_one_basin_succeeded