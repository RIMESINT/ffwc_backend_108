import os
import requests
import numpy as np
import netCDF4 as nc
from datetime import datetime as dt
from django.core.management.base import BaseCommand
from django.conf import settings
from tqdm import tqdm

from app_visualization.models import Source

# Constants
ECMWF_BASE_URL = settings.BASE_DIR

# These values are extracted directly from your BMDWRF file inspection
# to ensure the maps align perfectly without needing the BMD NC file present.
BMD_STATIC_EXTENT = {
    'LAT_MIN': 13.38,
    'LAT_MAX': 30.63,
    'LON_MIN': 80.00,  # Adjusted based on standard BMD regional wide-view
    'LON_MAX': 100.00  # Adjusted based on standard BMD regional wide-view
}

class Command(BaseCommand):
    help = "Downloads and Crops ECMWF data using a static BMD-matching extent"

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Date in YYYYMMDD format')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **options): 
        ui_date = options.get('date')
        positional_date = options.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if raw_date:
            # Clean dashboard template dashes safely: '2026-07-01' -> '20260701'
            fdate = raw_date.replace('-', '')
            self.stdout.write(self.style.SUCCESS(f"###### Received date parameter: {raw_date} -> Normalized to: {fdate}"))
        else:
            fdate = dt.now().strftime('%Y%m%d')
            self.stdout.write(self.style.NOTICE(f"###### No date provided. Defaulting to system time: {fdate}"))
        
        try:
            source_obj = Source.objects.get(name="ECMWF_HRES_VIS", source_type="vis")
        except Source.DoesNotExist:
            self.stderr.write(self.style.ERROR("Source ECMWF_HRES_VIS not found."))
            return

        download_output_dir = os.path.join(str(ECMWF_BASE_URL), source_obj.source_path.strip("/"), fdate)
        
        self.stdout.write(self.style.SUCCESS(f"Targeting Static BMD Extent: Lat {BMD_STATIC_EXTENT['LAT_MIN']} to {BMD_STATIC_EXTENT['LAT_MAX']}"))
        self.process_pipeline(download_output_dir, fdate)

    def crop_nc_file(self, file_path):
        """Subsets the NetCDF file to match the BMD regional extent."""
        temp_file = file_path + ".tmp"
        if os.path.exists(temp_file): os.remove(temp_file)
        os.rename(file_path, temp_file)

        try:
            with nc.Dataset(temp_file, 'r') as src:
                lat = src.variables['lat'][:]
                lon = src.variables['lon'][:]
                
                # Identify indices using the static BMD extent
                lat_idx = np.where((lat >= BMD_STATIC_EXTENT['LAT_MIN']) & (lat <= BMD_STATIC_EXTENT['LAT_MAX']))[0]
                lon_idx = np.where((lon >= BMD_STATIC_EXTENT['LON_MIN']) & (lon <= BMD_STATIC_EXTENT['LON_MAX']))[0]

                if len(lat_idx) == 0 or len(lon_idx) == 0:
                    raise ValueError("Static extent is outside the ECMWF file's geographic range.")

                with nc.Dataset(file_path, 'w') as dst:
                    # 1. Replicate Dimensions
                    for name, dimension in src.dimensions.items():
                        if name == 'lat':
                            dst.createDimension(name, len(lat_idx))
                        elif name == 'lon':
                            dst.createDimension(name, len(lon_idx))
                        else:
                            dst.createDimension(name, len(dimension) if not dimension.isunlimited() else None)

                    # 2. Replicate Variables with Spatial Slicing
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
                            
                            # Use np.take to safely extract the regional rectangle
                            subset = np.take(data, lat_idx, axis=lat_dim)
                            subset = np.take(subset, lon_idx, axis=lon_dim)
                            dst_var[:] = subset
                        else:
                            dst_var[:] = data

                    # 3. Global Attributes
                    dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})
            
            os.remove(temp_file)
            self.stdout.write(self.style.SUCCESS(f"Successfully cropped to {len(lat_idx)}x{len(lon_idx)} grid."))
            return True
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Processing failed: {e}"))
            if os.path.exists(temp_file): os.rename(temp_file, file_path)
            return False

    def process_pipeline(self, output_dir, fdate):
        base_url = f"https://open-data.rimes.int/Regional/rimes/ECMWF/ifs15/{fdate}/"
        os.makedirs(output_dir, exist_ok=True)
        
        file_name = "tp.nc"
        file_path = os.path.join(output_dir, file_name)
        
        try:
            response = requests.get(base_url + file_name, stream=True, timeout=60)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(file_path, "wb") as f, tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Downloading {file_name}") as pbar:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            self.crop_nc_file(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Pipeline Error: {e}"))