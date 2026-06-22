import os
import xarray as xr
import pandas as pd
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Robust 7-Day Weekly Anomaly for ECMWF with 1-day fallback'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        fdate_input = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        date_obj = dt.strptime(fdate_input, '%Y%m%d')
        
        EC_NC_FILE = None
        for i in range(2):
            check_date = (date_obj - timedelta(days=i)).strftime('%d%m%Y')
            temp_path = os.path.join(settings.BASE_DIR, 'forecast', 'ecmwf_0_2', f'{check_date}.nc')
            if os.path.exists(temp_path):
                EC_NC_FILE = temp_path
                actual_date_obj = date_obj - timedelta(days=i)
                break

        if not EC_NC_FILE:
            self.stdout.write(self.style.WARNING("⚠️ ECMWF File not found for today or yesterday."))
            return

        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate_input, 'ECMWF')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        ds_climo = xr.open_dataset(os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc'))
        
        ds_ec = xr.open_dataset(EC_NC_FILE).rename({'latitude': 'lat', 'longitude': 'lon'})
        ec_acc = ds_ec['cp'] * 1000
        
        t0 = pd.Timestamp(actual_date_obj)
        t7 = t0 + timedelta(days=7)
        
        if t7 not in ds_ec.time.values:
            self.stdout.write(self.style.ERROR("❌ ECMWF file does not contain full 7-day lead time."))
            return

        ec_weekly_mean = (ec_acc.sel(time=t7) - ec_acc.sel(time=t0)) / 7
        ec_regridded = ec_weekly_mean.interp(lat=ds_climo.lat, lon=ds_climo.lon)

        doys = [(t0 + timedelta(days=i)).dayofyear for i in range(7)]
        climo_mean = ds_climo['precipitation'].sel(dayofyear=doys).mean(dim='dayofyear')

        weekly_anomaly = (ec_regridded - climo_mean).to_dataset(name='weekly_anomaly')
        weekly_anomaly.to_netcdf(os.path.join(OUTPUT_ROOT, f'ecmwf_weekly_anomaly_{fdate_input}.nc'))
        self.stdout.write(self.style.SUCCESS(f"✅ ECMWF Weekly Created using {EC_NC_FILE}"))