import os
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Compute 7-Day Weekly Anomaly for IMD-GFS'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        fdate_input = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        date_obj = dt.strptime(fdate_input, '%Y%m%d')
        
        IMD_NC_FILE = None
        for i in range(2):
            check_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')
            temp_path = os.path.join(settings.BASE_DIR, 'forecast', 'imd_gfs', f'{check_date}.nc')
            if os.path.exists(temp_path):
                IMD_NC_FILE = temp_path
                break
        
        if not IMD_NC_FILE: return

        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate_input, 'IMD-GFS')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        ds_climo = xr.open_dataset(os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc'))
        ds_imd = xr.open_dataset(IMD_NC_FILE)
        
        # Calculate 7-day mean from bucket
        t0 = pd.to_datetime(ds_imd.time.values[0])
        t7 = t0 + timedelta(days=7)
        
        if t7 in ds_imd.time.values:
            imd_weekly_mean = (ds_imd['tp'].sel(time=t7) - ds_imd['tp'].sel(time=t0)) / 7
            imd_regridded = imd_weekly_mean.interp(lat=ds_climo.lat, lon=ds_climo.lon)

            doys = [(t0 + timedelta(days=i)).dayofyear for i in range(7)]
            climo_mean = ds_climo['precipitation'].sel(dayofyear=doys).mean(dim='dayofyear')

            weekly_anomaly = (imd_regridded - climo_mean).to_dataset(name='weekly_anomaly')
            weekly_anomaly.to_netcdf(os.path.join(OUTPUT_ROOT, f'imd_gfs_weekly_anomaly_{fdate_input}.nc'))
            self.stdout.write(self.style.SUCCESS(f"✅ IMD-GFS Weekly Anomaly Created"))