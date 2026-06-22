import os
import xarray as xr
import pandas as pd
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Robust 7-Day Weekly Anomaly for UKMET with 1-day fallback'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        fdate_input = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        date_obj = dt.strptime(fdate_input, '%Y%m%d')
        
        UK_NC_FILE = None
        for i in range(2):
            check_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')
            temp_path = os.path.join(settings.BASE_DIR, 'forecast', 'ukmet_det_data', f'precip_{check_date}.nc')
            if os.path.exists(temp_path):
                UK_NC_FILE = temp_path
                break

        if not UK_NC_FILE:
            self.stdout.write(self.style.WARNING("⚠️ UKMET File not found for today or yesterday."))
            return

        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate_input, 'UKMET')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        ds_climo = xr.open_dataset(os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc'))
        
        ds_uk = xr.open_dataset(UK_NC_FILE).rename({'latitude': 'lat', 'longitude': 'lon'})
        
        if len(ds_uk.time) < 7:
            self.stdout.write(self.style.ERROR("❌ UKMET file has less than 7 days of data."))
            return

        uk_weekly_mean = ds_uk['tp'].isel(time=slice(0, 7)).mean(dim='time')
        uk_regridded = uk_weekly_mean.interp(lat=ds_climo.lat, lon=ds_climo.lon)

        t_start = pd.to_datetime(ds_uk.time.values[0])
        doys = [(t_start + timedelta(days=i)).dayofyear for i in range(7)]
        climo_mean = ds_climo['precipitation'].sel(dayofyear=doys).mean(dim='dayofyear')

        weekly_anomaly = (uk_regridded - climo_mean).to_dataset(name='weekly_anomaly')
        weekly_anomaly.to_netcdf(os.path.join(OUTPUT_ROOT, f'ukmet_weekly_anomaly_{fdate_input}.nc'))
        self.stdout.write(self.style.SUCCESS(f"✅ UKMET Weekly Created using {UK_NC_FILE}"))