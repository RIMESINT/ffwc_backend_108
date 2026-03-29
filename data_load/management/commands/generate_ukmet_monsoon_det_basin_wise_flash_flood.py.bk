import os
from datetime import datetime, timedelta
import math
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from django.conf import settings
from django.core.management import BaseCommand
from rioxarray.exceptions import NoDataInBounds

# Import the correct model
from data_load.models import UKMetMonsoonBasinWiseFlashFloodForecast

# --- Static Data Dictionaries ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon', 13: 'amalshid'
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
    11: {0: [24, 36.88], 1: [48, 60.99], 2: [72, 81.87], 3: [120, 118.63], 4: [168, 151.45], 5: [240, 196.20]},
    12: {0: [24, 30.5], 1: [48, 40.5], 2: [72, 47.7], 3: [120, 58.8], 4: [168, 67.4], 5: [240, 77.9]},
    13: {0: [24, 13.04], 1: [48, 22.34], 2: [72, 30.61], 3: [120, 45.52], 4: [168, 59.12], 5: [240, 77.99]}
}

class Command(BaseCommand):
    help = 'Generates UKMet Deterministic Flash Flood Forecasts using specific local path.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        if not date_input:
            date_input = datetime.now().strftime('%Y-%m-%d')
        
        # Try target date, fallback to yesterday if data missing
        if not self.run_forecast_for_date(date_input):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Data missing for {date_input}. Trying {yesterday}..."))
            self.run_forecast_for_date(yesterday)

    def get_daily_forecast_rainfall(self, station_name, given_date):
        # 1. Path Setup based on your new directory structure
        date_str_nodash = given_date.replace('-', '')
        forecast_file = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_{date_str_nodash}.nc"
        
        basin_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        if not os.path.exists(basin_json): return {}
        station_gdf = gpd.read_file(basin_json, crs="epsg:4326")

        try:
            with xr.open_dataset(forecast_file) as ds:
                # 2. Variable and Coordinate Preparation
                if 'tp' not in ds.variables:
                    return {}
                
                # Fix for NoDataInBounds: Sort coordinates and set CRS
                ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
                ds.rio.write_crs("epsg:4326", inplace=True)
                ds = ds.sortby(['latitude', 'longitude'])
                
                # 3. Clip to Basin (Using all_touched=True for small basins)
                clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True, all_touched=True)
                
                # 4. Process Daily Totals
                daily_rainfall = {}
                time_steps = list(clipped.indexes['time'])
                
                for ts in time_steps:
                    data_step = clipped.sel(time=ts)
                    # Mean value of the basin for this time step
                    mean_val = data_step['tp'].mean(dim=["longitude", "latitude"]).values.tolist()
                    val = mean_val if isinstance(mean_val, (float, int)) else mean_val[0]
                    
                    # UKMET 'tp' is already in mm (Daily Total), so no multiplication needed
                    date_key = ts.strftime('%Y-%m-%d')
                    daily_rainfall[date_key] = round(val if not math.isnan(val) else 0.0, 4)
                
                return daily_rainfall

        except (FileNotFoundError, NoDataInBounds):
            return {}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f" Error in {station_name}: {e}"))
            return {}

    def get_observed_rainfall(self, station_name, given_date):
        daily_precip = {}
        given_dt = datetime.strptime(given_date, "%Y-%m-%d")
        basin_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        station_gdf = gpd.read_file(basin_json, crs="epsg:4326")

        for i in range(1, 11):
            obs_date = given_dt - timedelta(days=i)
            filename = f"{obs_date.year}{obs_date.timetuple().tm_yday:03d}.nc"
            filepath = os.path.join(settings.BASE_DIR, "observed", filename)
            
            if os.path.exists(filepath):
                try:
                    with xr.open_dataset(filepath) as ds:
                        ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                        ds = ds.sortby(['lat', 'lon'])
                        clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True, all_touched=True)
                        weights = np.cos(np.deg2rad(clipped.lat))
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = clipped['precipitation'].weighted(weights).mean().item()
                except: pass
        return daily_precip

    def calculate_flash_flood_forecast(self, combined_rainfall, thresholds, given_date):
            if not combined_rainfall: return {}
            
            # FIX: Create a fixed 10-day range starting from the actual Run Date
            forecast_start_date = pd.to_datetime(given_date)
            process_dates = [forecast_start_date + timedelta(days=i) for i in range(10)]
            
            results = {}
            for p_date in process_dates:
                date_str = p_date.strftime('%Y-%m-%d')
                cum_vals = {}
                for idx, (hour, _) in thresholds.items():
                    days = int(hour / 24)
                    # Sum backward from the current loop date
                    sum_range = [p_date - timedelta(days=i) for i in range(days)]
                    
                    # This will correctly use observed rainfall for "Today" 
                    # and forecast rainfall for future dates
                    daily_sum = sum(combined_rainfall.get(d.strftime('%Y-%m-%d'), 0) for d in sum_range)
                    cum_vals[idx] = round(daily_sum, 2)
                
                results[date_str] = cum_vals

            return results

    def save_to_database(self, results, prediction_date, basin_id):
        rows = []
        hours_map = {idx: val[0] for idx, val in STATION_THRESHOLDS[basin_id].items()}
        thresh_map = {idx: val[1] for idx, val in STATION_THRESHOLDS[basin_id].items()}

        for date_key, values in results.items():
            for idx, val in values.items():
                rows.append(UKMetMonsoonBasinWiseFlashFloodForecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=hours_map[idx],
                    thresholds=thresh_map[idx],
                    value=val
                ))
        
        if rows:
            UKMetMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            UKMetMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)

    def run_forecast_for_date(self, date_input):
        self.stdout.write(self.style.SUCCESS(f'--- UKMET Processing: {date_input} ---'))
        success_count = 0

        for basin_id, station_name in STATION_DICT.items():
            forecast_data = self.get_daily_forecast_rainfall(station_name, date_input)
            if not forecast_data: continue

            obs_data = self.get_observed_rainfall(station_name, date_input)
            combined = {**obs_data, **forecast_data}
            
            results = self.calculate_flash_flood_forecast(combined, STATION_THRESHOLDS[basin_id], date_input)
            
            if results:
                self.save_to_database(results, date_input, basin_id)
                success_count += 1
                self.stdout.write(f"  Processed Basin {basin_id} ({station_name})")

        return success_count > 0