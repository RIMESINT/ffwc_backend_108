# management/commands/generate_forecast_data.py

import os
import ftplib 
import stat
import paramiko

import xarray as xr
import numpy as np
import pandas as pd

import cftime 
import json
import pylab as pl 
import numpy as np
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

from app_visualization.models import (
    Source, SystemState
)

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
		parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')
		# pass
		# parser.add_argument('date', type=str, help='date for netcdf file')
	  

	def handle(self, *args, **kwargs):
		fcst_date = kwargs['fdate']

		if fcst_date is None:
			today_date = dt.now()
			formatted_date = today_date.strftime('%d%m%Y')  # Date format = DDMMYYYY
			print("formatted_date: ", formatted_date)
			fcst_date = formatted_date
		
		# fcst_date = '20230516'
		self.main(fcst_date)


	
			

	def download_data(self, fdate, folder_path):
		"""
			##################################################
			### Download IMD WRF data from their FTP Server
			##################################################
		"""
		
		print(" ###### download_data date: ", fdate) 

		
		try:
			with yaspin(Spinners.dots, text="File Downloading...") as spinner:

				with open(ECMWF_BASE_URL / 'env.json', 'r') as envf:
					env_ = json.load(envf)

				FTP_CONF = env_['bmdwrf_ecmwf_ssh_conf']
				
				ftp_host = FTP_CONF["HOST"]
				ftp_user = FTP_CONF["USER"]
				ftp_password = FTP_CONF["PASSWORD"]
				
				remote_file_path = f"/dataex-nc-cache/ecmwf-hres/{fdate}.nc"
				destination_directory = str(folder_path)
				# destination_directory = "/home/shaif/Downloads"

				# Ensure the destination directory exists
				if not os.path.exists(destination_directory):
					os.makedirs(destination_directory)
					os.chmod(
						destination_directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
					)  # chmod 777 permission

				# Local file path
				local_filepath = os.path.join(
					destination_directory, 
					os.path.basename(remote_file_path)
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

				os.rename(
					f"{destination_directory}{fdate}.nc", 
					f"{destination_directory}{fdate}_main.nc"
				)
				print(f"Chnaged file name {fdate}.nc to {fdate}_main.nc successfully.")

		except Exception as e:
			spinner.fail("✗")
			print(f"An error occurred: {e}")
		finally:
			ssh.close()
			print("Disconnecting from SSH server.")

	
	def crop_nc_file_for_bd(self, fdate, folder_path):
		"""
			################################################################
			### Crop Merged Hourly Steps IMD WRF data for Bangladesh Only 
			################################################################
		"""


		print(" ###### crop_nc_file_for_bd date: ", fdate) 

		try:
			with yaspin(Spinners.dots, text="File Cropping...") as spinner:
				# result = subprocess.run(ncks_command, check=True, capture_output=True, text=True)
				
		
				# Open the source NetCDF file
				src_file = str(folder_path) + f"{fdate}_main.nc"
				dst_file = str(folder_path) + f"{fdate}.nc"

				# Define the latitude and longitude bounds
				lat_min = BD_DETAILS['BD_LAT_MIN']	#22.0
				lat_max = BD_DETAILS['BD_LAT_MAX']	#28.0
				lon_min = BD_DETAILS['BD_LON_MIN']	#86.0
				lon_max = BD_DETAILS['BD_LON_MAX']	#97.0

				# Open the source dataset
				src_ds = nc.Dataset(src_file, 'r')

				# Extract the latitude and longitude variables
				latitude = src_ds.variables['latitude'][:]
				longitude = src_ds.variables['longitude'][:]

				# Find the indices that match the desired latitude and longitude ranges
				lat_indices = np.where((latitude >= lat_min) & (latitude <= lat_max))[0]
				lon_indices = np.where((longitude >= lon_min) & (longitude <= lon_max))[0]

				# Open a new NetCDF file to store the subset
				dst_ds = nc.Dataset(dst_file, 'w')

				# Copy the dimensions
				for name, dimension in src_ds.dimensions.items():
					if name == 'latitude':
						dst_ds.createDimension(name, len(lat_indices))
					elif name == 'longitude':
						dst_ds.createDimension(name, len(lon_indices))
					else:
						dst_ds.createDimension(name, len(dimension) if not dimension.isunlimited() else None)

				# Copy the variables
				for name, variable in src_ds.variables.items():
					dst_var = dst_ds.createVariable(name, variable.datatype, variable.dimensions)
					# Copy variable attributes
					dst_var.setncatts({k: variable.getncattr(k) for k in variable.ncattrs()})
					# Copy the variable data, only for the selected latitude and longitude ranges
					if name == 'latitude':
						dst_var[:] = latitude[lat_indices]
					elif name == 'longitude':
						dst_var[:] = longitude[lon_indices]
					elif 'latitude' in variable.dimensions and 'longitude' in variable.dimensions:
						lat_dim = variable.dimensions.index('latitude')
						lon_dim = variable.dimensions.index('longitude')
						data = variable[:]
						# Use slicing to select the appropriate data range
						if lat_dim == 1 and lon_dim == 2:
							dst_var[:] = data[:, lat_indices, :][:, :, lon_indices]
						elif lat_dim == 2 and lon_dim == 1:
							dst_var[:] = data[:, :, lat_indices][:, lon_indices, :]
						else:
							raise ValueError(f"Unexpected dimension order in variable {name}")
					else:
						dst_var[:] = variable[:]

				# Copy the global attributes
				dst_ds.setncatts({k: src_ds.getncattr(k) for k in src_ds.ncattrs()})

				# Close the datasets
				src_ds.close()
				dst_ds.close()

				spinner.ok("✔")
				print("File Cropped successfully.") 

				# print(f"Subset created and saved to {dst_file}")
		except subprocess.CalledProcessError as e:
			spinner.fail("✗")
			print(f"An error occurred on File Cropping: {e}")
			print("Command Output:", e.stdout)
			print("Command Error:", e.stderr)



	def main(self, date):

		source_obj = Source.objects.filter(
			name="ECMWF_HRES", 
			source_type="basin_specific",
			source_data_type__name="Forecast"
		)[0]
		WRF_NC_LOC_ECMWF_HRES = source_obj.source_path
		
		# folder_path = os.getcwd()
		folder_path = str(ECMWF_BASE_URL)+str(WRF_NC_LOC_ECMWF_HRES)
		print(" $$$$$$ folder_path: ", folder_path) 
		
		self.download_data(date, folder_path) 
		self.crop_nc_file_for_bd(date, folder_path)
		


		


