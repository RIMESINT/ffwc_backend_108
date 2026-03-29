# -*- coding: utf-8 -*-
import os
import math
import warnings
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from datetime import datetime, timedelta

from xarray import SerializationWarning 
from django.core.management import BaseCommand
from django.conf import settings

# --- Model Import ---
from data_load.models import BMDWRFPreMonsoonBasinWiseFlashFloodForecast

# Suppress technical warnings
warnings.filterwarnings("ignore", category=SerializationWarning, module='xarray.coding.times')
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

# --- Configuration ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon'
}

STATION_THRESHOLDS_LIST = {
    1: {0: [24, 51.45], 1: [48, 77.5], 2: [72, 98.3], 3: [120, 133.0], 4: [168, 162.0], 5: [240, 200.0]},
    2: {0: [24, 25.0], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    3: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    4: {0: [24, 25.0], 1: [48, 40.5], 2: [72, 53.5], 3: [120, 76.0], 4: [168, 96.0], 5: [240, 123.0]},
    5: {0: [24, 34.0], 1: [48, 46.3], 2: [72, 55.4], 3: [120, 69.37], 4: [168, 80.5], 5: [240, 94.0]},
    6: {0: [24, 33.50], 1: [48, 51.84], 2: [72, 66.93], 3: [120, 92.34], 4: [168, 114.14], 5: [240, 142.90]},
    7: {0: [24, 54.0], 1: [48, 87.0], 2: [72, 115.0], 3: [120, 164.0], 4: [168, 207.0], 5: [240, 264.0]},
    8: {0: [24, 15.0], 1: [48, 26.0], 2: [72, 35.0], 3: [120, 52.0], 4: [168, 68.0], 5: [240, 90.0]},
    9: {0: [24, 14.0], 1: [48, 22.0], 2: [72, 30.0], 3: [120, 44.0], 4: [168, 56.0], 5: [240, 73.0]},
    10: {0: [24, 17.0], 1: [48, 29.0], 2: [72, 39.0], 3: [120, 58.0], 4: [168, 75.0], 5: [240, 99.0]},
    11: {0: [24, 32.0], 1: [48, 49.0], 2: [72, 63.0], 3: [120, 87.0], 4: [168, 108.0], 5: [240, 135.0]},
    12: {0: [24, 30.52], 1: [48, 40.468], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]}
}

