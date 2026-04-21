# -*- coding: utf-8 -*-
import os
import math
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
import warnings
import rioxarray
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

# Target Model
from data_load.models import ECMWF_Monsoon_Probabilistic_Flash_Flood_Forecast

# Suppress technical warnings for cleaner logs
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

# --- Updated Configuration for Monsoon ---
STATION_DICT = {
    1: 'khaliajhuri', 2: 'gowainghat', 3: 'dharmapasha', 4: 'userbasin',
    5: 'laurergarh', 6: 'muslimpur', 7: 'debidwar', 8: 'ballah',
    9: 'habiganj', 10: 'parshuram', 11: 'cumilla', 12: 'nakuagaon', 13: 'amalshid'
}

STATION_THRESHOLDS = {
    1: {0: [24, 96.90], 1: [48, 162.83], 2: [72, 220.60], 3: [120, 323.39], 4: [168, 416.05], 5: [240, 543.43]},
    2: {0: [24, 62.92], 1: [48, 92.91], 2: [72, 116.71], 3: [120, 155.55], 4: [168, 187.95], 5: [240, 229.70]},
    3: {0: [24, 24.50], 1: [48, 41.50], 2: [72, 56.50], 3: [120, 83.00], 4: [168, 107.50], 5: [240, 141.00]},
    4: {0: [24, 25.00], 1: [48, 40.50], 2: [72, 53.50], 3: [120, 76.00], 4: [168, 96.00], 5: [240, 123.00]},
    5: {0: [24, 52.67], 1: [48, 65.83], 2: [72, 75.01], 3: [120, 88.42], 4: [168, 98.53], 5: [240, 110.52]},
    6: {0: [24, 33.50], 1: [48, 51.84], 2: [72, 66.93], 3: [120, 92.34], 4: [168, 114.14], 5: [240, 142.90]},
    7: {0: [24, 41.37], 1: [48, 59.11], 2: [72, 72.82], 3: [120, 94.72], 4: [168, 112.63], 5: [240, 135.33]},
    8: {0: [24, 28.77], 1: [48, 35.77], 2: [72, 40.63], 3: [120, 47.70], 4: [168, 53.02], 5: [240, 59.31]},
    9: {0: [24, 14.00], 1: [48, 22.00], 2: [72, 30.00], 3: [120, 44.00], 4: [168, 56.00], 5: [240, 73.00]},
    10: {0: [24, 48.54], 1: [48, 67.45], 2: [72, 81.77], 3: [120, 104.22], 4: [168, 122.27], 5: [240, 144.83]},
    11: {0: [24, 36.88], 1: [48, 60.99], 2: [72, 81.87], 3: [120, 118.63], 4: [168, 151.45], 5: [240, 196.20]},
    12: {0: [24, 30.52], 1: [48, 40.47], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]},
    13: {0: [24, 13.04], 1: [48, 22.34], 2: [72, 30.61], 3: [120, 45.52], 4: [168, 59.12], 5: [240, 77.99]}
}

