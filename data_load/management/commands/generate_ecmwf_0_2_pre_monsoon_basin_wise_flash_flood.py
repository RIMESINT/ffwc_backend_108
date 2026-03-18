import os
import math
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import rioxarray
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.conf import settings
from data_load.models import Basin_Wise_Flash_Flood_Forecast

# --- Pre-Monsoon Station Configurations ---
stationDict = { 
    1:'khaliajhuri', 2:'gowainghat', 3:'dharmapasha', 4:'userbasin',
    5:'laurergarh', 6:'muslimpur', 7:'debidwar', 8:'ballah',
    9:'habiganj', 10:'parshuram', 11:'cumilla', 12:'nakuagaon'
}

stationThresholds = {
    1:{24: 51.45, 48: 77.5, 72: 98.3, 120: 133, 168: 162, 240: 200},
    2:{24: 25, 48: 41.5, 72: 56.5, 120: 83, 168: 107.5, 240: 141},
    3:{24: 24.5, 48: 41.5, 72: 56.5, 120: 83, 168: 107.5, 240: 141},
    4:{24: 25, 48: 40.5, 72: 53.5, 120: 76, 168: 96, 240: 123},
    5:{24: 34, 48: 46.3, 72: 55.4, 120: 69.37, 168: 80.5, 240: 94},
    6:{24: 33.50, 48: 51.84, 72: 66.93, 120: 92.34, 168: 114.14, 240: 142.90},
    7:{24: 54, 48: 87, 72: 115, 120: 164, 168: 207, 240: 264},
    8:{24: 15, 48: 26, 72: 35, 120: 52, 168: 68, 240: 90},
    9:{24: 14, 48: 22, 72: 30, 120: 44, 168: 56, 240: 73},
    10:{24: 17, 48: 29, 72: 39, 120: 58, 168: 75, 240: 99},
    11:{24: 32, 48: 49, 72: 63, 120: 87, 168: 108, 240: 135},
    12: {24: 30.52, 48: 40.468, 72: 47.73, 120: 58.75, 168: 67.37, 240: 77.89}
}

