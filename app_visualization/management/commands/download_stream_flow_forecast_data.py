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
    Source, SystemState, StreamFlowStation
)

from ffwc_django_project.project_constant import app_visualization
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][20]
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
			formatted_date = today_date.strftime('%Y%m%d')  # Date format = YYYYMMDD
			print("formatted_date: ", formatted_date)
			fcst_date = formatted_date
		
		# fcst_date = '20230516'
		self.main(fcst_date)


	
			

	def download_data(self, fdate, folder_path, SF_FTP_DIR, SF_ST_FILE_LIST):
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

				FTP_CONF = env_['bdserver_site_235_ssh_conf']
				
				ftp_host = FTP_CONF["HOST"]
				ftp_user = FTP_CONF["USER"]
				ftp_password = FTP_CONF["PASSWORD"]
				
				
				for file_name in SF_ST_FILE_LIST:
        
					# remote_file_path = f"/dataex-nc-cache/ecmwf-hres/{fdate}.nc"
					remote_file_path = str(SF_FTP_DIR)+str(file_name)
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
					print(f"{file_name} Downloaded successfully.")
			return True
		except Exception as e:
			spinner.fail("✗")
			print(f"An error occurred: {e}")
			return False
		finally:
			ssh.close()
			print("Disconnecting from SSH server.")
			# return False

	def update_state(self,forecast_date,source_obj):
		# update system state

		if SystemState.objects.filter(source=source_obj.id, name=SYSTEM_STATE_NAME_ECMWF_HRES).count()==0:
			print('State dosent exists. Creating..')
			SystemState(source=source_obj,last_update=forecast_date, name=SYSTEM_STATE_NAME_ECMWF_HRES).save()	
		else:
			print('State exists. updating..')
			update_state = SystemState.objects.get(source=source_obj, name=SYSTEM_STATE_NAME_ECMWF_HRES)
			update_state.last_update=forecast_date
			update_state.save()
    

	def main(self, date):

		SF_ST_FILE_LIST = []
		forecast_date = dt.strptime(date,'%Y%m%d').strftime('%Y-%m-%d')

		source_obj = Source.objects.filter(
			name="FFWC_STREAM_FLOW_FORCAST", source_type="location_specific",
			source_data_type__name="Forecast"
		)[0]
		WRF_NC_LOC_ECMWF_HRES = source_obj.destination_path
		SF_FTP_DIR = source_obj.source_path 
		
		# folder_path = os.getcwd()
		folder_path = str(ECMWF_BASE_URL)+str(WRF_NC_LOC_ECMWF_HRES)
		print(" $$$$$$ folder_path: ", folder_path) 
    
		sf_station_obj = StreamFlowStation.objects.all()
		# today_date = dt.now().strftime('%Y%m%d')
		today_date = date
		# print("today_date: ", today_date)
		# print("today_date type: ", type(today_date))
    
		for station in sf_station_obj:
			csv_file_name_date_obj = dt.strptime(today_date,'%Y%m%d')
			sf_st_file_name = csv_file_name_date_obj.strftime(station.file_name)
			SF_ST_FILE_LIST.append(sf_st_file_name)
    
		print("SF_ST_FILE_LIST: ", SF_ST_FILE_LIST) 
		# return

		
		download_data = self.download_data(date, folder_path, SF_FTP_DIR, SF_ST_FILE_LIST)
		if download_data == True:
			self.update_state(forecast_date, source_obj)  
		


		