class Command(BaseCommand):
    help = 'Generate Pre-Monsoon Flash Flood Forecast for BMD-WRF with level squeezing and spatial fix.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Initialization date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date') or datetime.now().strftime('%Y-%m-%d')
        if "-" not in date_input:
            try: date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: pass

        self.stdout.write(self.style.SUCCESS(f"🚀 Starting BMD-WRF Generation: {date_input}"))
        self.main(date_input)

    def get_observed_rainfall(self, station_gdf, station_name, given_date):
        daily_precip = {}
        given_dt = datetime.strptime(given_date, "%Y-%m-%d")

        for i in range(1, 11):
            obs_date = given_dt - timedelta(days=i)
            filename = f"{obs_date.year}{obs_date.timetuple().tm_yday:03d}.nc"
            filepath = os.path.join(settings.BASE_DIR, "observed", filename)
            
            if os.path.exists(filepath):
                try:
                    with xr.open_dataset(filepath) as ds:
                        # Standardize coordinates to prevent "x dimension not found"
                        ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                        ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
                        ds_std.rio.write_crs("epsg:4326", inplace=True)
                        
                        # Clip with buffer and all_touched for accuracy
                        clipped = ds_std['precipitation'].rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                        weights = np.cos(np.deg2rad(clipped.y))
                        val = clipped.weighted(weights).mean().item()
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = val
                except: continue
        return daily_precip

    def compute_basin_wise_forecast(self, station_gdf, station_name, given_date):
        date_str_nodash = given_date.replace('-', '')
        filename = f'wrf_out_{date_str_nodash}00.nc'
        forecast_path = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/bmd_wrf/{filename}"

        if not os.path.exists(forecast_path): return {}

        try:
            with xr.open_dataset(forecast_path) as ds:
                # 1. Spatial Dimension Fix
                ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
                ds_std.rio.write_crs("epsg:4326", inplace=True)
                ds_std = ds_std.sortby(['y', 'x'])

                # 2. Extract and Squeeze Rainfall Variables
                # Inspection showed shape (81, 1, 214, 214), so squeeze('lev') is needed
                total_rain_da = ds_std['rainc'] + ds_std['rainnc']
                if 'lev' in total_rain_da.dims: 
                    total_rain_da = total_rain_da.squeeze('lev')

                # 3. Clip to Basin
                clipped = total_rain_da.rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                weights = np.cos(np.deg2rad(clipped.y))
                basin_mean = clipped.weighted(weights).mean(dim=["x", "y"])

                daily_inc = {}
                # 4. De-accumulation Logic
                # index 0 (00:00) is always 0.0. Index 8 (24h mark) is Day 1's rain.
                prev_val = float(basin_mean.isel(time=0))
                time_indices = list(range(8, len(basin_mean), 8)) 
                
                for i, idx in enumerate(time_indices):
                    curr_val = float(basin_mean.isel(time=idx))
                    # Map to the calendar: i=0 is the run date (given_date)
                    target_date = (datetime.strptime(given_date, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d')
                    daily_inc[target_date] = round(max(0.0, curr_val - prev_val), 4)
                    prev_val = curr_val
                
                return daily_inc
        except Exception as e: 
            self.stderr.write(f"      ⚠️ Forecast Error ({station_name}): {e}")
            return {}

    def main(self, date_input):
        global_peak_val = 0.0
        peak_basin_info = "N/A"
        high_risk_list = []

        for basin_id, station_name in STATION_DICT.items():
            json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(json_path): continue
            
            station_gdf = gpd.read_file(json_path, crs="epsg:4326")
            
            # --- GEOMETRY GUARD ---
            if station_gdf.empty or station_gdf.geometry.iloc[0] is None or station_gdf.geometry.iloc[0].is_empty:
                continue

            obs = self.get_observed_rainfall(station_gdf, station_name, date_input)
            fcst = self.compute_basin_wise_forecast(station_gdf, station_name, date_input)
            
            if fcst:
                combined = {**obs, **fcst}
                combined_norm = {pd.to_datetime(k).normalize(): v for k, v in combined.items()}
                
                start_dt = pd.to_datetime(date_input).normalize()
                forecast_range = [start_dt + timedelta(days=i) for i in range(10)]
                
                results = {}
                thresholds = STATION_THRESHOLDS_LIST[basin_id]

                for p_date in forecast_range:
                    day_results = {}
                    for idx, (hours, thresh) in thresholds.items():
                        # Rolling sum window
                        sum_range = [(p_date - timedelta(days=d)).normalize() for d in range(int(hours/24))]
                        total_rain = sum(combined_norm.get(d, 0.0) for d in sum_range)
                        day_results[idx] = round(total_rain, 2)
                        
                        if total_rain > global_peak_val:
                            global_peak_val = total_rain
                            peak_basin_info = f"{station_name.upper()} ({total_rain}mm)"

                        if total_rain >= thresh and p_date >= start_dt:
                            high_risk_list.append({
                                'basin': station_name.upper(), 'date': p_date.strftime('%Y-%m-%d'),
                                'hour': hours, 'val': total_rain, 'thresh': thresh
                            })
                    results[p_date.strftime('%Y-%m-%d')] = day_results

                self.save_to_db(results, date_input, basin_id, thresholds)
                self.stdout.write(f"  ✅ Processed {station_name}")

        # Summary Log
        self.stdout.write("\n" + "═"*60)
        if high_risk_list:
            self.stdout.write(self.style.WARNING("⚠️  THRESHOLDS EXCEEDED:"))
            for item in sorted(high_risk_list, key=lambda x: x['date']):
                self.stdout.write(f"  - {item['basin']:15} | {item['val']:.2f}mm vs {item['thresh']}mm ({item['hour']}h) on {item['date']}")
        else:
            self.stdout.write(self.style.SUCCESS("✅ No thresholds exceeded."))
            self.stdout.write(self.style.NOTICE(f"📊 Global Peak Diagnostic: {global_peak_val:.2f}mm in {peak_basin_info}"))
        self.stdout.write("═"*60 + "\n")

    def save_to_db(self, results, prediction_date, basin_id, thresholds):
        rows = []
        for date_key, values in results.items():
            for idx, value in values.items():
                rows.append(BMDWRFPreMonsoonBasinWiseFlashFloodForecast(
                    prediction_date=prediction_date, basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=thresholds[idx][0], thresholds=thresholds[idx][1], value=value
                ))
        if rows:
            BMDWRFPreMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            BMDWRFPreMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)