class Command(BaseCommand):
    help = 'Processes ECMWF files for Pre-Monsoon Flash Flood Forecast'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD or YYYYMMDD)')

    def handle(self, *args, **options):
        date_input = options['date']
        if not date_input:
            date_input = datetime.today().strftime('%Y-%m-%d')
        
        # 1. Flexible Date Parsing
        try:
            if "-" in date_input:
                dt_obj = datetime.strptime(date_input, "%Y-%m-%d")
            else:
                dt_obj = datetime.strptime(date_input, "%Y%m%d")
            standard_date = dt_obj.strftime('%Y-%m-%d')
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid date format: {date_input}"))
            return

        self.stdout.write(f"Starting Pre-Monsoon Calculation for {standard_date}...")

        # 2. Iterate through Pre-Monsoon Basins
        for basin_id, station_name in stationDict.items():
            self.stdout.write(f"Processing Basin {basin_id}: {station_name}")
            
            # Step A: Compute Observed Rainfall (last 10 days)
            daily_obs = {}
            day_of_year = dt_obj.timetuple().tm_yday
            current_year = dt_obj.year

            for i in range(1, 11):
                obs_day = str(day_of_year - i).zfill(3)
                obs_file = f"{current_year}{obs_day}.nc"
                daily_obs = self.compute_observed_mean(obs_file, station_name, daily_obs)

            # Step B: Compute Forecast Rainfall
            daily_forecast = self.compute_forecast_mean(station_name, standard_date)
            
            if not daily_forecast:
                self.stdout.write(self.style.WARNING(f"No forecast data for {station_name}. Skipping."))
                continue

            # Step C: Combine datasets
            df_obs = pd.DataFrame({'Date': list(daily_obs.keys()), 'Rainfall': list(daily_obs.values())})
            df_fc = pd.DataFrame({'Date': list(daily_forecast.keys()), 'Rainfall': list(daily_forecast.values())})
            all_records = pd.concat([df_obs, df_fc]).sort_values('Date').reset_index(drop=True)

            # Step D: Save to Basin_Wise_Flash_Flood_Forecast model
            self.save_to_db(all_records, standard_date, basin_id)

    def compute_forecast_mean(self, station_name, given_date):
        forecast_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/"
        assets_dir = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations')
        
        station_json = os.path.join(assets_dir, f'{station_name}.json')
        if not os.path.exists(station_json): return {}
        stationGDF = gpd.read_file(station_json, crs="epsg:4326")

        dt_obj = datetime.strptime(given_date, '%Y-%m-%d')
        filenames = [dt_obj.strftime('%d%m%Y'), (dt_obj - timedelta(days=1)).strftime('%d%m%Y')]
        
        file_path = ""
        for name in filenames:
            p = os.path.join(forecast_dir, f"{name}.nc")
            if os.path.isfile(p):
                file_path = p
                break
        
        if not file_path: return {}

        ds = xr.open_dataset(file_path)
        for var in ds.data_vars:
            ds[var] = ds[var].where(ds[var] < 1e30, 0.0)

        # Fix: Sort Coordinates and Set CRS
        ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
        ds.rio.write_crs("epsg:4326", inplace=True)
        ds = ds.sortby(['latitude', 'longitude'])

        try:
            # Fix: all_touched=True for small basins
            clipped = ds.rio.clip(stationGDF.geometry, stationGDF.crs, drop=True, all_touched=True)
        except Exception:
            return {}
        
        cumulative_precip = {}
        for ts in list(clipped.indexes['time']):
            data_step = clipped.sel(time=ts)
            mean_val = data_step.mean(("longitude", "latitude"))
            val = mean_val['cp'].values.tolist()
            val = val if isinstance(val, (float, int)) else val[0]
            cumulative_precip[ts.strftime('%Y-%m-%d %H:%M:%S')] = (val if not math.isnan(val) else 0.0) * 1000

        # Convert cumulative ECMWF data to daily incremental rainfall
        daily_vals = {}
        prev = 0.0
        for i, ts_str in enumerate(sorted(cumulative_precip.keys())):
            curr = cumulative_precip[ts_str]
            date_key = ts_str[:10]
            interval = curr if i == 0 else curr - prev
            if interval < 0: interval = 0.0
            daily_vals[date_key] = daily_vals.get(date_key, 0.0) + interval
            prev = curr
        return {d: round(v, 4) for d, v in daily_vals.items()}

    def compute_observed_mean(self, fileName, stationName, dailyPrecipitationDict):
        try:
            station_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{stationName}.json')
            file_path = os.path.join(settings.BASE_DIR, 'observed', fileName)
            if not os.path.exists(file_path): return dailyPrecipitationDict

            ds = xr.open_dataset(file_path)
            ds['precipitation'] = ds['precipitation'].where(ds['precipitation'] < 1e30, np.nan)
            ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
            ds.rio.write_crs("epsg:4326", inplace=True)
            ds = ds.sortby(['lat', 'lon'])
            
            clipped = ds.rio.clip(gpd.read_file(station_json).geometry, "epsg:4326", drop=True, all_touched=True)
            
            weights = np.cos(np.deg2rad(clipped.lat))
            mean_val = clipped.weighted(weights).mean(("lon", "lat"))['precipitation'].values.tolist()[0]
            date_key = clipped.indexes['time'][0].strftime('%Y-%m-%d')
            dailyPrecipitationDict[date_key] = mean_val
        except: pass
        return dailyPrecipitationDict

    def save_to_db(self, all_records, prediction_date, basin_id):
        dt_pred = datetime.strptime(prediction_date, '%Y-%m-%d')
        dict_rainfall = dict(zip(all_records['Date'], all_records['Rainfall']))
        hour_list = [24, 48, 72, 120, 168, 240]
        
        last_date_str = all_records['Date'].iloc[-1]
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
        forecast_days = (last_date - dt_pred).days
        
        rows = []
        for day_offset in range(forecast_days + 1):
            current_dt = dt_pred + timedelta(days=day_offset)
            for hr in hour_list:
                cum_sum = 0.0
                for d_back in range(int(hr/24)):
                    look_date = (current_dt - timedelta(days=d_back)).strftime('%Y-%m-%d')
                    cum_sum += dict_rainfall.get(look_date, 0.0)
                
                rows.append(Basin_Wise_Flash_Flood_Forecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=current_dt.date(),
                    hours=hr,
                    thresholds=stationThresholds[basin_id][hr],
                    value=round(cum_sum, 2)
                ))
        
        if rows:
            # Delete existing records for this date/basin before bulk inserting
            Basin_Wise_Flash_Flood_Forecast.objects.filter(
                prediction_date=prediction_date, basin_id=basin_id
            ).delete()
            Basin_Wise_Flash_Flood_Forecast.objects.bulk_create(rows)
            self.stdout.write(self.style.SUCCESS(f"Saved Pre-Monsoon records for Basin {basin_id}"))