# management/commands/generate_forecast_data.py

import os
import ftplib 
import stat

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

from concurrent.futures import ThreadPoolExecutor

from app_visualization.models import (
    Source, SystemState
)

from ffwc_django_project.project_constant import app_visualization
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][6]
BD_DETAILS = app_visualization['bd_details']
ECMWF_BASE_URL = settings.BASE_DIR
max_workers = 10








print(" #################################################################")
print(" ########## level_wise_forecast_ecmwf ############################")
print(" #################################################################")
###################################################################
### PRINT CURRENT DATE TIME
###################################################################
curr_date_time = dt.now()
curr_date_time_str = curr_date_time.strftime("%d-%m-%Y %H:%M:%S")
print(" ########################## ", curr_date_time_str, " ##############")








def ftp_connect(ftp_directory):

	with open(ECMWF_BASE_URL / 'env.json', 'r') as envf:
		env_ = json.load(envf)

	FTP_CONF = env_['imd_gfs_ftp_conf']

	ftp_host = FTP_CONF["HOST"]
	ftp_user = FTP_CONF["USER"]
	ftp_password = FTP_CONF["PASSWORD"]

	ftp = ftplib.FTP(ftp_host)
	ftp.login(ftp_user, ftp_password)
	ftp.cwd(ftp_directory)
	return ftp 


def r2(val):
	return np.round(val,2)


