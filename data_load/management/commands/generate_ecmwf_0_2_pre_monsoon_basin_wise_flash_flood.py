import os
import math
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.conf import settings
from data_load.models import Basin_Wise_Flash_Flood_Forecast

# --- Configuration ---
STATION_DICT = { 
    1:'khaliajhuri', 2:'gowainghat', 3:'dharmapasha', 4:'userbasin',
    5:'laurergarh', 6:'muslimpur', 7:'debidwar', 8:'ballah',
    9:'habiganj', 10:'parshuram', 11:'cumilla', 12:'nakuagaon'
}

STATION_THRESHOLDS = {
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
    help = 'Processes ECMWF HRES (Cumulative) for Pre-Monsoon Flash Flood Forecast'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        date_input = options['date'] or datetime.today().strftime('%Y-%m-%d')
        
        try:
            dt_obj = datetime.strptime(date_input, "%Y-%m-%d") if "-" in date_input else datetime.strptime(date_input, "%Y%m%d")
            standard_date = dt_obj.strftime('%Y-%m-%d')
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid date format: {date_input}"))
            return

        self.stdout.write(self.style.SUCCESS(f"🚀 Starting ECMWF Pre-Monsoon Calculation: {standard_date}"))
        
        high_risk_summary = []

        for basin_id, station_name in STATION_DICT.items():
            # 1. Compute Observed Rainfall (Weighted Mean)
            daily_obs = {}
            for i in range(1, 11):
                obs_dt = dt_obj - timedelta(days=i)
                obs_file = f"{obs_dt.year}{obs_dt.timetuple().tm_yday:03d}.nc"
                daily_obs = self.compute_observed_mean(obs_file, station_name, daily_obs)

            # 2. Compute Forecast Rainfall (De-accumulation)
            daily_forecast = self.compute_forecast_mean(station_name, dt_obj)
            
            if not daily_forecast:
                self.stdout.write(self.style.WARNING(f"  ⚠️ No forecast data for {station_name}. Skipping."))
                continue

            # 3. Merge Datasets
            df_obs = pd.DataFrame({'Date': list(daily_obs.keys()), 'Rainfall': list(daily_obs.values())})
            df_fc = pd.DataFrame({'Date': list(daily_forecast.keys()), 'Rainfall': list(daily_forecast.values())})
            all_records = pd.concat([df_obs, df_fc]).sort_values('Date').drop_duplicates('Date').reset_index(drop=True)

            # 4. Process and Save to DB
            risk_found = self.process_and_save(all_records, standard_date, basin_id, station_name)
            if risk_found:
                high_risk_summary.extend(risk_found)

        # 5. Final Summary Log
        self.print_summary(standard_date, high_risk_summary)

    def compute_forecast_mean(self, station_name, dt_obj):
        forecast_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/"
        station_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
        
        # Try today's file, then yesterday's
        file_path = ""
        for day_offset in [0, 1]:
            name = (dt_obj - timedelta(days=day_offset)).strftime('%d%m%Y')
            p = os.path.join(forecast_dir, f"{name}.nc")
            if os.path.exists(p):
                file_path = p
                break
        
        if not file_path: return {}

        with xr.open_dataset(file_path) as ds:
            # Detect variable (tp is preferred, cp is fallback)
            var_name = next((v for v in ['tp', 'cp', 'precip'] if v in ds.data_vars), None)
            if not var_name: return {}

            # Sort and set Spatial dims
            ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
            ds.rio.write_crs("epsg:4326", inplace=True)
            ds = ds.sortby(['latitude', 'longitude'])

            stationGDF = gpd.read_file(station_json, crs="epsg:4326")
            clipped = ds.rio.clip(stationGDF.geometry, stationGDF.crs, drop=True, all_touched=True)
            
            weights = np.cos(np.deg2rad(clipped.latitude))
            mean_ds = clipped.weighted(weights).mean(dim=["longitude", "latitude"])
            
            # Subtraction logic for cumulative data
            raw_series = mean_ds[var_name].to_series() * 1000 # Mg/m2 to mm
            incremental = raw_series.diff().fillna(raw_series.iloc[0])
            incremental[incremental < 0] = 0 # Clean numerical noise
            
            # Resample to Daily Totals
            daily_totals = incremental.resample('1D').sum()
            return {d.strftime('%Y-%m-%d'): round(v, 4) for d, v in daily_totals.items()}

    def compute_observed_mean(self, fileName, stationName, dailyPrecipitationDict):
        obs_path = os.path.join(settings.BASE_DIR, 'observed', fileName)
        if not os.path.exists(obs_path): return dailyPrecipitationDict

        try:
            with xr.open_dataset(obs_path) as ds:
                station_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{stationName}.json')
                ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True).rio.write_crs("epsg:4326", inplace=True)
                ds = ds.sortby(['lat', 'lon'])
                
                clipped = ds.rio.clip(gpd.read_file(station_json).geometry, "epsg:4326", drop=True, all_touched=True)
                weights = np.cos(np.deg2rad(clipped.lat))
                mean_val = clipped['precipitation'].weighted(weights).mean().item()
                date_key = clipped.indexes['time'][0].strftime('%Y-%m-%d')
                dailyPrecipitationDict[date_key] = mean_val
        except: pass
        return dailyPrecipitationDict

    def process_and_save(self, all_records, prediction_date, basin_id, station_name):
        dt_pred = datetime.strptime(prediction_date, '%Y-%m-%d')
        dict_rainfall = dict(zip(all_records['Date'], all_records['Rainfall']))
        hour_list = [24, 48, 72, 120, 168, 240]
        
        last_date = datetime.strptime(all_records['Date'].iloc[-1], '%Y-%m-%d')
        forecast_days = (last_date - dt_pred).days
        
        rows = []
        basin_risks = []

        for day_offset in range(forecast_days + 1):
            current_dt = dt_pred + timedelta(days=day_offset)
            for hr in hour_list:
                # Rolling backward sum
                cum_sum = sum(dict_rainfall.get((current_dt - timedelta(days=d)).strftime('%Y-%m-%d'), 0.0) for d in range(int(hr/24)))
                threshold = STATION_THRESHOLDS[basin_id][hr]
                
                rows.append(Basin_Wise_Flash_Flood_Forecast(
                    prediction_date=prediction_date,
                    basin_id=basin_id,
                    date=current_dt.date(),
                    hours=hr,
                    thresholds=threshold,
                    value=round(cum_sum, 2)
                ))

                # Logic for Summary Log: If forecast exceeds threshold
                if cum_sum >= threshold and day_offset > 0:
                    basin_risks.append({
                        'basin': station_name.upper(),
                        'date': current_dt.strftime('%Y-%m-%d'),
                        'hour': hr,
                        'val': round(cum_sum, 2),
                        'thresh': threshold
                    })
        
        if rows:
            Basin_Wise_Flash_Flood_Forecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            Basin_Wise_Flash_Flood_Forecast.objects.bulk_create(rows)
            self.stdout.write(f"  ✅ Saved Basin {basin_id}")
        
        return basin_risks

    def print_summary(self, fdate, risk_list):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"🏁 ECMWF PROCESSING COMPLETE: {fdate}"))
        if risk_list:
            self.stdout.write(self.style.WARNING("⚠️  THRESHOLDS EXCEEDED IN FORECAST:"))
            # Sort by date
            risk_list.sort(key=lambda x: x['date'])
            for r in risk_list:
                self.stdout.write(f"  - {r['basin']}: {r['val']}mm exceeds {r['thresh']}mm ({r['hour']}h window) on {r['date']}")
        else:
            self.stdout.write(self.style.SUCCESS("✅ No thresholds exceeded in current forecast."))
        self.stdout.write("="*60 + "\n")