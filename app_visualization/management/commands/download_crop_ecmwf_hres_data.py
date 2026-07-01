# -*- coding: utf-8 -*-
import os
import warnings

# --- WARNING FILTERS DIAGNOSTICS CLEANUP ---
warnings.filterwarnings("ignore", message=".*TripleDES.*")

import requests
import numpy as np
import netCDF4 as nc
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from tqdm import tqdm

from app_visualization.models import Source

# Constants
ECMWF_BASE_URL = settings.BASE_DIR

BMD_STATIC_EXTENT = {
    'LAT_MIN': 13.38,
    'LAT_MAX': 30.63,
    'LON_MIN': 80.00,  
    'LON_MAX': 100.00  
}

class Command(BaseCommand):
    help = "Downloads and Crops ECMWF data using a static BMD-matching extent with 1-day fallback"

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Date in YYYYMMDD format')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Target date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **options): 
        ui_date = options.get('date')
        positional_date = options.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if not raw_date:
            base_date = dt.now()
        else:
            clean_date = raw_date.replace('-', '')
            try:
                base_date = dt.strptime(clean_date, "%Y%m%d")
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format received: {raw_date}"))
                return
        
        try:
            source_obj = Source.objects.get(name="ECMWF_HRES_VIS", source_type="vis")
        except Source.DoesNotExist:
            self.stderr.write(self.style.ERROR("Source ECMWF_HRES_VIS not found in database."))
            return

        # Try targeted date first; fallback to yesterday if it fails
        target_fdate = base_date.strftime('%Y%m%d')
        fallback_fdate = (base_date - timedelta(days=1)).strftime('%Y%m%d')

        self.stdout.write(self.style.NOTICE(f"Processing ECMWF HRES pipeline. Target: {target_fdate} | Fallback: {fallback_fdate}"))
        self.stdout.write(self.style.NOTICE(f"Targeting Static BMD Extent: Lat {BMD_STATIC_EXTENT['LAT_MIN']} to {BMD_STATIC_EXTENT['LAT_MAX']}"))

        # Step 1: Attempt Target Date Ingestion
        download_output_dir = os.path.join(str(ECMWF_BASE_URL), source_obj.source_path.strip("/"), target_fdate)
        success = self.process_pipeline(download_output_dir, target_fdate)

        # Step 2: Day-1 Fallback Loop Action
        if not success:
            self.stdout.write(self.style.WARNING(f"⚠️ Data missing for target date {target_fdate}. Executing historical Day-1 fallback to: {fallback_fdate}..."))
            fallback_output_dir = os.path.join(str(ECMWF_BASE_URL), source_obj.source_path.strip("/"), fallback_fdate)
            success_fallback = self.process_pipeline(fallback_output_dir, fallback_fdate)
            
            if not success_fallback:
                self.stderr.write(self.style.ERROR(f"❌ Critical Failure: No ECMWF HRES data found for target or fallback windows."))

    def crop_nc_file(self, file_path):
        """Subsets the NetCDF file to match the BMD regional extent."""
        temp_file = file_path + ".tmp"
        if os.path.exists(temp_file): os.remove(temp_file)
        os.rename(file_path, temp_file)

        try:
            with nc.Dataset(temp_file, 'r') as src:
                lat = src.variables['lat'][:]
                lon = src.variables['lon'][:]
                
                lat_idx = np.where((lat >= BMD_STATIC_EXTENT['LAT_MIN']) & (lat <= BMD_STATIC_EXTENT['LAT_MAX']))[0]
                lon_idx = np.where((lon >= BMD_STATIC_EXTENT['LON_MIN']) & (lon <= BMD_STATIC_EXTENT['LON_MAX']))[0]

                if len(lat_idx) == 0 or len(lon_idx) == 0:
                    raise ValueError("Static extent is outside the ECMWF file's geographic range.")

                with nc.Dataset(file_path, 'w') as dst:
                    for name, dimension in src.dimensions.items():
                        if name == 'lat':
                            dst.createDimension(name, len(lat_idx))
                        elif name == 'lon':
                            dst.createDimension(name, len(lon_idx))
                        else:
                            dst.createDimension(name, len(dimension) if not dimension.isunlimited() else None)

                    for name, variable in src.variables.items():
                        dst_var = dst.createVariable(name, variable.datatype, variable.dimensions)
                        dst_var.setncatts({k: variable.getncattr(k) for k in variable.ncattrs()})
                        
                        data = variable[:]
                        if name == 'lat':
                            dst_var[:] = lat[lat_idx]
                        elif name == 'lon':
                            dst_var[:] = lon[lon_idx]
                        elif 'lat' in variable.dimensions and 'lon' in variable.dimensions:
                            lat_dim = variable.dimensions.index('lat')
                            lon_dim = variable.dimensions.index('lon')
                            
                            subset = np.take(data, lat_idx, axis=lat_dim)
                            subset = np.take(subset, lon_idx, axis=lon_dim)
                            dst_var[:] = subset
                        else:
                            dst_var[:] = data

                    dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})
            
            os.remove(temp_file)
            self.stdout.write(self.style.SUCCESS(f"Successfully cropped to {len(lat_idx)}x{len(lon_idx)} grid."))
            return True
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Crop processing failed: {e}"))
            if os.path.exists(temp_file): os.rename(temp_file, file_path)
            return False

    def process_pipeline(self, output_dir, fdate):
        base_url = f"https://open-data.rimes.int/Regional/rimes/ECMWF/ifs15/{fdate}/"
        file_name = "tp.nc"
        file_path = os.path.join(output_dir, file_name)
        
        try:
            # Check headers first to bypass file allocation if remote endpoint returns a 404
            response = requests.get(base_url + file_name, stream=True, timeout=30)
            if response.status_code == 404:
                self.stdout.write(self.style.WARNING(f"File {file_name} not yet published on open-data for run: {fdate}"))
                return False
                
            response.raise_for_status()
            os.makedirs(output_dir, exist_ok=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(file_path, "wb") as f, tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Downloading {file_name}") as pbar:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            self.stdout.write(self.style.SUCCESS(f"Downloaded {file_name} successfully. Starting crop..."))
            return self.crop_nc_file(file_path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Pipeline connectivity gap discovered for date {fdate}: {e}"))
            if os.path.exists(file_path): os.remove(file_path)
            return False