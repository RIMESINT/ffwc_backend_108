import os
import math
from datetime import datetime, timedelta

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from django.conf import settings
from django.core.management import BaseCommand
from rioxarray.exceptions import NoDataInBounds

# Import the new Pre-Monsoon model
from data_load.models import UKMetPreMonsoonBasinWiseFlashFloodForecast

# --- Pre-Monsoon Station Configurations ---
STATION_DICT = { 
    1:'khaliajhuri', 2:'gowainghat', 3:'dharmapasha', 4:'userbasin',
    5:'laurergarh', 6:'muslimpur', 7:'debidwar', 8:'ballah',
    9:'habiganj', 10:'parshuram', 11:'cumilla', 12:'nakuagaon'
}

STATION_THRESHOLDS = {
    1: {0: [24, 51.45], 1: [48, 77.5], 2: [72, 98.3], 3: [120, 133.0], 4: [168, 162.0], 5: [240, 200.0]},
    2: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    3: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    4: {0: [24, 25.0], 1: [48, 40.5], 2: [72, 53.5], 3: [120, 76.0], 4: [168, 96.0], 5: [240, 123.0]},
    5: {0: [24, 34.0], 1: [48, 46.3], 2: [72, 55.4], 3: [120, 69.37], 4: [168, 80.5], 5: [240, 94.0]},
    6: {0: [24, 33.50], 1: [48, 51.84], 2: [72, 66.93], 3: [120, 92.34], 4: [168, 114.14], 5: [240, 142.90]},
    7: {0: [24, 54.0], 1: [48, 87.0], 2: [72, 115.0], 3: [120, 164.0], 4: [168, 207.0], 5: [240, 264.0]},
    8: {0: [24, 15.0], 1: [48, 26.0], 2: [72, 35.0], 3: [120, 52.0], 4: [168, 68.0], 5: [240, 90.0]},
    9: {0: [24, 14.0], 1: [48, 22.0], 2: [72, 30.0], 3: [120, 44.0], 4: [168, 56.0], 5: [240, 73.0]},
    10: {0: [24, 17.0], 1: [48, 29.0], 2: [72, 39.0], 3: [120, 58.0], 4: [168, 75.0], 5: [240, 99.0]},
    11: {0: [24, 32.0], 1: [48, 49.0], 2: [72, 63.0], 3: [120, 87.0], 4: [168, 108.0], 5: [240, 135.0]},
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]}
}

class Command(BaseCommand):
    help = 'Generates UKMet Deterministic PRE-MONSOON Flash Flood Forecasts.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        if not date_input:
            date_input = datetime.now().strftime('%Y-%m-%d')
        
        # Standardize date format (YYYY-MM-DD)
        try:
            if "-" not in date_input:
                date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
        except:
            pass

        if not self.run_forecast_for_date(date_input):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Data missing for {date_input}. Trying {yesterday}..."))
            self.run_forecast_for_date(yesterday)

    def get_daily_forecast_rainfall(self, station_name, given_date):
        date_str_nodash = given_date.replace('-', '')
        forecast_file = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_{date_str_nodash}.nc"
        
        basin_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        if not os.path.exists(basin_json): return {}
        station_gdf = gpd.read_file(basin_json, crs="epsg:4326")

        try:
            with xr.open_dataset(forecast_file) as ds:
                if 'tp' not in ds.variables:
                    return {}
                
                ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
                ds.rio.write_crs("epsg:4326", inplace=True)
                ds = ds.sortby(['latitude', 'longitude'])
                
                clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True, all_touched=True)
                
                daily_rainfall = {}
                time_steps = list(clipped.indexes['time'])
                
                for ts in time_steps:
                    data_step = clipped.sel(time=ts)
                    mean_val = data_step['tp'].mean(dim=["longitude", "latitude"]).values.tolist()
                    val = mean_val if isinstance(mean_val, (float, int)) else mean_val[0]
                    
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
        
        forecast_start_date = pd.to_datetime(given_date)
        all_dates = sorted(pd.to_datetime(list(combined_rainfall.keys())))
        process_dates = [d for d in all_dates if d >= forecast_start_date]
        
        results = {}
        for p_date in process_dates:
            cum_vals = {}
            for idx, (hour, _) in thresholds.items():
                days = int(hour / 24)
                sum_range = [p_date - timedelta(days=i) for i in range(days)]
                daily_sum = sum(combined_rainfall.get(d.strftime('%Y-%m-%d'), 0) for d in sum_range)
                cum_vals[idx] = round(daily_sum, 2)
            results[p_date.strftime('%Y-%m-%d')] = cum_vals

        return results

    def save_to_database(self, results, prediction_date, basin_id):
        rows = []
        # Map indices to actual values from pre-monsoon thresholds
        hours_map = {idx: val[0] for idx, val in STATION_THRESHOLDS[basin_id].items()}
        thresh_map = {idx: val[1] for idx, val in STATION_THRESHOLDS[basin_id].items()}

        for date_key, values in results.items():
            for idx, val in values.items():
                rows.append(UKMetPreMonsoonBasinWiseFlashFloodForecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=hours_map[idx],
                    thresholds=thresh_map[idx],
                    value=val
                ))
        
        if rows:
            UKMetPreMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            UKMetPreMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)

    def run_forecast_for_date(self, date_input):
        self.stdout.write(self.style.SUCCESS(f'--- UKMET Pre-Monsoon Processing: {date_input} ---'))
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