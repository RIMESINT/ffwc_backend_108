import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Step 1: Compute Anomaly NetCDF from IMD-GFS (Accumulated tp) with fallback'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        fdate_input = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        date_obj = dt.strptime(fdate_input, '%Y%m%d')
        
        # 1. Fallback Logic
        IMD_NC_FILE = None
        actual_fdate = fdate_input
        for i in range(2):
            check_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')
            temp_path = os.path.join(settings.BASE_DIR, 'forecast', 'imd_gfs', f'{check_date}.nc')
            if os.path.exists(temp_path):
                IMD_NC_FILE = temp_path
                actual_fdate = check_date
                break
        
        if not IMD_NC_FILE:
            self.stdout.write(self.style.WARNING(f"⚠️ No IMD-GFS file found for {fdate_input} or yesterday."))
            return

        # 2. Paths
        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate_input, 'IMD-GFS')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        CLIMO_PATH = os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc')

        # 3. Load Datasets
        ds_climo = xr.open_dataset(CLIMO_PATH)
        ds_imd = xr.open_dataset(IMD_NC_FILE)
        
        # tp is kg/m2 which is already mm. No scaling needed.
        tp_acc = ds_imd['tp']
        
        # Crop Climatology to IMD box (72-98E, 20-32N)
        ds_climo_cropped = ds_climo.sel(
            lat=slice(ds_imd.lat.max().item() + 0.5, ds_imd.lat.min().item() - 0.5),
            lon=slice(ds_imd.lon.min().item() - 0.5, ds_imd.lon.max().item() + 0.5)
        ).load()

        all_times = pd.to_datetime(ds_imd.time.values)
        unique_days = np.unique(all_times.date)
        anomaly_cubes = []

        # 4. Calculation Loop
        for day in unique_days:
            # We look for the 24-hour difference (e.g., 03:00 today to 03:00 tomorrow)
            t_start = pd.Timestamp(day) + timedelta(hours=3)
            t_end = t_start + timedelta(days=1)
            
            if t_start in all_times and t_end in all_times:
                daily_rain = tp_acc.sel(time=t_end) - tp_acc.sel(time=t_start)
                
                # Regrid 0.125 Forecast to 0.1 Climatology
                daily_regridded = daily_rain.interp(
                    lat=ds_climo_cropped.lat, 
                    lon=ds_climo_cropped.lon,
                    method="linear"
                )
                
                climo_slice = ds_climo_cropped['precipitation'].sel(dayofyear=t_start.dayofyear)
                anomaly_cubes.append((daily_regridded - climo_slice).expand_dims(time=[t_start]))

        # 5. Save NetCDF
        if anomaly_cubes:
            full_nc_path = os.path.join(OUTPUT_ROOT, f'imd_gfs_rainfall_anomaly_{fdate_input}.nc')
            xr.concat(anomaly_cubes, dim='time').to_dataset(name='rainfall_anomaly').to_netcdf(full_nc_path)
            self.stdout.write(self.style.SUCCESS(f"✅ IMD-GFS Anomaly Created: {full_nc_path}"))