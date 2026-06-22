# -*- coding: utf-8 -*-
import os
import math
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import warnings
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.conf import settings
from data_load.models import MonsoonBasinWiseFlashFloodForecast

# Suppress CRS buffer warnings for cleaner output
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

# --- Station/Basin Configuration ---
stationDict = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon', 13: 'amalshid'
}

stationThresholds = {
    1: {24: 96.89950599, 48: 162.8320331, 72: 220.5977546, 120: 323.3900146, 168: 416.0549444, 240: 543.4315997},
    2: {24: 62.91949742, 48: 92.91302073, 72: 116.7093532, 120: 155.5491175, 168: 187.9516346, 240: 229.6988847},
    3: {24: 24.5, 48: 41.5, 72: 56.5, 120: 83, 168: 107.5, 240: 141},
    4: {24: 25, 48: 40.5, 72: 53.5, 120: 76, 168: 96, 240: 123},
    5: {24: 52.66627048, 48: 65.83191795, 72: 75.01043443, 120: 88.41715826, 168: 98.53177944, 240: 110.5199031},
    6: {24: 33.50, 48: 51.84, 72: 66.93, 120: 92.34, 168: 114.14, 240: 142.90},
    7: {24: 41.37244531, 48: 59.10820306, 72: 72.82489007, 120: 94.72459479, 168: 112.6349373, 240: 135.331633},
    8: {24: 28.77247366, 48: 35.77137016, 72: 40.63017364, 120: 47.70181973, 168: 53.01955989, 240: 59.30527458},
    9: {24: 14, 48: 22, 72: 30, 120: 44, 168: 56, 240: 73},
    10: {24: 48.53562859, 48: 67.45165462, 72: 81.77158915, 120: 104.2169518, 168: 122.2704102, 240: 144.8339302},
    11: {24: 36.8802, 48: 60.998, 72: 81.87342, 120: 118.6278, 168: 151.4478, 240: 196.2044},
    12: {24: 30.52, 48: 40.468, 72: 47.73, 120: 58.75, 168: 67.37, 240: 77.89},
    13: {24: 13.04, 48: 22.34, 72: 30.61, 120: 45.52, 168: 59.12, 240: 77.99}
}

