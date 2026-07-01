import os
import ftplib 
import stat
import paramiko
import sys
import json
import pylab as pl 
import numpy as np
import pandas as pd
import xarray as xr
import cftime 
import netCDF4 as nc
import subprocess
from yaspin import yaspin
from yaspin.spinners import Spinners
from django.core.management.base import BaseCommand
from django.conf import settings
import geojsoncontour as gj 
import mysql.connector as mconn 
import matplotlib.colors as mplcolors
from netCDF4 import Dataset as nco, num2date
from datetime import datetime as dt, timedelta as delt 
from scipy.ndimage import zoom
from tqdm import tqdm

from app_visualization.models import Source, SystemState
from ffwc_django_project.project_constant import app_visualization

SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][6]
BD_DETAILS = app_visualization['bd_details']
ECMWF_BASE_URL = settings.BASE_DIR

print(" #################################################################")
print(" ########## level_wise_forecast_ecmwf ############################")
print(" #################################################################")
###################################################################
### PRINT CURRENT DATE TIME
###################################################################
curr_date_time = dt.now()
curr_date_time_str = curr_date_time.strftime("%d-%m-%Y %H:%M:%S")
print(" ########################## ", curr_date_time_str, " ##############")


class Command(BaseCommand):
    help = '[Generate location Forecast]'

    def add_arguments(self, parser):
        # 1. Positional argument support for manual CLI backup runs
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')

        if ui_date:
            # Clean dashboard template dashes safely: '2026-06-29' -> '20260629'
            fcst_date = ui_date.replace('-', '')
            print(f"###### Received date parameter via UI Selector: {ui_date} -> Normalized to: {fcst_date}")
        elif positional_date:
            fcst_date = positional_date
            print(f"###### Received date parameter via Positional CLI: {fcst_date}")
        else:
            today_date = dt.now()
            fcst_date = today_date.strftime('%Y%m%d')  # Default fallback layout = YYYYMMDD
            print(f"###### No runtime date parameter detected. Defaulting to system time: {fcst_date}")
        
        self.main(fcst_date)

    def download_data(self, fdate, folder_path):
        """
            ##################################################
            ### Download BMD WRF data from their SFTP Server
            ##################################################
        """
        print(" ###### download_data date: ", fdate) 
        
        try:
            with yaspin(Spinners.dots, text="File Downloading...") as spinner:
                # Use robust os.path.join for loading environment configurations safely
                env_file_path = os.path.join(str(ECMWF_BASE_URL), 'env.json')
                with open(env_file_path, 'r') as envf:
                    env_ = json.load(envf)

                FTP_CONF = env_['bmdwrf_ecmwf_ssh_conf']
                
                ftp_host = FTP_CONF["HOST"]
                ftp_user = FTP_CONF["USER"]
                ftp_password = FTP_CONF["PASSWORD"]
                
                remote_file_path = f"/RIMESNAS/WRF_OUT/wrf_out_{fdate}00.nc"
                print("remote_file_path: ", remote_file_path)
    
                destination_directory = str(folder_path)
                print("destination_directory: ", destination_directory)

                # Ensure the destination directory exists
                if not os.path.exists(destination_directory):
                    os.makedirs(destination_directory)
                    os.chmod(
                        destination_directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
                    )  # chmod 777 permission

                # Target temporary file for raw download to decouple source from crop target names
                local_filepath = os.path.join(
                    destination_directory, 
                    f"wrf_out_{fdate}00_main.nc"
                )

                print("Connecting to SSH server...")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ftp_host, username=ftp_user, password=ftp_password)

                print("Starting file download from SSH server...")
                with ssh.open_sftp() as sftp:
                    file_size = sftp.stat(remote_file_path).st_size
                    with tqdm(total=file_size, unit='B', unit_scale=True, desc=os.path.basename(remote_file_path)) as pbar:
                        with sftp.open(remote_file_path, 'rb') as remote_file:
                            with open(local_filepath, 'wb') as local_file:
                                while True:
                                    data = remote_file.read(32768)  # Read in chunks
                                    if not data:
                                        break
                                    local_file.write(data)
                                    pbar.update(len(data))
                spinner.ok("✔")
                print("File Downloaded successfully.")

                os.chmod(
                    destination_directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
                )
                print("Permission provided successfully.")
                return True

        except Exception as e:
            spinner.fail("✗")
            print(f"An error occurred during file sync transfer: {e}")
            return False
        finally:
            if 'ssh' in locals():
                ssh.close()
                print("Disconnecting from SSH server.")

    def crop_nc_file_for_bd(self, fdate, folder_path):
        """
            ################################################################
            ### Crop Merged Hourly Steps BMD WRF data for Bangladesh Only 
            ################################################################
        """
        print(" ###### crop_nc_file_for_bd date: ", fdate) 

        src_file = os.path.join(str(folder_path), f"wrf_out_{fdate}00_main.nc")
        dst_file = os.path.join(str(folder_path), f"wrf_out_{fdate}00.nc")

        if not os.path.exists(src_file):
            print(f"❌ Missing source template for matrix crop: {src_file}")
            return False

        try:
            with yaspin(Spinners.dots, text="File Cropping...") as spinner:
                lat_min = BD_DETAILS['BD_LAT_MIN']  
                lat_max = BD_DETAILS['BD_LAT_MAX']  
                lon_min = BD_DETAILS['BD_LON_MIN']  
                lon_max = BD_DETAILS['BD_LON_MAX']  

                src_ds = nc.Dataset(src_file, 'r')

                lat = src_ds.variables['lat'][:]
                lon = src_ds.variables['lon'][:]

                lat_indices = np.where((lat >= lat_min) & (lat <= lat_max))[0]
                lon_indices = np.where((lon >= lon_min) & (lon <= lon_max))[0]

                dst_ds = nc.Dataset(dst_file, 'w')

                for name, dimension in src_ds.dimensions.items():
                    if name == 'lat':
                        dst_ds.createDimension(name, len(lat_indices))
                    elif name == 'lon':
                        dst_ds.createDimension(name, len(lon_indices))
                    else:
                        dst_ds.createDimension(name, len(dimension) if not dimension.isunlimited() else None)

                for name, variable in src_ds.variables.items():
                    dst_var = dst_ds.createVariable(name, variable.datatype, variable.dimensions)
                    dst_var.setncatts({k: variable.getncattr(k) for k in variable.ncattrs()})
                    if name == 'lat':
                        dst_var[:] = lat[lat_indices]
                    elif name == 'lon':
                        dst_var[:] = lon[lon_indices]
                    elif 'lat' in variable.dimensions and 'lon' in variable.dimensions:
                        lat_dim = variable.dimensions.index('lat')
                        lon_dim = variable.dimensions.index('lon')
                        data = variable[:]
                        if lat_dim == 1 and lon_dim == 2:
                            dst_var[:] = data[:, lat_indices, :][:, :, lon_indices]
                        elif lat_dim == 2 and lon_dim == 1:
                            dst_var[:] = data[:, :, lat_indices][:, lon_indices, :]
                        else:
                            raise ValueError(f"Unexpected dimension order in variable {name}")
                    else:
                        dst_var[:] = variable[:]

                dst_ds.setncatts({k: src_ds.getncattr(k) for k in src_ds.ncattrs()})

                src_ds.close()
                dst_ds.close()

                # Clean up the large raw source file after a successful crop to optimize system storage space
                if os.path.exists(src_file):
                    os.remove(src_file)

                spinner.ok("✔")
                print("File Cropped successfully.") 
                return True
        except Exception as e:
            spinner.fail("✗")
            print(f"An error occurred during multi-dimensional matrix slicing: {e}")
            return False

    def main(self, date):
        source_obj = Source.objects.filter(
            name="BMDWRF", 
            source_type="basin_specific",
            source_data_type__name="Forecast"
        )[0]
        WRF_NC_LOC_ECMWF_HRES = source_obj.source_path
        
        folder_path = os.path.join(str(ECMWF_BASE_URL), WRF_NC_LOC_ECMWF_HRES.strip("/"))
        print(" $$$$$$ folder_path: ", folder_path) 
        
        if self.download_data(date, folder_path):
            self.crop_nc_file_for_bd(date, folder_path)