import os
import math
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import warnings
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.utils import timezone

from data_load.models import UKMetMonsoonBasinWiseFlashFloodForecast

# Suppress the buffer warning for geographic CRS to keep logs clean
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

# --- Monsoon Configuration ---
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
    help = 'Generates UKMet Deterministic Monsoon Flash Flood Forecasts with Day-0 Recovery.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date') or datetime.now().strftime('%Y-%m-%d')
        if "-" not in date_input:
            try: date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: pass

        if not self.run_forecast_for_date(date_input):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Data missing for {date_input}. Trying yesterday: {yesterday}..."))
            self.run_forecast_for_date(yesterday)

    def get_daily_forecast_rainfall(self, station_gdf, station_name, given_date):
        date_str_nodash = given_date.replace('-', '')
        forecast_file = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_{date_str_nodash}.nc"
        
        if not os.path.exists(forecast_file): return {}
        run_date_obj = datetime.strptime(given_date, '%Y-%m-%d').date()

        try:
            with xr.open_dataset(forecast_file) as ds:
                # 1. Coordinate Standardization
                x_dim = "longitude" if "longitude" in ds.coords else "lon"
                y_dim = "latitude" if "latitude" in ds.coords else "lat"
                
                da = ds.rename({x_dim: 'x', y_dim: 'y'})
                da.rio.set_spatial_dims(x_dim='x', y_dim='y', inplace=True)
                da.rio.write_crs("epsg:4326", inplace=True)
                da = da.sortby(['y', 'x'])
                
                # 2. Geometry Sanitizer & Clipping (using buffer for small basins)
                clipped = da.rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                
                target_var = 'tp' if 'tp' in clipped.data_vars else list(clipped.data_vars)[0]
                data_array = clipped[target_var]
                
                # Unit check: inspection showed mm
                if ds[target_var].attrs.get('units') == 'm':
                    data_array = data_array * 1000

                daily_rainfall = {}
                weights = np.cos(np.deg2rad(data_array.y))
                
                # 3. DAY-0 RECOVERY LOGIC (Aligning with Inspection)
                for idx, ts in enumerate(list(data_array.indexes['time'])):
                    mean_val = data_array.isel(time=idx).weighted(weights).mean(dim=['x', 'y']).item()
                    
                    # If Index 0 is the 29th, it represents the 28th's rain (run date)
                    if idx == 0 and ts.date() > run_date_obj:
                        key_date = given_date
                    else:
                        key_date = ts.strftime('%Y-%m-%d')
                    
                    daily_rainfall[key_date] = round(mean_val if not math.isnan(mean_val) else 0.0, 4)
                
                return daily_rainfall
        except Exception as e:
            self.stdout.write(self.style.ERROR(f" Error in Forecast {station_name}: {e}"))
            return {}

    def get_observed_rainfall(self, station_gdf, given_date):
        daily_precip = {}
        given_dt = datetime.strptime(given_date, "%Y-%m-%d")

        for i in range(1, 11):
            obs_date = given_dt - timedelta(days=i)
            filename = f"{obs_date.year}{obs_date.timetuple().tm_yday:03d}.nc"
            filepath = os.path.join(settings.BASE_DIR, "observed", filename)
            
            if os.path.exists(filepath):
                try:
                    with xr.open_dataset(filepath) as ds:
                        # Standardize global observed file coordinates
                        ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                        ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
                        ds_std.rio.write_crs("epsg:4326", inplace=True)
                        ds_std = ds_std.sortby(['y', 'x'])
                        
                        clipped = ds_std['precipitation'].rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                        weights = np.cos(np.deg2rad(clipped.y))
                        val = clipped.weighted(weights).mean().item()
                        
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = val
                except: 
                    daily_precip[obs_date.strftime('%Y-%m-%d')] = 0.0
            else:
                daily_precip[obs_date.strftime('%Y-%m-%d')] = 0.0
        return daily_precip

    def run_forecast_for_date(self, date_input):
        self.stdout.write(self.style.SUCCESS(f'--- UKMET Monsoon Deterministic Processing: {date_input} ---'))
        success_count = 0
        global_peak_val = 0.0

        for basin_id, station_name in STATION_DICT.items():
            basin_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(basin_json): continue
            
            station_gdf = gpd.read_file(basin_json, crs="epsg:4326")
            if station_gdf.empty or station_gdf.geometry.iloc[0] is None: continue

            forecast_data = self.get_daily_forecast_rainfall(station_gdf, station_name, date_input)
            if not forecast_data: continue

            obs_data = self.get_observed_rainfall(station_gdf, date_input)
            combined = {**obs_data, **forecast_data}
            
            # Use Pandas for easier rolling window calculations
            combined_norm = {pd.to_datetime(k).normalize(): v for k, v in combined.items()}
            forecast_start = pd.to_datetime(date_input).normalize()
            process_dates = [forecast_start + timedelta(days=i) for i in range(10)]
            
            results = {}
            for p_date in process_dates:
                day_results = {}
                for idx, (hour, threshold) in STATION_THRESHOLDS[basin_id].items():
                    days_to_sum = int(hour / 24)
                    sum_range = [(p_date - timedelta(days=i)).normalize() for i in range(days_to_sum)]
                    total_rain = sum(combined_norm.get(d, 0.0) for d in sum_range)
                    day_results[idx] = round(total_rain, 2)
                    
                    if total_rain > global_peak_val: global_peak_val = total_rain

                results[p_date.strftime('%Y-%m-%d')] = day_results

            if results:
                self.save_to_database(results, date_input, basin_id)
                success_count += 1
                self.stdout.write(f"  ✅ Processed {station_name}")

        self.stdout.write(self.style.NOTICE(f"🏁 Processing Complete. Global Peak Rainfall Detected: {global_peak_val:.2f}mm"))
        return success_count > 0

    def save_to_database(self, results, prediction_date, basin_id):
        rows = []
        h_map = {idx: val[0] for idx, val in STATION_THRESHOLDS[basin_id].items()}
        t_map = {idx: val[1] for idx, val in STATION_THRESHOLDS[basin_id].items()}

        for date_key, values in results.items():
            for idx, val in values.items():
                rows.append(UKMetMonsoonBasinWiseFlashFloodForecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=h_map[idx],
                    thresholds=t_map[idx],
                    value=val
                ))
        
        if rows:
            UKMetMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            UKMetMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)