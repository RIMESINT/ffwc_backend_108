# -*- coding: utf-8 -*-
import os
import math
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import warnings
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from data_load.models import UKMetPreMonsoonBasinWiseFlashFloodForecast

# Suppress the buffer warning for geographic CRS to keep logs clean
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

# --- Pre-Monsoon Configuration ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon'
}

STATION_THRESHOLDS = {
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
    help = 'Generates UKMet Deterministic Pre-Monsoon Flash Flood Forecasts with Day-0 Recovery.'

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Forecast date (YYYYMMDD format)')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Explicit argument flag injected by dashboard panel')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        date_input = raw_date or datetime.now().strftime('%Y-%m-%d')
        
        # Standardize formatting to YYYY-MM-DD layout standard safely
        if "-" not in date_input:
            try: 
                date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: 
                pass

        if not self.run_forecast_for_date(date_input):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Data missing for {date_input}. Trying yesterday: {yesterday}..."))
            self.run_forecast_for_date(yesterday)

    def get_daily_forecast_rainfall(self, station_gdf, station_name, given_date):
        date_str_nodash = given_date.replace('-', '')
        forecast_file = os.path.join(settings.BASE_DIR, "forecast", "ukmet_det_data", f"precip_{date_str_nodash}.nc")
        
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
                
                # 2. Geometry Sanitizer & Clipping
                clipped = da.rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                
                target_var = 'tp' if 'tp' in clipped.data_vars else list(clipped.data_vars)[0]
                data_array = clipped[target_var]
                
                # Unit check: conversion from meters to millimeters if required
                if ds[target_var].attrs.get('units') == 'm':
                    data_array = data_array * 1000

                daily_rainfall = {}
                weights = np.cos(np.deg2rad(data_array.y))
                
                # 3. Day-0 Recovery Execution Logic
                for idx, ts in enumerate(list(data_array.indexes['time'])):
                    mean_val = data_array.isel(time=idx).weighted(weights).mean(dim=['x', 'y']).item()
                    
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
        self.stdout.write(self.style.SUCCESS(f'--- UKMET Pre-Monsoon Deterministic Processing: {date_input} ---'))
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
                rows.append(UKMetPreMonsoonBasinWiseFlashFloodForecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=h_map[idx],
                    thresholds=t_map[idx],
                    value=val
                ))
        
        if rows:
            UKMetPreMonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            UKMetPreMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)