def thi_(temp:float,rh:float)->float:
	# THI = 0.8 * t_db + RH * (t_tdb − 14.4) + 46.4
	return (0.8*temp) + (rh/100)*(temp-14.4) + 46.4



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
			formatted_date = today_date.strftime('%Y%m%d')  # Date format = YYYYMMDD
			print("formatted_date: ", formatted_date)
			fcst_date = formatted_date
		
		# fcst_date = '20230516'
		self.main(fcst_date)
			

	def download_data(self, fdate, folder_path, filename):
		"""
			##################################################
			### Download IMD WRF data from their FTP Server
			##################################################
		"""
		
		print(" ###### download_data date: ", fdate) 

		
		try:
			with yaspin(Spinners.dots, text="File Downloading...") as spinner:
				

				destination_directory = folder_path
				if not os.path.exists(destination_directory):
					os.makedirs(destination_directory)
					os.chmod(destination_directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) # for chmod 777 permission
				
				
				ftp_directory = f"/nwp-data/WRF_NETCDF/{fdate}00/"
				filename_pattern = "WRF3km_INDIA-*.nc"

				print("Connecting to FTP server.")
								
				ftp = ftp_connect(ftp_directory)
				# print("################ IM HERE ###################")

				print("Start file wise downloading FTP server....")
				# for filename in tqdm(ftp.nlst()):
				if filename.startswith('WRF3km_INDIA-') and filename.endswith('.nc'):
					local_filepath = os.path.join(destination_directory, filename)
					# local_filepath = os.path.join(destination_directory)
					with open(local_filepath, 'wb') as local_file:
						print(f"Writing file: {filename} to the directory...")
						ftp.retrbinary(f"RETR {filename}", local_file.write)

				print("Disconnecting from FTP server.")
				ftp.quit()

				spinner.ok("✔")
				print("File Downloaded successfully.")

		except Exception as e:
			spinner.fail("✗")
			print(f"An error occurred: {e}")


	def merge_data(self, fdate, folder_path):
		"""
			##################################################
			### Merge Hourly Steps IMD WRF data 
			##################################################
		"""

		print(" ###### merge data date: ", fdate) 

		try:
			with yaspin(Spinners.dots, text="File Merging...") as spinner:
				# result = subprocess.run(ncks_command, check=True, capture_output=True, text=True)

				file_names = [f for f in os.listdir(folder_path) if f.startswith("WRF3km_INDIA-")]
				file_names.sort()

				# List of file paths
				# WRF3km_INDIA-2024-05-12_00.nc
				# file_names = ["AAA_WRF3km_INDIA-2024-05-12_00.nc", "AAA_WRF3km_INDIA-2024-05-12_01.nc"]  # Add more file paths as needed
				print(" $$$$$$$$ file_names: ", file_names)
				times_list = []
				for file_path in file_names:
					times_list.append(f"{file_path[13:23]} {file_path[24:26]}:00:00")
				print(" ########### times_list: ", times_list)
				times = pd.to_datetime(times_list)
				# times = pd.to_datetime(["2024-05-12 00:00:00", "2024-05-12 01:00:00"])
				# Create an empty list to store datasets
				datasets = []

				##########################################################################
				# Open each file, assign time coordinates, and append to the datasets list
				##########################################################################
				idx = 0
				for file_path in file_names:
					ds = xr.open_dataset(str(folder_path)+str(file_path))
					ds = ds.assign_coords(time=pd.to_datetime(times[idx]))
					datasets.append(ds)
					idx=idx+1

				####################################################
				# Merge the datasets along the new 'time' dimension
				####################################################
				merged_ds = xr.concat(datasets, dim='time')
				
				####################################################
				# Write the merged dataset to a new NetCDF file
				####################################################
				merged_ds.to_netcdf(str(folder_path)+"merged_file.nc")
				# print(" ########## File success fully merged ######### ")

				####################################################
				# Close the datasets
				####################################################
				for ds in datasets:
					ds.close()
				
				
				spinner.ok("✔")
				print("File Merged successfully.") 

				# print(f"Subset created and saved to {dst_file}")
		except subprocess.CalledProcessError as e:
			spinner.fail("✗")
			print(f"An error occurred on File Merging: {e}")
			print("Command Output:", e.stdout)
			print("Command Error:", e.stderr)

	
	def crop_nc_file_for_bd(self, fdate, folder_path):
		"""
			################################################################
			### Crop Merged Hourly Steps IMD WRF data for Bangladesh Only 
			################################################################
		"""


		print(" ###### download_data date: ", fdate) 

		try:
			with yaspin(Spinners.dots, text="File Cropping...") as spinner:
				# result = subprocess.run(ncks_command, check=True, capture_output=True, text=True)
				
		
				# Open the source NetCDF file
				src_file = str(folder_path) + "merged_file.nc"
				dst_file = str(folder_path) + f"{fdate}.nc"

				# Define the latitude and longitude bounds
				lat_min = BD_DETAILS['BD_LAT_MIN']	#22.0
				lat_max = BD_DETAILS['BD_LAT_MAX']	#28.0
				lon_min = BD_DETAILS['BD_LON_MIN']	#86.0
				lon_max = BD_DETAILS['BD_LON_MAX']	#97.0

				# Open the source dataset
				src_ds = nc.Dataset(src_file, 'r')

				# Extract the latitude and longitude variables
				lat = src_ds.variables['lat'][:]
				lon = src_ds.variables['lon'][:]

				# Find the indices that match the desired latitude and longitude ranges
				lat_indices = np.where((lat >= lat_min) & (lat <= lat_max))[0]
				lon_indices = np.where((lon >= lon_min) & (lon <= lon_max))[0]

				# Open a new NetCDF file to store the subset
				dst_ds = nc.Dataset(dst_file, 'w')

				# Copy the dimensions
				for name, dimension in src_ds.dimensions.items():
					if name == 'lat':
						dst_ds.createDimension(name, len(lat_indices))
					elif name == 'lon':
						dst_ds.createDimension(name, len(lon_indices))
					else:
						dst_ds.createDimension(name, len(dimension) if not dimension.isunlimited() else None)

				# Copy the variables
				for name, variable in src_ds.variables.items():
					dst_var = dst_ds.createVariable(name, variable.datatype, variable.dimensions)
					# Copy variable attributes
					dst_var.setncatts({k: variable.getncattr(k) for k in variable.ncattrs()})
					# Copy the variable data, only for the selected latitude and longitude ranges
					if name == 'lat':
						dst_var[:] = lat[lat_indices]
					elif name == 'lon':
						dst_var[:] = lon[lon_indices]
					elif 'lat' in variable.dimensions and 'lon' in variable.dimensions:
						lat_dim = variable.dimensions.index('lat')
						lon_dim = variable.dimensions.index('lon')
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
			name="IMD_WRF_VIS", source_type="vis",
			source_data_type__name="Forecast"
		)[0]
		WRF_NC_LOC_ECMWF_HRES = source_obj.source_path
		
		# folder_path = os.getcwd()
		folder_path = str(ECMWF_BASE_URL)+str(WRF_NC_LOC_ECMWF_HRES)+str(date)+"00/"
		print(" $$$$$$ folder_path: ", folder_path) 

		ftp_directory = f"/nwp-data/WRF_NETCDF/{date}00/"
		print(" $$$$$$ ftp_directory: ", ftp_directory) 
		ftp = ftp_connect(ftp_directory)
		filenames = ftp.nlst()
		ftp.quit()

		# print(" $$$$$$$$$$$$$$$$$$$ my files name: ", filenames)
		# print(" $$$$$$$$$$$$$$$$$$$ my files name type: ", type(filenames))
		# return
		
		# download_args = [(date, folder_path, filenames) for filename in filenames]
		download_args = []
		for filename in filenames:
			download_args.append((date, folder_path, filename))
		# print("##### download_args: ", download_args) 
		# print("##### download_args len: ", len(download_args)) 
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			list(tqdm(executor.map(lambda args: self.download_data(*args), download_args), total=len(download_args)))

		# self.download_data(date, folder_path)
		self.merge_data(date, folder_path)
		self.crop_nc_file_for_bd(date, folder_path)
		


		


