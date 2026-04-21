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
from data_load.models import UKMetMonsoonProbabilisticFlashFloodForecast

# Suppress technical warnings
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
    help = 'Generates 11-day UKMet Monsoon Probabilistic Forecasts with dynamic member detection and detailed tracing.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYYMMDD)')
        parser.add_argument('--trace', action='store_true', help='Show detailed tracing and rainfall amounts')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date') or datetime.now().strftime('%Y-%m-%d')
        trace = kwargs.get('trace')
        if "-" not in date_input:
            try: date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: pass

        if not self.run_forecast_for_date(date_input, trace):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Today's data missing. Trying yesterday: {yesterday}"))
            self.run_forecast_for_date(yesterday, trace)

    def process_ensemble_member(self, station_gdf, forecast_dir, filename, run_date_str):
        filepath = os.path.join(forecast_dir, filename)
        if not os.path.exists(filepath): return None
        run_date_obj = datetime.strptime(run_date_str, '%Y-%m-%d').date()
        try:
            with xr.open_dataset(filepath) as ds:
                x_dim = "longitude" if "longitude" in ds.coords else "lon"
                y_dim = "latitude" if "latitude" in ds.coords else "lat"
                da = ds.rename({x_dim: 'x', y_dim: 'y'})
                da.rio.set_spatial_dims(x_dim='x', y_dim='y', inplace=True)
                da.rio.write_crs("epsg:4326", inplace=True)
                da = da.sortby(['y', 'x'])
                clipped = da.rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                target_var = next((v for v in ['tp', 'thickness_of_rainfall_amount', 'precipitation'] if v in clipped.data_vars), None)
                if not target_var: return None
                data_array = clipped[target_var]
                if ds[target_var].attrs.get('units') == 'm':
                    data_array = data_array * 1000
                daily_ds = data_array.resample(time='1D').sum() if len(data_array.indexes['time']) > 15 else data_array
                daily_rainfall = {}
                weights = np.cos(np.deg2rad(daily_ds.y))
                for idx, ts in enumerate(list(daily_ds.indexes['time'])):
                    mean_val = daily_ds.isel(time=idx).weighted(weights).mean(dim=['x', 'y']).item()
                    key_date = run_date_str if (idx == 0 and ts.date() > run_date_obj) else ts.strftime('%Y-%m-%d')
                    daily_rainfall[key_date] = round(mean_val if not math.isnan(mean_val) else 0.0, 4)
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
                        mean_obs = clipped.weighted(weights).mean().item()
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = mean_obs
                except: pass
        return pd.DataFrame(list(daily_precip.items()), columns=['Date', 'Rainfall'])

    def calculate_exceedance_probability(self, all_member_rainfall, thresholds, given_date, station_name, trace):
            num_members = len(all_member_rainfall)
            combined_df = pd.DataFrame(all_member_rainfall).T.fillna(0)
            combined_df.index = pd.to_datetime(combined_df.index).normalize()
            start_dt = pd.to_datetime(given_date).normalize()
            
            forecast_range = [start_dt + timedelta(days=i) for i in range(12)]
            all_required_dates = sorted(list(set(combined_df.index).union(set(forecast_range))))
            combined_df = combined_df.reindex(all_required_dates, fill_value=0)
            
            # Ensure metadata keys are strings
            probability_results = {
                "Hours": {str(k): v[0] for k, v in thresholds.items()},
                "Thresholds": {str(k): v[1] for k, v in thresholds.items()}
            }

            if trace:
                self.stdout.write(f"\n{'-'*90}\nUKMET MONSOON BASIN: {station_name.upper()}\n{'-'*90}")

            for p_date in forecast_range:
                daily_probs = {}
                if trace:
                    self.stdout.write(f"\nDATE: {p_date.strftime('%Y-%m-%d')}")

                for idx, values in thresholds.items():
                    hour, threshold = values[0], values[1]
                    days_to_sum = int(hour / 24)
                    sum_range = [(p_date - timedelta(days=i)).normalize() for i in range(days_to_sum)]
                    try:
                        member_sums = combined_df.loc[sum_range].sum(axis=0)
                        mean_rainfall = member_sums.mean()
                        exceed_count = (member_sums >= threshold).sum()
                        prob = round((exceed_count / num_members) * 100, 2)
                        
                        # USE str(idx) HERE TO MATCH METADATA
                        daily_probs[str(idx)] = prob
                        
                        if trace:
                            self.stdout.write(
                                f"   Window: {hour:>3}h | Thresh: {threshold:7.2f}mm | "
                                f"Mean Rain: {mean_rainfall:7.2f}mm | Prob: {prob:6.2f}% ({exceed_count}/{num_members})"
                            )
                    except Exception:
                        daily_probs[str(idx)] = 0.0
                
                probability_results[p_date.strftime('%Y-%m-%d')] = daily_probs
            return probability_results

    def save_to_database(self, data_dict, prediction_date, basin_id):
        if not data_dict or "Hours" not in data_dict:
            return
        
        rows = []
        # Extract metadata
        h_meta = data_dict.get("Hours", {})
        t_meta = data_dict.get("Thresholds", {})

        for date_key, values in data_dict.items():
            # Skip metadata keys
            if date_key in ["Hours", "Thresholds"]:
                continue
            
            for idx_str, prob_value in values.items():
                # Ensure we have metadata for this index
                if idx_str in h_meta and idx_str in t_meta:
                    rows.append(UKMetMonsoonProbabilisticFlashFloodForecast(
                        prediction_date=prediction_date,
                        basin_id=basin_id,
                        date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                        hours=h_meta[idx_str],
                        thresholds=t_meta[idx_str],
                        value=prob_value if not math.isnan(prob_value) else 0.0
                    ))
        
        if rows:
            UKMetMonsoonProbabilisticFlashFloodForecast.objects.filter(
                prediction_date=prediction_date, 
                basin_id=basin_id
            ).delete()
            UKMetMonsoonProbabilisticFlashFloodForecast.objects.bulk_create(rows)

    def save_to_database(self, data_dict, prediction_date, basin_id):
        if not data_dict or "Hours" not in data_dict: return
        rows = []
        for date_key, values in data_dict.items():
            if date_key in ["Hours", "Thresholds"]: continue
            for index, value in values.items():
                rows.append(UKMetMonsoonProbabilisticFlashFloodForecast(
                    prediction_date=prediction_date, basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=data_dict["Hours"][index],
                    thresholds=data_dict["Thresholds"][index],
                    value=value if not math.isnan(value) else 0.0
                ))
        if rows:
            UKMetMonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            UKMetMonsoonProbabilisticFlashFloodForecast.objects.bulk_create(rows)

    def run_forecast_for_date(self, date_input, trace):
        self.stdout.write(self.style.SUCCESS(f'--- UKMET Monsoon Probabilistic Run: {date_input} ---'))
        success = False
        date_nodash = date_input.replace('-', '')
        forecast_dir = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_ens_data/ukmet_ens_{date_nodash}/"

        if not os.path.exists(forecast_dir): return False
        
        # DYNAMIC MEMBER DETECTION
        member_files = sorted([f for f in os.listdir(forecast_dir) if f.startswith('precip_EN') and f.endswith('.nc')])

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
            
            response = self.calculate_exceedance_probability(
                [{**obs_dict, **m} for m in all_members_data], 
                STATION_THRESHOLDS[basin_id], 
                date_input,
                station_name,
                trace
            )
            
            if response:
                self.save_to_database(response, date_input, basin_id)
                success = True
                self.stdout.write(f"  ✅ Processed {station_name} ({len(all_members_data)} members)")
        return success