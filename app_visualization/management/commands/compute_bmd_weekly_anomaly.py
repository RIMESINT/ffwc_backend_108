import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Robust 7-Day Weekly Anomaly for BMD-WRF with 1-day fallback'

    def add_arguments(self, parser):
        # 1. Positional argument support for manual CLI backup runs
        parser.add_argument('fdate', nargs='?', type=str, help='Forecast date YYYYMMDD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')

        if ui_date:
            # Clean dashboard template dashes safely: '2026-06-30' -> '20260630'
            fdate_input = ui_date.replace('-', '')
            self.stdout.write(self.style.SUCCESS(f"###### Received date parameter via UI Selector: {ui_date} -> Normalized to: {fdate_input}"))
        elif positional_date:
            fdate_input = positional_date
            self.stdout.write(self.style.SUCCESS(f"###### Received date parameter via Positional CLI: {fdate_input}"))
        else:
            fdate_input = dt.now().strftime('%Y%m%d')
            self.stdout.write(self.style.NOTICE(f"###### No runtime date parameter detected. Defaulting to system time: {fdate_input}"))

        date_obj = dt.strptime(fdate_input, '%Y%m%d')
        
        # --- Fallback Logic ---
        WRF_NC_FILE = None
        current_attempt_date = date_obj
        
        # Check Today, then check Yesterday
        for i in range(2):
            check_date = (current_attempt_date - timedelta(days=i)).strftime('%Y%m%d')
            temp_path = os.path.join(settings.BASE_DIR, 'forecast', 'bmd_wrf', f'wrf_out_{check_date}00.nc')
            if os.path.exists(temp_path):
                WRF_NC_FILE = temp_path
                actual_fdate = check_date
                break
        
        if not WRF_NC_FILE:
            self.stdout.write(self.style.WARNING(f"⚠️ No BMD-WRF file found for {fdate_input} or yesterday. Exiting."))
            return

        self.stdout.write(f"✅ Using File: {WRF_NC_FILE}")

        # --- Computation ---
        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate_input, 'BMD-WRF')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        CLIMO_PATH = os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc')

        ds_climo = xr.open_dataset(CLIMO_PATH)
        ds_wrf = xr.open_dataset(WRF_NC_FILE).squeeze()
        wrf_acc = (ds_wrf['rainc'] + ds_wrf['rainnc'])

        t0 = pd.Timestamp(dt.strptime(actual_fdate, '%Y%m%d'))
        t7 = t0 + timedelta(days=7)
        
        # Verify t7 exists in the NC file before proceeding
        if t7 not in ds_wrf.time.values:
            self.stdout.write(self.style.ERROR(f" Forecast in {WRF_NC_FILE} does not reach 7 days."))
            return

        wrf_weekly_mean = (wrf_acc.sel(time=t7) - wrf_acc.sel(time=t0)) / 7
        wrf_regridded = wrf_weekly_mean.interp(lat=ds_climo.lat, lon=ds_climo.lon)

        doys = [(t0 + timedelta(days=i)).dayofyear for i in range(7)]
        climo_weekly_mean = ds_climo['precipitation'].sel(dayofyear=doys).mean(dim='dayofyear')

        weekly_anomaly = (wrf_regridded - climo_weekly_mean).to_dataset(name='weekly_anomaly')
        weekly_anomaly.to_netcdf(os.path.join(OUTPUT_ROOT, f'bmd_weekly_anomaly_{fdate_input}.nc'))
        self.stdout.write(self.style.SUCCESS(f"✅ Success for {fdate_input}"))