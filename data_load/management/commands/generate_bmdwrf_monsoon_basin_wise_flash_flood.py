# -*- coding: utf-8 -*-
import os
import math
import warnings
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from datetime import datetime, timedelta

# Standard imports for WRF handling
from xarray import SerializationWarning 
from django.core.management.base import BaseCommand
from django.conf import settings
from data_load.models import BMDWRFMonsoonBasinWiseFlashFloodForecast

# Suppress WRF-specific technical warnings
warnings.filterwarnings("ignore", category=SerializationWarning, module='xarray.coding.times')
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

# --- Configuration ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon', 13: 'amalshid'
}

STATION_THRESHOLDS_LIST = {
    1: {0: [24, 96.899], 1: [48, 162.832], 2: [72, 220.597], 3: [120, 323.390], 4: [168, 416.054], 5: [240, 543.431]},
    2: {0: [24, 62.919], 1: [48, 92.913], 2: [72, 116.709], 3: [120, 155.549], 4: [168, 187.951], 5: [240, 229.698]},
    3: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    4: {0: [24, 25.0], 1: [48, 40.5], 2: [72, 53.5], 3: [120, 76.0], 4: [168, 96.0], 5: [240, 123.0]},
    5: {0: [24, 52.666], 1: [48, 65.831], 2: [72, 75.010], 3: [120, 88.417], 4: [168, 98.531], 5: [240, 110.519]},
    6: {0: [24, 33.50], 1: [48, 51.84], 2: [72, 66.93], 3: [120, 92.34], 4: [168, 114.14], 5: [240, 142.90]},
    7: {0: [24, 41.372], 1: [48, 59.108], 2: [72, 72.824], 3: [120, 94.724], 4: [168, 112.634], 5: [240, 135.331]},
    8: {0: [24, 28.772], 1: [48, 35.771], 2: [72, 40.630], 3: [120, 47.701], 4: [168, 53.019], 5: [240, 59.305]},
    9: {0: [24, 14.0], 1: [48, 22.0], 2: [72, 30.0], 3: [120, 44.0], 4: [168, 56.0], 5: [240, 73.0]},
    10: {0: [24, 58.20], 1: [48, 76.29], 2: [72, 89.34], 3: [120, 109.05], 4: [168, 124.35], 5: [240, 142.92]},
    11: {0: [24, 36.88], 1: [48, 60.99], 2: [72, 81.87], 3: [120, 118.63], 4: [168, 151.45], 5: [240, 196.20]},
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]},
    13: {0: [24, 13.04], 1: [48, 22.34], 2: [72, 30.61], 3: [120, 45.52], 4: [168, 59.12], 5: [240, 77.99]}
}

class Command(BaseCommand):
    help = 'Generate Monsoon Basin Wise Flashflood for BMD-WRF with robust spatial handling'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Initialization date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date') or datetime.now().strftime('%Y-%m-%d')
        if "-" not in date_input:
            try:
                date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: pass

        self.stdout.write(self.style.SUCCESS(f"🚀 Starting BMD-WRF Monsoon Run: {date_input}"))
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
                        # Coordinate Fix: Rename to x/y to resolve "x dimension not found"
                        ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                        ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
                        ds_std.rio.write_crs("epsg:4326", inplace=True)
                        
                        # Clip with buffer for small basins
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

        if not os.path.isfile(forecast_path): return {}

        try:
            with xr.open_dataset(forecast_path) as ds:
                # 1. Coordinate Fix for WRF (lon/lat to x/y)
                ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
                ds_std.rio.write_crs("epsg:4326", inplace=True)
                ds_std = ds_std.sortby(['y', 'x'])

                # 2. Variable Extraction and Level Squeezing
                # Per inspection: rainc/rainnc have a 'lev' dimension (size 1)
                if 'rainc' in ds_std and 'rainnc' in ds_std:
                    total_rain_da = ds_std['rainc'] + ds_std['rainnc']
                else:
                    return {}

                if 'lev' in total_rain_da.dims: 
                    total_rain_da = total_rain_da.squeeze('lev')

                # 3. Clip using 0.01 degree buffer for small basins
                clipped = total_rain_da.rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                weights = np.cos(np.deg2rad(clipped.y))
                basin_mean = clipped.weighted(weights).mean(dim=["x", "y"])

                daily_inc = {}
                # 4. Correct De-accumulation Logic
                # index 0 (00:00) is the start. Index 8 (24h mark) is the end of Day 1 (Run Date).
                prev_val = float(basin_mean.isel(time=0))
                time_indices = list(range(8, len(basin_mean), 8)) 
                
                for i, idx in enumerate(time_indices):
                    curr_val = float(basin_mean.isel(time=idx))
                    # Map correctly: i=0 corresponds to the initialization Run Date (given_date)
                    target_date = (datetime.strptime(given_date, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d')
                    daily_inc[target_date] = round(max(0.0, curr_val - prev_val), 4)
                    prev_val = curr_val
                
                return daily_inc
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing WRF for {station_name}: {e}"))
            return {}

    def calculate_flash_flood_forecast(self, combined_rainfall, basin_id, given_date):
        thresholds = STATION_THRESHOLDS_LIST[basin_id]
        forecast_start = pd.to_datetime(given_date)
        
        # Sort and ensure we only process from the run date forward
        all_dates = sorted(pd.to_datetime(list(combined_rainfall.keys())))
        process_dates = [d for d in all_dates if d >= forecast_start]

        results = {
            "Hours": {idx: val[0] for idx, val in thresholds.items()},
            "Thresholds": {idx: val[1] for idx, val in thresholds.items()}
        }

        for p_date in process_dates:
            day_results = {}
            for idx, (hours, _) in thresholds.items():
                days_to_sum = int(hours / 24)
                # Rolling backward summation window
                summation_range = [(p_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days_to_sum)]
                total_rain = sum(combined_rainfall.get(d, 0.0) for d in summation_range)
                day_results[idx] = round(total_rain, 2)
            results[p_date.strftime('%Y-%m-%d')] = day_results
        return results

    def main(self, date_input):
        for basin_id, station_name in STATION_DICT.items():
            json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(json_path): continue
            
            station_gdf = gpd.read_file(json_path, crs="epsg:4326")
            
            # --- GEOMETRY GUARD ---
            if station_gdf.empty or station_gdf.geometry.iloc[0] is None or station_gdf.geometry.iloc[0].is_empty:
                self.stdout.write(self.style.ERROR(f"  ❌ Skipping {station_name}: Geometry is empty/invalid."))
                continue

            obs = self.get_observed_rainfall(station_gdf, station_name, date_input)
            fcst = self.compute_basin_wise_forecast(station_gdf, station_name, date_input)
            
            if fcst:
                # Merge observed history with WRF forecast
                combined = {**obs, **fcst}
                response = self.calculate_flash_flood_forecast(combined, basin_id, date_input)
                
                # Verify we have enough data steps to form a valid forecast record
                if response and len(response) > 2:
                    rows = []
                    for date_key, values in response.items():
                        if date_key in ["Hours", "Thresholds"]: continue
                        for index, value in values.items():
                            rows.append(BMDWRFMonsoonBasinWiseFlashFloodForecast(
                                prediction_date=date_input,
                                basin_id=basin_id,
                                hours=response["Hours"][index],
                                thresholds=response["Thresholds"][index],
                                date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                                value=value
                            ))
                    
                    if rows:
                        BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=date_input, basin_id=basin_id).delete()
                        BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)
                        self.stdout.write(f"  ✅ Processed {station_name}")