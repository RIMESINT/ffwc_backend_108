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
    10: {0: [24, 48.22], 1: [48, 67.37], 2: [72, 81.94], 3: [120, 104.84], 4: [168, 123.33], 5: [240, 146.50]},
    11: {0: [24, 36.88], 1: [48, 60.99], 2: [72, 81.87], 3: [120, 118.63], 4: [168, 151.45], 5: [240, 196.20]},
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]},
    13: {0: [24, 13.04], 1: [48, 22.34], 2: [72, 30.61], 3: [120, 45.52], 4: [168, 59.12], 5: [240, 77.99]}
}

class Command(BaseCommand):
    help = 'Generate Monsoon Basin Wise Flashflood for BMD-WRF'

    def add_arguments(self, parser):
        # FIX: Renamed positional variable to 'fdate' to resolve structural parsing overwrite bugs
        parser.add_argument('fdate', nargs='?', type=str, help='Initialization date (YYYYMMDD or YYYY-MM-DD)')
        # Explicit option parameter support for Django Admin UI layout hooks
        parser.add_argument('--date', type=str, help='Explicit argument flag injected by dashboard panel')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date
        
        # Fallback to current system timestamp if parameter fields are completely blank
        date_input = raw_date or datetime.now().strftime('%Y-%m-%d')
        
        # Standardize formatting to YYYY-MM-DD layout safely
        if "-" not in date_input:
            try: 
                date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: 
                pass
                
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
                        ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                        ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                        clipped = ds_std['precipitation'].rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                        weights = np.cos(np.deg2rad(clipped.y))
                        val = clipped.weighted(weights).mean().item()
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = val
                except: continue
        return daily_precip

    def compute_basin_wise_forecast(self, station_gdf, station_name, given_date):
        date_str_nodash = given_date.replace('-', '')
        filename = f'wrf_out_{date_str_nodash}00.nc'
        forecast_path = os.path.join(settings.BASE_DIR, "forecast", "bmd_wrf", filename)
        if not os.path.isfile(forecast_path): return {}
        try:
            with xr.open_dataset(forecast_path) as ds:
                ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                ds_std = ds_std.sortby(['y', 'x'])
                if 'rainc' in ds_std and 'rainnc' in ds_std:
                    total_rain_da = ds_std['rainc'] + ds_std['rainnc']
                else: return {}
                if 'lev' in total_rain_da.dims: total_rain_da = total_rain_da.squeeze('lev')
                clipped = total_rain_da.rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                weights = np.cos(np.deg2rad(clipped.y))
                basin_mean = clipped.weighted(weights).mean(dim=["x", "y"])
                daily_inc = {}
                prev_val = float(basin_mean.isel(time=0))
                time_indices = list(range(8, len(basin_mean), 8)) 
                for i, idx in enumerate(time_indices):
                    curr_val = float(basin_mean.isel(time=idx))
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
        all_dates = sorted(pd.to_datetime(list(combined_rainfall.keys())))
        process_dates = [d for d in all_dates if d >= forecast_start]
        results = {}
        for p_date in process_dates:
            day_results = []
            for _, (hours, threshold_val) in thresholds.items():
                days_to_sum = int(hours / 24)
                summation_range = [(p_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days_to_sum)]
                total_rain = sum(combined_rainfall.get(d, 0.0) for d in summation_range)
                day_results.append({
                    "hours": hours,
                    "threshold": threshold_val,
                    "value": round(total_rain, 2)
                })
            results[p_date.strftime('%Y-%m-%d')] = day_results
        return results

    def main(self, date_input):
        for basin_id, station_name in STATION_DICT.items():
            json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(json_path): continue
            station_gdf = gpd.read_file(json_path, crs="epsg:4326")
            if station_gdf.empty or station_gdf.geometry.iloc[0] is None or station_gdf.geometry.iloc[0].is_empty: continue
            obs = self.get_observed_rainfall(station_gdf, station_name, date_input)
            fcst = self.compute_basin_wise_forecast(station_gdf, station_name, date_input)
            if fcst:
                combined = {**obs, **fcst}
                response = self.calculate_flash_flood_forecast(combined, basin_id, date_input)
                if response:
                    rows = []
                    for date_key, records_list in response.items():
                        for record in records_list:
                            rows.append(BMDWRFMonsoonBasinWiseFlashFloodForecast(
                                prediction_date=date_input,
                                basin_id=basin_id,
                                hours=record['hours'],
                                thresholds=record['threshold'],
                                date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                                value=record['value']
                            ))
                    if rows:
                        BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=date_input, basin_id=basin_id).delete()
                        BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)
                        self.stdout.write(f"  ✅ Processed {station_name}")