class Command(BaseCommand):
    help = 'Generates ECMWF Probabilistic Flash Flood Forecasts using the ECMWF_Monsoon_Probabilistic_Flash_Flood_Forecast model.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYYMMDD)')
        parser.add_argument('--trace', action='store_true', help='Show detailed member tracing and rainfall amounts')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date') or datetime.now().strftime('%Y%m%d')
        trace = kwargs.get('trace')
        date_std = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')

        if not self.run_forecast_for_date(date_std, trace):
            yesterday = (datetime.strptime(date_std, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Today's data missing. Trying yesterday: {yesterday}..."))
            self.run_forecast_for_date(yesterday, trace)

    def process_ensemble_member(self, station_gdf, forecast_dir, filename, run_date_str):
        filepath = os.path.join(forecast_dir, filename)
        if not os.path.exists(filepath): return None
        run_date_obj = datetime.strptime(run_date_str, '%Y-%m-%d').date()
        try:
            with xr.open_dataset(filepath) as ds:
                da = ds.rename({'lon': 'x', 'lat': 'y'})
                da.rio.set_spatial_dims(x_dim='x', y_dim='y', inplace=True)
                da.rio.write_crs("epsg:4326", inplace=True)
                da = da.sortby(['y', 'x'])
                clipped = da['tp'].rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                weights = np.cos(np.deg2rad(clipped.y))
                mean_series = clipped.weighted(weights).mean(dim=['x', 'y']).to_series() * 1000
                daily_accumulation = mean_series.resample('1D').max()
                daily_incremental = daily_accumulation.diff().fillna(daily_accumulation.iloc[0])
                daily_incremental[daily_incremental < 0] = 0
                daily_rainfall = {}
                for d, v in daily_incremental.items():
                    key_date = run_date_str if (d.date() > run_date_obj and not daily_rainfall) else d.strftime('%Y-%m-%d')
                    daily_rainfall[key_date] = round(v, 4)
                return daily_rainfall
        except Exception as e:
            return None

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
                        ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                        clipped = ds_std['precipitation'].rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                        weights = np.cos(np.deg2rad(clipped.y))
                        val = clipped.weighted(weights).mean().item()
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = val
                except: pass
            else:
                daily_precip[obs_date.strftime('%Y-%m-%d')] = 0.0
        return pd.DataFrame(list(daily_precip.items()), columns=['Date', 'Rainfall'])

    def calculate_exceedance_probability(self, all_member_rainfall, thresholds, given_date, station_name, trace):
        num_members = len(all_member_rainfall)
        combined_df = pd.DataFrame(all_member_rainfall).T.fillna(0)
        combined_df.index = pd.to_datetime(combined_df.index).normalize()
        start_dt = pd.to_datetime(given_date).normalize()
        
        # EXTENDED RANGE: range(12) for 11 forecast days
        forecast_range = [start_dt + timedelta(days=i) for i in range(12)]
        full_index = sorted(list(set(combined_df.index).union(set(forecast_range))))
        combined_df = combined_df.reindex(full_index, fill_value=0)
        
        probability_results = {
            "Hours": {str(k): v[0] for k, v in thresholds.items()},
            "Threshold": {str(k): v[1] for k, v in thresholds.items()}
        }
        
        if trace:
            self.stdout.write(f"\n{'-'*90}\nMONSOON BASIN: {station_name.upper()}\n{'-'*90}")

        for p_date in forecast_range:
            daily_probs = {}
            if trace:
                self.stdout.write(f"\nDATE: {p_date.strftime('%Y-%m-%d')}")

            for idx, values in thresholds.items():
                hour, threshold = values[0], values[1]
                days_to_sum = int(hour / 24)
                sum_range = [(p_date - timedelta(days=i)).normalize() for i in range(days_to_sum)]
                
                member_sums = combined_df.loc[sum_range].sum(axis=0)
                mean_rainfall = member_sums.mean()
                
                exceed_count = (member_sums >= threshold).sum()
                prob = round((exceed_count / num_members) * 100, 2)
                daily_probs[str(idx)] = prob

                if trace:
                    self.stdout.write(
                        f"   Window: {hour:>3}h | Thresh: {threshold:7.2f}mm | "
                        f"Mean Rain: {mean_rainfall:7.2f}mm | Prob: {prob:6.2f}% ({exceed_count}/{num_members})"
                    )

            probability_results[p_date.strftime('%Y-%m-%d')] = daily_probs
        return probability_results

    def save_to_database(self, results, prediction_date, basin_id):
        rows = []
        h_meta, t_meta = results.get("Hours", {}), results.get("Threshold", {})
        for date_key, values in results.items():
            if date_key in ["Hours", "Threshold"]: continue
            for idx_str, prob_val in values.items():
                rows.append(ECMWF_Monsoon_Probabilistic_Flash_Flood_Forecast(
                    prediction_date=prediction_date, basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=int(h_meta.get(idx_str)), thresholds=float(t_meta.get(idx_str)), 
                    value=float(prob_val)
                ))
        if rows:
            ECMWF_Monsoon_Probabilistic_Flash_Flood_Forecast.objects.filter(
                prediction_date=prediction_date, basin_id=basin_id
            ).delete()
            ECMWF_Monsoon_Probabilistic_Flash_Flood_Forecast.objects.bulk_create(rows)

    def run_forecast_for_date(self, date_input, trace):
        self.stdout.write(self.style.SUCCESS(f'--- Starting Monsoon 11-Day Probabilistic Calculation: {date_input} ---'))
        date_nodash = date_input.replace('-', '')
        forecast_dir = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_ens_data/{date_nodash}/"
        if not os.path.exists(forecast_dir): return False
        
        # DYNAMIC MEMBER DETECTION
        member_files = sorted([f for f in os.listdir(forecast_dir) if f.startswith(date_nodash) and f.endswith('.nc')])
        
        for basin_id, station_name in STATION_DICT.items():
            json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(json_path): continue
            station_gdf = gpd.read_file(json_path, crs="epsg:4326")
            all_members_data = []
            for fname in member_files:
                res = self.process_ensemble_member(station_gdf, forecast_dir, fname, date_input)
                if res: all_members_data.append(res)
            if not all_members_data: continue
            
            obs_df = self.get_observed_rainfall(station_gdf, date_input)
            obs_dict = dict(zip(obs_df['Date'], obs_df['Rainfall']))
            combined_rainfall_list = [{**obs_dict, **m} for m in all_members_data]
            
            response = self.calculate_exceedance_probability(
                combined_rainfall_list, STATION_THRESHOLDS[basin_id], date_input, station_name, trace
            )
            if response:
                self.save_to_database(response, date_input, basin_id)
                self.stdout.write(f"  ✅ Processed {station_name} ({len(all_members_data)} members detected)")
        return True