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

# Import the correct Pre-Monsoon Probabilistic model
from data_load.models import UKMetPreMonsoonProbabilisticFlashFloodForecast

# --- Pre-Monsoon Station Configurations ---
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
    help = 'Generates UKMet Probabilistic PRE-MONSOON Flash Flood Forecasts.'

    def add_arguments(self, parser):
        parser.add_argument('date', nargs='?', type=str, help='Forecast date (YYYY-MM-DD or YYYYMMDD)')

    def handle(self, *args, **kwargs):
        date_input = kwargs.get('date')
        if not date_input:
            date_input = datetime.now().strftime('%Y-%m-%d')
        
        # Standardize date format to YYYY-MM-DD
        try:
            if "-" not in date_input:
                date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
        except Exception:
            pass

        if not self.run_forecast_for_date(date_input):
            yesterday = (datetime.strptime(date_input, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            self.stdout.write(self.style.WARNING(f"Data missing for {date_input}. Trying yesterday: {yesterday}..."))
            self.run_forecast_for_date(yesterday)

    def process_ensemble_member(self, station_gdf, forecast_dir, filename):
        filepath = os.path.join(forecast_dir, filename)
        if not os.path.exists(filepath):
            return None
        
        try:
            with xr.open_dataset(filepath) as ds:
                # 1. Coordinate Setup
                x_dim = "longitude" if "longitude" in ds.coords else "lon"
                y_dim = "latitude" if "latitude" in ds.coords else "lat"
                
                ds.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim, inplace=True)
                ds.rio.write_crs("epsg:4326", inplace=True)
                # Sort coordinates to prevent NoDataInBounds errors
                ds = ds.sortby([y_dim, x_dim])

                # 2. Clipping with small basin support (all_touched)
                clipped = ds.rio.clip(station_gdf.geometry, station_gdf.crs, drop=True, all_touched=True)
                
                # 3. Variable Detection (UKMET ensemble uses 'tp')
                target_var = next((v for v in ['tp', 'precipitation'] if v in clipped), None)
                if not target_var:
                    return None

                # 4. Compute Daily Rainfall
                daily_rainfall = {}
                weights = np.cos(np.deg2rad(clipped[y_dim]))
                
                for ts in list(clipped.indexes['time']):
                    step_data = clipped.sel(time=ts)
                    mean_val = step_data[target_var].weighted(weights).mean(dim=[x_dim, y_dim]).item()
                    
                    # Units check: inspection showed 'tp' is mm
                    val_mm = mean_val if ds[target_var].attrs.get('units') == 'mm' else mean_val * 1000
                    daily_rainfall[ts.strftime('%Y-%m-%d')] = round(val_mm if not math.isnan(val_mm) else 0.0, 4)
                
                return daily_rainfall
        except Exception:
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
                except Exception:
                    pass
        return daily_precip

    def calculate_exceedance_probability(self, all_enriched_members, thresholds, given_date):
        if not all_enriched_members:
            return {}
        num_members = len(all_enriched_members)
        threshold_df = pd.DataFrame.from_dict(thresholds, orient='index', columns=['Hours', 'Threshold'])
        
        # Combine member data into a DataFrame where index are dates and columns are members
        combined_df = pd.DataFrame(all_enriched_members).T.fillna(0)
        
        forecast_dates = [d for d in pd.to_datetime(combined_df.index) if d >= pd.to_datetime(given_date)]
        
        probability_results = {}
        for p_date in sorted(forecast_dates):
            daily_probs = {}
            for idx, (hour, threshold) in threshold_df.iterrows():
                days_to_sum = int(hour / 24)
                # Backward-looking cumulative sum (past X days)
                sum_range = [p_date - timedelta(days=i) for i in range(days_to_sum)]
                sum_range_strs = [d.strftime('%Y-%m-%d') for d in sum_range]
                
                available_dates = [d for d in sum_range_strs if d in combined_df.index]
                if not available_dates:
                    continue
                
                # Sum across the days for each ensemble member
                member_sums = combined_df.loc[available_dates].sum(axis=0)
                exceed_count = (member_sums > threshold).sum()
                daily_probs[idx] = round((exceed_count / num_members) * 100, 2)
            
            if daily_probs:
                probability_results[p_date.strftime('%Y-%m-%d')] = daily_probs
                
        return probability_results

    def save_to_database(self, results, prediction_date, basin_id):
        rows = []
        # Mapping indices to actual values from thresholds
        hours_map = {idx: val[0] for idx, val in STATION_THRESHOLDS[basin_id].items()}
        thresh_map = {idx: val[1] for idx, val in STATION_THRESHOLDS[basin_id].items()}

        for date_key, values in results.items():
            for idx, prob_val in values.items():
                rows.append(UKMetPreMonsoonProbabilisticFlashFloodForecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                    hours=hours_map[idx],
                    thresholds=thresh_map[idx],
                    value=prob_val
                ))
        
        if rows:
            # Delete existing records for this specific prediction date and basin
            UKMetPreMonsoonProbabilisticFlashFloodForecast.objects.filter(
                prediction_date=prediction_date, 
                basin_id=basin_id
            ).delete()
            
            # Use bulk_create for performance
            UKMetPreMonsoonProbabilisticFlashFloodForecast.objects.bulk_create(rows)
            self.stdout.write(self.style.SUCCESS(f"  Saved Basin {basin_id}"))

    def run_forecast_for_date(self, date_input):
        self.stdout.write(self.style.SUCCESS(f'--- UKMET Pre-Monsoon Probabilistic Processing: {date_input} ---'))
        success = False
        
        date_nodash = date_input.replace('-', '')
        forecast_dir = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_ens_data/ukmet_ens_{date_nodash}/"

        for basin_id, station_name in STATION_DICT.items():
            json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(json_path):
                continue
            station_gdf = gpd.read_file(json_path, crs="epsg:4326")

            # 1. Process all 18 Ensemble Members
            member_forecasts = []
            for i in range(18):
                res = self.process_ensemble_member(station_gdf, forecast_dir, f'precip_EN{i:02d}.nc')
                if res:
                    member_forecasts.append(res)

            if not member_forecasts:
                continue

            # 2. Get Observed Context (last 10 days)
            obs_dict = self.get_observed_rainfall(station_gdf, date_input)
            
            # 3. Enrich each member with historical data for the cumulative (backward-looking) calculation
            enriched_members = [{**obs_dict, **m} for m in member_forecasts]

            # 4. Calculate Probabilities
            response = self.calculate_exceedance_probability(enriched_members, STATION_THRESHOLDS[basin_id], date_input)
            
            if response:
                self.save_to_database(response, date_input, basin_id)
                success = True

        return success