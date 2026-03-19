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

# Pointing to the pre-monsoon model
from data_load.models import Basin_Wise_Flash_Flood_Forecast

# Suppress the WRF-specific reference date warnings
warnings.filterwarnings("ignore", category=SerializationWarning, module='xarray.coding.times')

# --- Pre-Monsoon Static Configuration ---
STATION_DICT = { 
    1:'khaliajhuri', 2:'gowainghat', 3:'dharmapasha', 4:'userbasin',
    5:'laurergarh', 6:'muslimpur', 7:'debidwar', 8:'ballah',
    9:'habiganj', 10:'parshuram', 11:'cumilla', 12:'nakuagaon'
}

STATION_THRESHOLDS_LIST = {
    1: {0:[24,51.45], 1:[48,77.5], 2:[72,98.3], 3:[120,133], 4:[168,162], 5:[240,200]},
    2: {0:[24,24.5], 1:[48,41.5], 2:[72,56.5], 3:[120,83], 4:[168,107.5], 5:[240,141]},
    3: {0:[24,24.5], 1:[48,41.5], 2:[72,56.5], 3:[120,83], 4:[168,107.5], 5:[240,141]},
    4: {0:[24,25], 1:[48,40.5], 2:[72,53.5], 3:[120,76], 4:[168,96], 5:[240,123]},
    5: {0:[24,34], 1:[48,46.3], 2:[72,55.4], 3:[120,69.37], 4:[168,80.5], 5:[240,94]},
    6: {0:[24,33.50], 1:[48,51.84], 2:[72,66.93], 3:[120,92.34], 4:[168,114.14], 5:[240,142.90]},
    7: {0:[24,54], 1:[48,87], 2:[72,115], 3:[120,164], 4:[168,207], 5:[240,264]},
    8: {0:[24,15], 1:[48,26], 2:[72,35], 3:[120,52], 4:[168,68], 5:[240,90]},
    9: {0:[24,14], 1:[48,22], 2:[72,30], 3:[120,44], 4:[168,56], 5:[240,73]},
    10: {0:[24,17], 1:[48,29], 2:[72,39], 3:[120,58], 4:[168,75], 5:[240,99]},
    11: {0:[24,32], 1:[48,49], 2:[72,63], 3:[120,87], 4:[168,108], 5:[240,135]},
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]}
}

class Command(BaseCommand):
    help = 'Generate Basin Wise Flashflood for BMD-WRF Pre-Monsoon'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Initialization date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        if not date_input:
            date_input = datetime.now().strftime('%Y-%m-%d')
        
        if "-" not in date_input:
            try:
                date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: pass

        self.stdout.write(self.style.SUCCESS(f"--- Starting BMD-WRF Pre-Monsoon Forecast: {date_input} ---"))
        self.main(date_input)

    def get_observed_rainfall(self, station_name, given_date):
        daily_precip = {}
        given_dt = datetime.strptime(given_date, "%Y-%m-%d")
        basin_json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        station_gdf = gpd.read_file(basin_json_path, crs="epsg:4326")

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
                        val = clipped['precipitation'].weighted(weights).mean().item()
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = val
                except: continue
        return daily_precip

    def compute_basin_wise_forecast(self, station_name, given_date):
        date_str_nodash = given_date.replace('-', '')
        filename = f'wrf_out_{date_str_nodash}00.nc'
        forecast_path = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/bmd_wrf/{filename}"

        if not os.path.isfile(forecast_path):
            self.stdout.write(self.style.WARNING(f"File missing: {forecast_path}"))
            return {}

        basin_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        station_gdf = gpd.read_file(basin_json, crs="epsg:4326")

        try:
            with xr.open_dataset(forecast_path) as ds:
                ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                ds = ds.sortby(['lat', 'lon'])
                clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True, all_touched=True)
                
                target_var = None
                for var in ['rainc', 'tp', 'precip', 'precip_total']:
                    if var in [v.lower() for v in clipped.data_vars]:
                        target_var = next(v for v in clipped.data_vars if v.lower() == var)
                        break

                if not target_var:
                    if 'rainc' in clipped and 'rainnc' in clipped:
                        total_rain = clipped['rainc'] + clipped['rainnc']
                    else:
                        return {}
                else:
                    total_rain = clipped[target_var]

                if 'lev' in total_rain.dims: 
                    total_rain = total_rain.squeeze('lev')

                weights = np.cos(np.deg2rad(clipped.lat))
                basin_mean = total_rain.weighted(weights).mean(dim=["lon", "lat"])

                daily_inc = {}
                prev_val = 0.0
                time_indices = list(range(8, len(basin_mean), 8)) 
                
                for i, idx in enumerate(time_indices):
                    curr_val = float(basin_mean.isel(time=idx))
                    target_date = (datetime.strptime(given_date, '%Y-%m-%d') + timedelta(days=i+1)).strftime('%Y-%m-%d')
                    incremental = max(0.0, curr_val - prev_val)
                    daily_inc[target_date] = round(incremental, 4)
                    prev_val = curr_val
                
                return daily_inc
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in {station_name}: {e}"))
            return {}

    def calculate_flash_flood_forecast(self, combined_rainfall, basin_id, given_date):
        thresholds = STATION_THRESHOLDS_LIST[basin_id]
        forecast_start = pd.to_datetime(given_date)
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
                summation_range = [p_date - timedelta(days=i) for i in range(days_to_sum)]
                total_rain = sum(combined_rainfall.get(d.strftime('%Y-%m-%d'), 0) for d in summation_range)
                day_results[idx] = round(total_rain, 2)
            results[p_date.strftime('%Y-%m-%d')] = day_results
        return results

    def transform_into_dataframe(self, data_dict, date_input, basin_id):
        rows = []
        for date_key, values in data_dict.items():
            if date_key in ["Hours", "Thresholds"]: continue
            for index, value in values.items():
                rows.append({
                    'prediction_date': date_input,
                    'basin_id': basin_id,
                    'hours': data_dict["Hours"][index],
                    'thresholds': data_dict["Thresholds"][index],
                    'date': datetime.strptime(date_key, "%Y-%m-%d").date(),
                    'value': value
                })
        return pd.DataFrame(rows)

    def insert_dataframe(self, df):
        if df.empty: return
        p_date, b_id = df['prediction_date'].iloc[0], df['basin_id'].iloc[0]
        # Targets the Pre-Monsoon model
        Basin_Wise_Flash_Flood_Forecast.objects.filter(prediction_date=p_date, basin_id=b_id).delete()
        forecast_objects = [Basin_Wise_Flash_Flood_Forecast(**row) for _, row in df.iterrows()]
        Basin_Wise_Flash_Flood_Forecast.objects.bulk_create(forecast_objects)
        self.stdout.write(self.style.SUCCESS(f"  Inserted {len(forecast_objects)} Pre-Monsoon records for Basin {b_id}."))

    def main(self, date_input):
        for basin_id, station_name in STATION_DICT.items():
            self.stdout.write(f"Calculating Basin {basin_id}: {station_name}")
            obs = self.get_observed_rainfall(station_name, date_input)
            fcst = self.compute_basin_wise_forecast(station_name, date_input)
            
            if fcst:
                combined = {**obs, **fcst}
                response = self.calculate_flash_flood_forecast(combined, basin_id, date_input)
                if response and len(response) > 2:
                    df = self.transform_into_dataframe(response, date_input, basin_id)
                    self.insert_dataframe(df)