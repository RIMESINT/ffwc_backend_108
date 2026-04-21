import os
import math
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
import warnings
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

# Target Model
from data_load.models import UKMetPreMonsoonProbabilisticFlashFloodForecast

# Suppress the buffer warning for geographic CRS
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

# --- Pre-Monsoon Configuration ---
STATION_DICT = { 
    1:'khaliajhuri', 2:'gowainghat', 3:'dharmapasha', 4:'userbasin',
    5:'laurergarh', 6:'muslimpur', 7:'debidwar', 8:'ballah',
    9:'habiganj', 10:'parshuram', 11:'cumilla', 12:'nakuagaon'
}

STATION_THRESHOLDS = {
    1: {0: [24, 51.45], 1: [48, 77.5], 2: [72, 98.3], 3: [120, 133.0], 4: [168, 162.0], 5: [240, 200.0]},
    2: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    3: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83.0], 4: [168, 107.5], 5: [240, 141.0]},
    4: {0: [24, 25.0], 1: [48, 40.5], 2: [72, 53.5], 3: [120, 76.0], 4: [168, 96.0], 5: [240, 123.0]},
    5: {0: [24, 34.0], 1: [48, 46.3], 2: [72, 55.4], 3: [120, 69.37], 4: [168, 80.5], 5: [240, 94.0]},
    6: {0: [24, 33.50], 1: [48, 51.84], 2: [72, 66.93], 3: [120, 92.34], 4: [168, 114.14], 5: [240, 142.90]},
    7: {0: [24, 54.0], 1: [48, 87.0], 2: [72, 115.0], 3: [120, 164.0], 4: [168, 207.0], 5: [240, 264.0]},
    8: {0: [24, 15.0], 1: [48, 26.0], 2: [72, 35.0], 3: [120, 52.0], 4: [168, 68.0], 5: [240, 90.0]},
    9: {0: [24, 14.0], 1: [48, 22.0], 2: [72, 30.0], 3: [120, 44.0], 4: [168, 56.0], 5: [240, 73.0]},
    10: {0: [24, 17.0], 1: [48, 29.0], 2: [72, 39.0], 3: [120, 58.0], 4: [168, 75.0], 5: [240, 99.0]},
    11: {0: [24, 32.0], 1: [48, 49.0], 2: [72, 63.0], 3: [120, 87.0], 4: [168, 108.0], 5: [240, 135.0]},
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]}
}

