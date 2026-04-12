import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Step 1: Compute Anomaly NetCDF from UKMET Deterministic and Climatology'

    def add_arguments(self, parser):
        # Accepts YYYYMMDD
        parser.add_argument('fdate', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        # 1. Date Parsing
        fdate_input = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        
        # 2. Paths
        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate_input, 'UKMET')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        
        CLIMO_PATH = os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc')
        UKMET_NC_FILE = os.path.join(settings.BASE_DIR, 'forecast', 'ukmet_det_data', f'precip_{fdate_input}.nc')

        self.stdout.write(f"🔍 Searching for UKMET File: {UKMET_NC_FILE}")

        if not os.path.exists(UKMET_NC_FILE):
            self.stdout.write(self.style.ERROR(f"❌ File not found: {UKMET_NC_FILE}"))
            return

        # 3. Load and Prepare Data
        ds_climo = xr.open_dataset(CLIMO_PATH)
        ds_uk = xr.open_dataset(UKMET_NC_FILE)
        
        # Rename dimensions to avoid conflicts during interpolation
        ds_uk = ds_uk.rename({'latitude': 'lat', 'longitude': 'lon'})
        
        # UKMET is already in mm, no scaling needed
        uk_precip = ds_uk['tp']
        
        # Crop Climatology to match UKMET spatial extent
        ds_climo_cropped = ds_climo.sel(
            lat=slice(ds_uk.lat.max().item() + 0.5, ds_uk.lat.min().item() - 0.5),
            lon=slice(ds_uk.lon.min().item() - 0.5, ds_uk.lon.max().item() + 0.5)
        ).load()

        all_times = pd.to_datetime(ds_uk.time.values)
        anomaly_cubes = []

        # 4. Calculation Loop
        for t in all_times:
            # Get Day of Year for the specific forecast timestamp
            doy = t.dayofyear
            
            self.stdout.write(f"Processing UKMET Anomaly for: {t.date()} (DOY: {doy})")

            # Extract daily total directly (UKMET is usually daily non-accumulated)
            daily_rain = uk_precip.sel(time=t)
            
            # Regrid Forecast to Climatology Resolution
            daily_regridded = daily_rain.interp(
                lat=ds_climo_cropped.lat, 
                lon=ds_climo_cropped.lon,
                method="linear"
            )
            
            # Get Climatology slice
            climo_slice = ds_climo_cropped['precipitation'].sel(dayofyear=doy)
            
            # Compute Anomaly
            day_anomaly = daily_regridded - climo_slice
            anomaly_cubes.append(day_anomaly.expand_dims(time=[t]))

        # 5. Save NetCDF
        if anomaly_cubes:
            full_nc_path = os.path.join(OUTPUT_ROOT, f'ukmet_rainfall_anomaly_{fdate_input}.nc')
            xr.concat(anomaly_cubes, dim='time').to_dataset(name='rainfall_anomaly').to_netcdf(full_nc_path)
            self.stdout.write(self.style.SUCCESS(f"✅ UKMET Anomaly NetCDF Created: {full_nc_path}"))