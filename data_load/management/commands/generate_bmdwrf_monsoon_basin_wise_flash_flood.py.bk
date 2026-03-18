import os
import math
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from datetime import datetime, timedelta

from django.core.management import BaseCommand
from django.conf import settings
from data_load.models import BMDWRFMonsoonBasinWiseFlashFloodForecast

# --- Static Configuration ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon',13:'amalshid'
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
    # 11: {0: [24, 9.732], 1: [48, 28.227], 2: [72, 52.625], 3: [120, 115.346], 4: [168, 193.415], 5: [240, 334.546]},
    11: {0: [24, 36.88], 1: [48, 60.99], 2: [72, 81.87], 3: [120, 118.63], 4: [168, 151.45], 5: [240, 196.20]},
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]},
    13: {0: [24, 13.04], 1: [48, 22.34], 2: [72, 30.61], 3: [120, 45.52], 4: [168, 59.12],5: [240, 77.99]}
}

class Command(BaseCommand):
    help = 'Generate Basin Wise Flashflood for BMD-WRF with automated insertion'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Initialization date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        if not date_input:
            date_input = datetime.now().strftime('%Y-%m-%d')
        
        self.stdout.write(self.style.SUCCESS(f"--- Starting Forecast for Date: {date_input} ---"))
        self.main(date_input)

    # --- Data Processing Methods ---

    def get_observed_rainfall(self, station_name, given_date):
        """Retrieves observed rainfall for the past 10 days."""
        daily_precip = {}
        given_dt = datetime.strptime(given_date, "%Y-%m-%d")
        basin_json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        station_gdf = gpd.read_file(basin_json_path)

        for i in range(1, 11):
            obs_date = given_dt - timedelta(days=i)
            filename = f"{obs_date.year}{obs_date.timetuple().tm_yday:03d}.nc"
            filepath = os.path.join(settings.BASE_DIR, "observed", filename)
            
            if os.path.exists(filepath):
                try:
                    with xr.open_dataset(filepath) as ds:
                        ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                        clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True)
                        weights = np.cos(np.deg2rad(clipped.lat))
                        val = clipped['precipitation'].weighted(weights).mean().item()
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = val
                except Exception:
                    continue
        return daily_precip

    def compute_basin_wise_forecast(self, station_name, given_date):
        """Processes WRF output to get daily incremental rainfall."""
        date_str_nodash = given_date.replace('-', '')
        filename = f'wrf_out_{date_str_nodash}00.nc'
        forecast_path = os.path.join(settings.BASE_DIR, 'forecast', filename)

        if not os.path.isfile(forecast_path):
            self.stdout.write(self.style.WARNING(f"Forecast file missing: {filename}"))
            return {}

        basin_json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        station_gdf = gpd.read_file(basin_json_path)

        try:
            with xr.open_dataset(forecast_path) as ds:
                ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True)
                
                # Combine rainc and rainnc, remove 'lev' dimension if present
                total_rain = clipped['rainc'] + clipped['rainnc']
                if 'lev' in total_rain.dims:
                    total_rain = total_rain.squeeze('lev')

                weights = np.cos(np.deg2rad(clipped.lat))
                basin_mean = total_rain.weighted(weights).mean(dim=["lon", "lat"])

                # WRF is 3-hourly: 8 steps = 24 hours
                max_idx = basin_mean.sizes['time'] - 1
                positional_indices = np.arange(8, max_idx + 1, 8)
                
                acc_values = basin_mean.isel(time=positional_indices)
                
                daily_inc = {}
                prev_val = 0
                for i, val in enumerate(acc_values.values):
                    target_date = (datetime.strptime(given_date, '%Y-%m-%d') + timedelta(days=i+1)).strftime('%Y-%m-%d')
                    incremental = max(0.0, float(val) - prev_val)
                    daily_inc[target_date] = round(incremental, 4)
                    prev_val = float(val)
                
                return daily_inc
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing WRF for {station_name}: {e}"))
            return {}

    def calculate_flash_flood_forecast(self, combined_rainfall, basin_id, given_date):
        """Calculates backward-looking cumulative rainfall vs thresholds."""
        thresholds = STATION_THRESHOLDS_LIST[basin_id]
        forecast_start = pd.to_datetime(given_date)
        all_dates = sorted(pd.to_datetime(list(combined_rainfall.keys())))
        process_dates = [d for d in all_dates if d >= forecast_start]

        if not process_dates:
            return {}

        # Prepare structure for transformIntoDataFrame
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

    # --- Database & Transformation Methods ---

    def transform_into_dataframe(self, data_dict, date_input, basin_id):
        """Converts results dictionary to a flat DataFrame for DB insertion."""
        rows = []
        for date_key, values in data_dict.items():
            if date_key in ["Hours", "Thresholds"]:
                continue
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
        """Clears existing records and performs a bulk insert."""
        if df.empty:
            return

        p_date = df['prediction_date'].iloc[0]
        b_id = df['basin_id'].iloc[0]

        # Cleanup existing records for this initialization to prevent duplicates
        BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.filter(
            prediction_date=p_date, basin_id=b_id
        ).delete()

        # Create model instances
        forecast_objects = [
            BMDWRFMonsoonBasinWiseFlashFloodForecast(**row) for _, row in df.iterrows()
        ]

        # Bulk create
        BMDWRFMonsoonBasinWiseFlashFloodForecast.objects.bulk_create(forecast_objects)
        self.stdout.write(f"  Inserted {len(forecast_objects)} records for Basin {b_id}.")

    # --- Main Execution Flow ---

    def main(self, date_input):
        for basin_id, station_name in STATION_DICT.items():
            self.stdout.write(f"Processing Basin ID: {basin_id} ({station_name})")
            
            # 1. Gather Data
            obs = self.get_observed_rainfall(station_name, date_input)
            fcst = self.compute_basin_wise_forecast(station_name, date_input)
            
            if not fcst:
                continue

            # 2. Combine and Calculate
            combined = {**obs, **fcst}
            response = self.calculate_flash_flood_forecast(combined, basin_id, date_input)

            # 3. Transform and Save
            if response and len(response) > 2:
                df = self.transform_into_dataframe(response, date_input, basin_id)
                self.insert_dataframe(df)
            else:
                self.stdout.write(self.style.WARNING(f"  No valid calculations for {station_name}"))

        self.stdout.write(self.style.SUCCESS(f"--- Process Completed for {date_input} ---"))