class Command(BaseCommand):
    help = 'Generates UKMet Probabilistic PRE-MONSOON Flash Flood Forecasts with robust spatial logic.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date') or datetime.now().strftime('%Y-%m-%d')
        if "-" not in date_input:
            try: date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: pass

        if not self.run_forecast_for_date(date_input):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Data missing for {date_input}. Trying {yesterday}..."))
            self.run_forecast_for_date(yesterday)

    def process_ensemble_member(self, station_gdf, forecast_dir, filename, run_date_str):
        filepath = os.path.join(forecast_dir, filename)
        if not os.path.exists(filepath): return None
        run_date_obj = datetime.strptime(run_date_str, '%Y-%m-%d').date()

        try:
            with xr.open_dataset(filepath) as ds:
                # Explicit spatial setup (using full names for UKMET Forecast)
                x_dim, y_dim = "longitude", "latitude"
                if x_dim not in ds.coords: x_dim, y_dim = "lon", "lat"
                
                # Assign corrected dimensions to the variable itself
                da = ds.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim).rio.write_crs("epsg:4326")
                
                # Clip using the variable instead of the dataset to avoid coordinate loss
                target_var = next((v for v in ['tp', 'thickness_of_rainfall_amount', 'precipitation'] if v in da.data_vars), None)
                if not target_var: return None
                
                clipped_da = da[target_var].rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                
                if ds[target_var].attrs.get('units') != 'mm':
                    clipped_da = clipped_da * 1000

                # Handle sub-daily vs already daily
                daily_ds = clipped_da.resample(time='1D').sum() if len(clipped_da.indexes['time']) > 15 else clipped_da

                daily_rainfall = {}
                weights = np.cos(np.deg2rad(daily_ds[y_dim]))
                for idx, ts in enumerate(list(daily_ds.indexes['time'])):
                    mean_val = daily_ds.isel(time=idx).weighted(weights).mean(dim=[x_dim, y_dim]).item()
                    key_date = run_date_str if (idx == 0 and ts.date() > run_date_obj) else ts.strftime('%Y-%m-%d')
                    daily_rainfall[key_date] = round(mean_val if not math.isnan(mean_val) else 0.0, 4)
                
                return daily_rainfall
        except Exception as e:
            print(f"      ⚠️ Error processing forecast {filename}: {e}")
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
                        # FIX: Explicitly handle Observed coordinates (lon/lat)
                        # We use .rename() to ensure rioxarray sees 'x' and 'y' if auto-detection fails
                        ds_std = ds.rename({'lon': 'x', 'lat': 'y'})
                        ds_std.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
                        ds_std.rio.write_crs("epsg:4326", inplace=True)
                        
                        # Clip the DataArray specifically
                        clipped = ds_std['precipitation'].rio.clip(station_gdf.geometry.buffer(0.01), station_gdf.crs, drop=True, all_touched=True)
                        weights = np.cos(np.deg2rad(clipped.y))
                        val = clipped.weighted(weights).mean().item()
                        
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = val
                except Exception as e:
                    print(f"      ⚠️ Error processing observed {filename}: {e}")
            else:
                daily_precip[obs_date.strftime('%Y-%m-%d')] = 0.0
        return pd.DataFrame(list(daily_precip.items()), columns=['Date', 'Rainfall'])

    def calculate_exceedance_probability(self, all_member_rainfall, thresholds, given_date):
        if not all_member_rainfall: return {}
        num_members = len(all_member_rainfall)
        probability_results = {
            "Hours": {str(k): v[0] for k, v in thresholds.items()},
            "Threshold": {str(k): v[1] for k, v in thresholds.items()}
        }
        combined_df = pd.DataFrame(all_member_rainfall).T.fillna(0)
        combined_df.index = pd.to_datetime(combined_df.index).normalize()
        start_dt = pd.to_datetime(given_date).normalize()
        forecast_range = [start_dt + timedelta(days=i) for i in range(10)]
        combined_df = combined_df.reindex(sorted(list(set(combined_df.index).union(set(forecast_range)))), fill_value=0)
        
        for p_date in forecast_range:
            daily_probs = {}
            for idx, values in thresholds.items():
                hour, threshold = values[0], values[1]
                sum_range = [(p_date - timedelta(days=i)).normalize() for i in range(int(hour / 24))]
                try:
                    exceed_count = (combined_df.loc[sum_range].sum(axis=0) >= threshold).sum()
                    daily_probs[str(idx)] = round((exceed_count / num_members) * 100, 2)
                except: daily_probs[str(idx)] = 0.0
            probability_results[p_date.strftime('%Y-%m-%d')] = daily_probs
        return probability_results

    def save_to_database(self, results, prediction_date, basin_id):
        rows = []
        h_meta, t_meta = results.get("Hours", {}), results.get("Threshold", {})
        for date_key, values in results.items():
            if date_key in ["Hours", "Threshold"]: continue
            for idx_str, prob_val in values.items():
                rows.append(UKMetPreMonsoonProbabilisticFlashFloodForecast(
                    prediction_date=prediction_date, basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=h_meta.get(idx_str), thresholds=t_meta.get(idx_str), value=prob_val
                ))
        if rows:
            UKMetPreMonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            UKMetPreMonsoonProbabilisticFlashFloodForecast.objects.bulk_create(rows)

    def run_forecast_for_date(self, date_input):
        self.stdout.write(self.style.SUCCESS(f'--- UKMET Probabilistic Pre-Monsoon Run: {date_input} ---'))
        success = False
        peak_prob, peak_info = 0.0, "N/A"
        risk_categories = {"CRITICAL (>=75%)": [], "WARNING (50-74%)": [], "WATCH (10-49%)": []}
        date_nodash = date_input.replace('-', '')
        forecast_dir = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_ens_data/ukmet_ens_{date_nodash}/"

        for basin_id, station_name in STATION_DICT.items():
            json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(json_path): continue
            station_gdf = gpd.read_file(json_path, crs="epsg:4326")
            if station_gdf.empty or station_gdf.geometry.iloc[0] is None or station_gdf.geometry.iloc[0].is_empty:
                continue

            all_members_data = []
            for i in range(18):
                res = self.process_ensemble_member(station_gdf, forecast_dir, f'precip_EN{str(i).zfill(2)}.nc', date_input)
                if res: all_members_data.append(res)
            
            if not all_members_data: continue
            obs_df = self.get_observed_rainfall(station_gdf, date_input)
            obs_dict = dict(zip(obs_df['Date'], obs_df['Rainfall']))
            response = self.calculate_exceedance_probability([{**obs_dict, **m} for m in all_members_data], STATION_THRESHOLDS[basin_id], date_input)
            
            if response:
                self.save_to_database(response, date_input, basin_id)
                success = True
                for d_key, probs in response.items():
                    if d_key in ["Hours", "Threshold"]: continue
                    for idx_str, val in probs.items():
                        if val > peak_prob: peak_prob, peak_info = val, f"{station_name.upper()} on {d_key}"
                        alert = {'basin': station_name.upper(), 'date': d_key, 'hour': response['Hours'][idx_str], 'prob': val}
                        if val >= 75: risk_categories["CRITICAL (>=75%)"].append(alert)
                        elif val >= 50: risk_categories["WARNING (50-74%)"].append(alert)
                        elif val >= 10: risk_categories["WATCH (10-49%)"].append(alert)
                self.stdout.write(f"  ✅ Processed {station_name}")

        self.stdout.write("\n" + "═"*60)
        any_risk = False
        for label, items in risk_categories.items():
            if items:
                any_risk = True
                self.stdout.write(self.style.WARNING(f"\n{label}:"))
                for i in sorted(items, key=lambda x: (x['prob'], x['date']), reverse=True)[:5]:
                    self.stdout.write(f"  - {i['basin']}: {i['prob']}% ({i['hour']}h) on {i['date']}")
        if not any_risk:
            self.stdout.write(self.style.SUCCESS(f"\n✅ No Alerts. Global Peak Prob: {peak_prob}% ({peak_info})"))
        self.stdout.write("\n" + "═"*60 + "\n")
        return success