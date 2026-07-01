import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Step 1: Compute Anomaly NetCDF from ECMWF (DDMMYYYY file) using YYYYMMDD input'

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Date in format YYYYMMDD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        fdate_input = raw_date or dt.now().strftime('%Y%m%d')
        if "-" in fdate_input:
            fdate_input = fdate_input.replace('-', '')

        try:
            date_obj = dt.strptime(fdate_input, '%Y%m%d')
            filename_date = date_obj.strftime('%d%m%Y') 
        except ValueError:
            self.stdout.write(self.style.ERROR(f"Invalid date format: {fdate_input}. Use YYYYMMDD"))
            return

        # Paths
        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate_input, 'ECMWF')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        
        CLIMO_PATH = os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc')
        ECMWF_NC_FILE = os.path.join(settings.BASE_DIR, 'forecast', 'ecmwf_0_2', f'{filename_date}.nc')

        self.stdout.write(f"🔍 Searching for Forecast File: {ECMWF_NC_FILE}")

        if not os.path.exists(ECMWF_NC_FILE):
            self.stdout.write(self.style.ERROR(f"❌ File not found: {ECMWF_NC_FILE}"))
            return

        # Load and Prepare Data
        ds_climo = xr.open_dataset(CLIMO_PATH)
        ds_ec = xr.open_dataset(ECMWF_NC_FILE)
        
        ds_ec = ds_ec.rename({'latitude': 'lat', 'longitude': 'lon'})
        ec_acc = ds_ec['cp'] * 1000 
        
        ds_climo_cropped = ds_climo.sel(
            lat=slice(ds_ec.lat.max().item() + 0.5, ds_ec.lat.min().item() - 0.5),
            lon=slice(ds_ec.lon.min().item() - 0.5, ds_ec.lon.max().item() + 0.5)
        ).load()

        all_times = pd.to_datetime(ds_ec.time.values)
        unique_days = np.unique(all_times.date)
        anomaly_cubes = []

        for day in unique_days:
            t_start, t_end = pd.Timestamp(day), pd.Timestamp(day) + timedelta(days=1)
            
            if t_start in all_times and t_end in all_times:
                daily_rain = ec_acc.sel(time=t_end) - ec_acc.sel(time=t_start)
                
                daily_regridded = daily_rain.interp(
                    lat=ds_climo_cropped.lat, 
                    lon=ds_climo_cropped.lon,
                    method="linear"
                )
                
                climo_slice = ds_climo_cropped['precipitation'].sel(dayofyear=t_start.dayofyear)
                day_anomaly = daily_regridded - climo_slice
                
                anomaly_cubes.append(day_anomaly.expand_dims(time=[t_start]))

        if anomaly_cubes:
            full_nc_path = os.path.join(OUTPUT_ROOT, f'ecmwf_rainfall_anomaly_{fdate_input}.nc')
            xr.concat(anomaly_cubes, dim='time').to_dataset(name='rainfall_anomaly').to_netcdf(full_nc_path)
            self.stdout.write(self.style.SUCCESS(f"✅ Anomaly NetCDF Created: {full_nc_path}"))