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
from data_load.models import Basin_Wise_Flash_Flood_Forecast


# Suppress the buffer warning
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")

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
    12:{24: 30.52, 48: 40.468, 72: 47.73, 120: 58.75, 168: 67.37, 240: 77.89}
}

class Command(BaseCommand):
    help = 'Processes ECMWF HRES (cp variable) for Pre-Monsoon Flash Flood Forecast'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        date_input = options['date'] or datetime.today().strftime('%Y-%m-%d')
        dt_obj = datetime.strptime(date_input, "%Y-%m-%d") if "-" in date_input else datetime.strptime(date_input, "%Y%m%d")
        standard_date = dt_obj.strftime('%Y-%m-%d')

        self.stdout.write(self.style.SUCCESS(f"🚀 Starting ECMWF Pre-Monsoon: {standard_date}"))
        high_risk_summary = []

        for basin_id, station_name in STATION_DICT.items():
            station_json = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{station_name}.json')
            if not os.path.exists(station_json): continue
            stationGDF = gpd.read_file(station_json, crs="epsg:4326")

            # 1. Compute Observed
            daily_obs = {}
            for i in range(1, 11):
                obs_dt = dt_obj - timedelta(days=i)
                obs_file = f"{obs_dt.year}{obs_dt.timetuple().tm_yday:03d}.nc"
                daily_obs = self.compute_observed_mean(obs_file, stationGDF, daily_obs)

            # 2. Compute Forecast (Modified for 'cp' and 'Mg/m^2')
            daily_forecast = self.compute_forecast_mean(stationGDF, dt_obj)
            
            if not daily_forecast: continue

            # 3. Merge and Save
            df_obs = pd.DataFrame({'Date': list(daily_obs.keys()), 'Rainfall': list(daily_obs.values())})
            df_fc = pd.DataFrame({'Date': list(daily_forecast.keys()), 'Rainfall': list(daily_forecast.values())})
            all_records = pd.concat([df_obs, df_fc]).sort_values('Date').drop_duplicates('Date').reset_index(drop=True)

            risk_found = self.process_and_save(all_records, standard_date, basin_id, station_name)
            if risk_found: high_risk_summary.extend(risk_found)

        self.print_summary(standard_date, high_risk_summary)

    def compute_forecast_mean(self, stationGDF, dt_obj):
        # Path logic: try ddmmyyyy.nc
        forecast_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/"
        file_name = dt_obj.strftime('%d%m%Y') + ".nc"
        file_path = os.path.join(forecast_dir, file_name)
        
        if not os.path.exists(file_path): return {}

        try:
            with xr.open_dataset(file_path) as ds:
                # Coordinate Renaming for rioxarray
                da = ds.rename({'longitude': 'x', 'latitude': 'y'})
                da.rio.set_spatial_dims(x_dim='x', y_dim='y', inplace=True)
                da.rio.write_crs("epsg:4326", inplace=True)
                da = da.sortby(['y', 'x'])

                # Variable extraction based on inspection
                target_var = 'cp' 
                
                # Clip with 0.01 buffer for small basins
                clipped = da[target_var].rio.clip(stationGDF.geometry.buffer(0.01), stationGDF.crs, drop=True, all_touched=True)
                
                # Calculate weighted spatial mean
                weights = np.cos(np.deg2rad(clipped.y))
                mean_series = clipped.weighted(weights).mean(dim=["x", "y"]).to_series()
                
                # Unit Conversion: Mg/m^2 to mm (multiplier 1000)
                mean_series = mean_series * 1000
                
                # De-accumulation: Since behavior is Cumulative
                # The file starts at 00:00 with 0.0. 
                # resample('1D').max() gets the total accumulation at the end of each day.
                daily_accumulation = mean_series.resample('1D').max()
                daily_incremental = daily_accumulation.diff().fillna(daily_accumulation.iloc[0])
                daily_incremental[daily_incremental < 0] = 0

                return {d.strftime('%Y-%m-%d'): round(v, 4) for d, v in daily_incremental.items()}
        except Exception as e:
            print(f"      ⚠️ Forecast Error: {e}")
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

    def process_and_save(self, all_records, prediction_date, basin_id, station_name):
        dt_pred = datetime.strptime(prediction_date, '%Y-%m-%d')
        dict_rainfall = dict(zip(all_records['Date'], all_records['Rainfall']))
        hour_list = [24, 48, 72, 120, 168, 240]
        
        # Determine available forecast range
        last_date = datetime.strptime(all_records['Date'].iloc[-1], '%Y-%m-%d')
        forecast_days = (last_date - dt_pred).days
        
        rows, basin_risks = [], []

        for day_offset in range(forecast_days + 1):
            current_dt = dt_pred + timedelta(days=day_offset)
            for hr in hour_list:
                days_to_sum = int(hr/24)
                cum_sum = sum(dict_rainfall.get((current_dt - timedelta(days=d)).strftime('%Y-%m-%d'), 0.0) for d in range(days_to_sum))
                threshold = STATION_THRESHOLDS[basin_id][hr]
                
                rows.append(Basin_Wise_Flash_Flood_Forecast(
                    prediction_date=prediction_date, basin_id=basin_id,
                    date=current_dt.date(), hours=hr, thresholds=threshold, value=round(cum_sum, 2)
                ))

                if cum_sum >= threshold and day_offset >= 0:
                    basin_risks.append({'basin': station_name.upper(), 'date': current_dt.strftime('%Y-%m-%d'), 'hour': hr, 'val': round(cum_sum, 2), 'thresh': threshold})
        
        if rows:
            Basin_Wise_Flash_Flood_Forecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
            Basin_Wise_Flash_Flood_Forecast.objects.bulk_create(rows)
            self.stdout.write(f"  ✅ Processed {station_name}")
        return basin_risks

    def print_summary(self, fdate, risk_list):
        self.stdout.write("\n" + "═"*60)
        self.stdout.write(self.style.SUCCESS(f"🏁 ECMWF PROCESSING COMPLETE: {fdate}"))
        if risk_list:
            self.stdout.write(self.style.WARNING("⚠️  THRESHOLDS EXCEEDED:"))
            risk_list.sort(key=lambda x: x['date'])
            for r in risk_list[:10]:
                self.stdout.write(f"  - {r['basin']}: {r['val']}mm (>{r['thresh']}mm) in {r['hour']}h on {r['date']}")
        else:
            self.stdout.write(self.style.SUCCESS("✅ No thresholds exceeded."))
        self.stdout.write("═"*60 + "\n")