class Command(BaseCommand):
    help = 'Processes ECMWF Monsoon files with Day-0 Recovery and Spatial Fixes'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD or YYYYMMDD)')

    def handle(self, *args, **options):
        date_input = options['date'] or datetime.today().strftime('%Y-%m-%d')
        
        try:
            dt_obj = datetime.strptime(date_input, "%Y-%m-%d") if "-" in date_input else datetime.strptime(date_input, "%Y%m%d")
            standard_date = dt_obj.strftime('%Y-%m-%d')
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid date: {date_input}"))
            return

        self.stdout.write(self.style.SUCCESS(f"🚀 Starting ECMWF Monsoon: {standard_date}"))

        for basin_id, station_name in stationDict.items():
            station_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(station_json): continue
            
            stationGDF = gpd.read_file(station_json, crs="epsg:4326")
            if stationGDF.empty or stationGDF.geometry.iloc[0] is None: continue

            # 1. Compute Observed (10 Days back)
            daily_obs = {}
            for i in range(1, 11):
                obs_dt = dt_obj - timedelta(days=i)
                obs_file = f"{obs_dt.year}{obs_dt.timetuple().tm_yday:03d}.nc"
                daily_obs = self.compute_observed_mean(obs_file, stationGDF, daily_obs)

            # 2. Compute Forecast
            daily_forecast = self.compute_forecast_mean(stationGDF, station_name, standard_date)
            
            if not daily_forecast:
                continue

            # 3. Combine Datasets
            df_obs = pd.DataFrame({'Date': list(daily_obs.keys()), 'Rainfall': list(daily_obs.values())})
            df_fc = pd.DataFrame({'Date': list(daily_forecast.keys()), 'Rainfall': list(daily_forecast.values())})
            all_records = pd.concat([df_obs, df_fc]).sort_values('Date').drop_duplicates('Date').reset_index(drop=True)

            self.save_to_db(all_records, standard_date, basin_id)

    def compute_forecast_mean(self, stationGDF, station_name, given_date):
        forecast_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/"
        dt_obj = datetime.strptime(given_date, '%Y-%m-%d')
        
        file_path = ""
        actual_run_date = dt_obj
        for offset in [0, 1]:
            curr_date = dt_obj - timedelta(days=offset)
            fname = curr_date.strftime('%d%m%Y') + ".nc"
            p = os.path.join(forecast_dir, fname)
            if os.path.exists(p):
                file_path = p
                actual_run_date = curr_date
                break
        
        if not file_path: return {}

        try:
            with xr.open_dataset(file_path) as ds:
                # Resolve coordinate naming mismatch
                da = ds.rename({'longitude': 'x', 'latitude': 'y'})
                da.rio.set_spatial_dims(x_dim='x', y_dim='y', inplace=True)
                da.rio.write_crs("epsg:4326", inplace=True)
                da = da.sortby(['y', 'x'])

                # Inspection confirmed 'cp' as the data variable
                target_var = 'cp' if 'cp' in da.data_vars else list(da.data_vars)[0]
                
                # Clip with Buffer and all_touched for high spatial accuracy
                clipped_da = da[target_var].rio.clip(stationGDF.geometry.buffer(0.01), stationGDF.crs, drop=True, all_touched=True)
                
                # Spatial Weighted Mean
                weights = np.cos(np.deg2rad(clipped_da.y))
                mean_series = clipped_da.weighted(weights).mean(dim=["x", "y"]).to_series()
                
                # Conversion: Mg/m^2 to mm (multiplier 1000)
                mean_series = mean_series * 1000
                
                # --- De-accumulation Logic ---
                # Daily total is the max value at end of day minus max value at start of day
                daily_accumulation = mean_series.resample('1D').max()
                daily_incremental = daily_accumulation.diff().fillna(daily_accumulation.iloc[0])
                daily_incremental[daily_incremental < 0] = 0

                results = {}
                for d, v in daily_incremental.items():
                    # Day-0 recovery logic: if first slice is dated tomorrow, attribute to Run Date
                    if d.date() > actual_run_date.date() and not results:
                        key_date = actual_run_date.strftime('%Y-%m-%d')
                    else:
                        key_date = d.strftime('%Y-%m-%d')
                    results[key_date] = round(v, 4)
                return results
        except Exception as e:
            self.stderr.write(f"      ⚠️ Forecast Error ({station_name}): {e}")
            return {}

    def compute_observed_mean(self, fileName, stationGDF, dailyPrecipitationDict):
        obs_path = os.path.join(settings.BASE_DIR, 'observed', fileName)
        if not os.path.exists(obs_path): return dailyPrecipitationDict

        try:
            with xr.open_dataset(obs_path) as ds:
                ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
                ds_std.rio.write_crs("epsg:4326", inplace=True)
                
                clipped = ds_std['precipitation'].rio.clip(stationGDF.geometry.buffer(0.01), "epsg:4326", drop=True, all_touched=True)
                weights = np.cos(np.deg2rad(clipped.y))
                val = clipped.weighted(weights).mean().item()
                
                date_key = ds.indexes['time'][0].strftime('%Y-%m-%d')
                dailyPrecipitationDict[date_key] = val
        except: pass
        return dailyPrecipitationDict

    def save_to_db(self, all_records, prediction_date, basin_id):
        dt_pred = datetime.strptime(prediction_date, '%Y-%m-%d')
        dict_rainfall = dict(zip(all_records['Date'], all_records['Rainfall']))
        hour_list = [24, 48, 72, 120, 168, 240]
        
        last_date = datetime.strptime(all_records['Date'].iloc[-1], '%Y-%m-%d')
        forecast_days = (last_date - dt_pred).days
        
        rows = []
        for day_offset in range(forecast_days + 1):
            current_dt = dt_pred + timedelta(days=day_offset)
            for hr in hour_list:
                # Rolling cumulative sum across the hourly window
                cum_sum = sum(dict_rainfall.get((current_dt - timedelta(days=d)).strftime('%Y-%m-%d'), 0.0) for d in range(int(hr/24)))
                
                rows.append(MonsoonBasinWiseFlashFloodForecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=current_dt.date(),
                    hours=hr,
                    thresholds=stationThresholds[basin_id][hr],
                    value=round(cum_sum, 2)
                ))
        
        if rows:
            MonsoonBasinWiseFlashFloodForecast.objects.filter(
                prediction_date=prediction_date, basin_id=basin_id
            ).delete()
            MonsoonBasinWiseFlashFloodForecast.objects.bulk_create(rows)
            self.stdout.write(f"  ✅ Saved Basin {basin_id}")