import os
import math
from datetime import datetime, timedelta

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from django.conf import settings
from django.core.management import BaseCommand
from rioxarray.exceptions import NoDataInBounds

# Ensure this model exists in your models.py
from data_load.models import UKMetMonsoonProbabilisticFlashFloodForecast

# --- Static Data ---
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
    help = 'Generate Probabilistic Basin Wise Flash Flood Forecasts using local UKMET Ensemble data.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYY-MM-DD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        if not date_input:
            date_input = datetime.now().strftime('%Y-%m-%d')
        
        # Format normalization
        if "-" not in date_input:
            try: date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
            except: pass

        if not self.run_forecast_for_date(date_input):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Today's data missing. Trying yesterday: {yesterday}"))
            self.run_forecast_for_date(yesterday)

    def process_ensemble_member(self, station_gdf, forecast_dir, filename):
        filepath = os.path.join(forecast_dir, filename)
        if not os.path.exists(filepath): return None
        
        try:
            with xr.open_dataset(filepath) as ds:
                # 1. Coordinate Setup
                x_dim = "longitude" if "longitude" in ds.coords else "lon"
                y_dim = "latitude" if "latitude" in ds.coords else "lat"
                
                ds.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim, inplace=True)
                ds.rio.write_crs("epsg:4326", inplace=True)
                # Sort coordinates to prevent NoDataInBounds errors
                ds = ds.sortby([y_dim, x_dim])

                # 2. Clipping (using all_touched for small basins like Muslimpur)
                clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True, all_touched=True)
                
                # 3. Variable Detection (Prioritize 'tp' for new files)
                target_var = next((v for v in ['tp', 'thickness_of_rainfall_amount', 'precipitation'] if v in clipped), None)
                if not target_var: return None

                # 4. Compute Daily Rainfall
                # Since inspection shows 24h intervals of "Daily total", each step is one day.
                daily_rainfall = {}
                weights = np.cos(np.deg2rad(clipped[y_dim]))
                
                for ts in list(clipped.indexes['time']):
                    step_data = clipped.sel(time=ts)
                    mean_val = step_data[target_var].weighted(weights).mean(dim=[x_dim, y_dim]).item()
                    
                    # New files are in mm, old were in m. Let's check attributes if possible, 
                    # but per your inspection, new 'tp' is mm. 
                    val_mm = mean_val if ds[target_var].attrs.get('units') == 'mm' else mean_val * 1000
                    
                    daily_rainfall[ts.strftime('%Y-%m-%d')] = round(val_mm if not math.isnan(val_mm) else 0.0, 4)
                
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
                        ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                        ds = ds.sortby(['lat', 'lon'])
                        clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True, all_touched=True)
                        weights = np.cos(np.deg2rad(clipped.lat))
                        daily_precip[obs_date.strftime('%Y-%m-%d')] = clipped['precipitation'].weighted(weights).mean().item()
                except: pass
        return pd.DataFrame(list(daily_precip.items()), columns=['Date', 'Rainfall'])

    def calculate_exceedance_probability(self, all_member_rainfall, thresholds, given_date):
        if not all_member_rainfall: return {}
        num_members = len(all_member_rainfall)
        threshold_df = pd.DataFrame.from_dict(thresholds, orient='index', columns=['Hours', 'Threshold'])
        
        # Combine member data into a DataFrame where rows are dates, columns are members
        combined_df = pd.DataFrame(all_member_rainfall).T.fillna(0)
        
        forecast_dates = [d for d in pd.to_datetime(combined_df.index) if d >= pd.to_datetime(given_date)]
        probability_results = {}
        
        for p_date in sorted(forecast_dates):
            daily_probs = {}
            for idx, (hour, threshold) in threshold_df.iterrows():
                days_to_sum = int(hour / 24)
                # Look BACKWARD from the forecast date to include historical context if needed
                sum_range = [p_date - timedelta(days=i) for i in range(days_to_sum)]
                sum_range_strs = [d.strftime('%Y-%m-%d') for d in sum_range]
                
                # Check which dates exist in our combined dataframe
                available_cols = [d for d in sum_range_strs if d in combined_df.index]
                if not available_cols: continue
                
                # Sum across the days for each member
                member_sums = combined_df.loc[available_cols].sum(axis=0)
                exceed_count = (member_sums > threshold).sum()
                daily_probs[idx] = round((exceed_count / num_members) * 100, 2)
            
            if daily_probs:
                probability_results[p_date.strftime('%Y-%m-%d')] = daily_probs
                
        return {"Hours": threshold_df['Hours'].to_dict(), "Thresholds": threshold_df['Threshold'].to_dict(), **probability_results}

    def save_to_database(self, data_dict, prediction_date, basin_id):
        if not data_dict or "Hours" not in data_dict: return
        rows = []
        for date_key, values in data_dict.items():
            if date_key in ["Hours", "Thresholds"]: continue
            for index, value in values.items():
                rows.append(UKMetMonsoonProbabilisticFlashFloodForecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=data_dict["Hours"][index],
                    thresholds=data_dict["Thresholds"][index],
                    value=value if not math.isnan(value) else 0.0
                ))
        if rows:
            UKMetMonsoonProbabilisticFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            UKMetMonsoonProbabilisticFlashFloodForecast.objects.bulk_create(rows)

    def run_forecast_for_date(self, date_input):
        self.stdout.write(self.style.SUCCESS(f'--- Starting Probabilistic Generation: {date_input} ---'))
        success = False
        
        date_nodash = date_input.replace('-', '')
        forecast_dir = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_ens_data/ukmet_ens_{date_nodash}/"

        for basin_id, station_name in STATION_DICT.items():
            json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(json_path): continue
            station_gdf = gpd.read_file(json_path, crs="epsg:4326")

            # Process all 18 members
            all_members = []
            for i in range(18):
                res = self.process_ensemble_member(station_gdf, forecast_dir, f'precip_EN{i:02d}.nc')
                if res: all_members.append(res)

            if not all_members: continue

            # Get Observed and merge (simplified for exceedance calc)
            # Probability calc needs the ensemble members, but cumulative logic includes history.
            # We merge observed into EACH member's history.
            obs_df = self.get_observed_rainfall(station_gdf, date_input)
            obs_dict = dict(zip(obs_df['Date'], obs_df['Rainfall']))
            
            enriched_members = []
            for member_rain in all_members:
                enriched_members.append({**obs_dict, **member_rain})

            response = self.calculate_exceedance_probability(enriched_members, STATION_THRESHOLDS[basin_id], date_input)
            if response:
                self.save_to_database(response, date_input, basin_id)
                success = True
                self.stdout.write(f"  Processed {station_name}")

        return success