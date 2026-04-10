import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from app_visualization.models import Source

class Command(BaseCommand):
    help = 'Step 1: Compute Anomaly NetCDF from raw WRF and Climatology'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        
        # Paths
        OUTPUT_ROOT = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate, 'BMD-WRF')
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        
        CLIMO_PATH = os.path.join(settings.BASE_DIR, 'climatology_data', 'rainfallClimatology.nc')
        source_obj = Source.objects.get(name='BMDWRF_HRES_VIS', source_type="vis")
        WRF_NC_FILE = os.path.join(settings.BASE_DIR, source_obj.source_path.strip('/'), f'wrf_out_{fdate}00.nc')

        if not os.path.exists(WRF_NC_FILE):
            self.stdout.write(self.style.ERROR(f"WRF File not found: {WRF_NC_FILE}"))
            return

        # Calculation
        ds_climo = xr.open_dataset(CLIMO_PATH)
        ds_wrf = xr.open_dataset(WRF_NC_FILE)
        if 'lev' in ds_wrf.dims: ds_wrf = ds_wrf.squeeze('lev')
        
        wrf_acc = (ds_wrf['rainc'] + ds_wrf['rainnc'])
        ds_climo_cropped = ds_climo.sel(
            lat=slice(ds_wrf.lat.max().item() + 0.1, ds_wrf.lat.min().item() - 0.1),
            lon=slice(ds_wrf.lon.min().item() - 0.1, ds_wrf.lon.max().item() + 0.1)
        ).load()

        all_times = pd.to_datetime(ds_wrf.time.values)
        unique_days = np.unique(all_times.date)
        anomaly_cubes = []

        for day in unique_days:
            t_start, t_end = pd.Timestamp(day), pd.Timestamp(day) + timedelta(days=1)
            if t_start in all_times and t_end in all_times:
                daily_rain = wrf_acc.sel(time=t_end) - wrf_acc.sel(time=t_start)
                daily_regridded = daily_rain.interp(lat=ds_climo_cropped.lat, lon=ds_climo_cropped.lon)
                climo_slice = ds_climo_cropped['precipitation'].sel(dayofyear=t_start.dayofyear)
                anomaly_cubes.append((daily_regridded - climo_slice).expand_dims(time=[t_start]))

        # Save NetCDF
        full_nc_path = os.path.join(OUTPUT_ROOT, f'bmd_rainfall_anomaly_{fdate}.nc')
        xr.concat(anomaly_cubes, dim='time').to_dataset(name='rainfall_anomaly').to_netcdf(full_nc_path)
        self.stdout.write(self.style.SUCCESS(f"✅ NetCDF Created: {full_nc_path}"))