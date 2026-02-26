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
from django.db.models import Max
import geojsoncontour as gj 
import mysql.connector as mconn 
import matplotlib.colors as mplcolors

from netCDF4 import Dataset as nco, num2date
from datetime import datetime as dt, timedelta as delt 

from scipy.ndimage import zoom
from tqdm import tqdm

from app_visualization.models import (
    Source, SystemState, FfwcRainfallStation,
	RainfallObservation,
)

from ffwc_django_project.project_constant import app_visualization
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][9]
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


	
			

	def process_imd_stations_ARG_observations(self, fdate, state_list):
		"""
			##################################################
			### Store IMD stations data from web:
			### url: http://aws.imd.gov.in:8091/
			##################################################
		""" 
		
		try:
			with yaspin(Spinners.dots, text="ARG type station details storing...") as spinner:
				
				station_details_list = []
				
				# today_date = dt.now()
				today_date = dt.strptime(fdate, "%Y%m%d").date()
				yesterday = today_date - delt(days=1)
				formatted_date = yesterday.strftime('%Y-%m-%d')  # Date format = YYYYMMDD
				print("formatted_date: ", formatted_date)

				state_list = state_list

				combined_df_rf = None

				for state in state_list:
					obs_url = f"http://aws.imd.gov.in:8091/AWS/dataview.php?a=ARG&b={state}&c=ALL_DISTRICT&d=ALL_STATION&e={formatted_date}&f={formatted_date}&g=ALL_HOUR&h=ALL_MINUTE"
					print("obs_url: ", obs_url)

					tables = pd.read_html(obs_url)
					df_rf = tables[0]

					df_rf = df_rf[[
						'S NO.', 'DISTRICT', 'STATION', 'DATE(YYYY-MM-DD)', 'TIME (UTC)',
						'RAIN FALL CUM. SINCE 0300 UTC (mm)'
					]]
					df_rf.rename(
						columns={
							'DATE(YYYY-MM-DD)': 'DATE',
							'TIME (UTC)': 'TIMESTAMP',
							'RAIN FALL CUM. SINCE 0300 UTC (mm)': 'ACC_RF',
						}, inplace=True
					)
					df_rf['STATE'] = state
					df_rf['NETWORK'] = "ARG"

					# df_rf.sort_values(by=['STATION', 'DATE(YYYY-MM-DD)', 'TIME (UTC)'], inplace=True)
					# print("total row of DF: ", df_rf.shape[0])
					# print(" ####################################### ")

					combined_df_rf = pd.concat([combined_df_rf, df_rf], axis=0)

				# print("total row o/f combined_df_rf: ", combined_df_rf.shape[0])
				combined_df_rf.sort_values(
					by=['STATION', 'DATE', 'TIMESTAMP'],
					ascending=[True, True, True], inplace=True
				)
				print("total row of combined_df_rf: ", combined_df_rf.shape[0])
				# combined_df_rf.head(10)
				# return

				x = 1
				for row in combined_df_rf.itertuples():
					max_rf_id = RainfallObservation.objects.aggregate(
						Max('rf_id')
					)['rf_id__max']
					print("max_rf_id: ", max_rf_id)

					st_obj = FfwcRainfallStation.objects.filter(
						name=row.STATION, 
						observe_data_source_network=row.NETWORK
					)
					if len(st_obj) == 0:
						continue
					else:
						st_obj = FfwcRainfallStation.objects.filter(
							name=row.STATION, 
							observe_data_source_network=row.NETWORK
						)[0]

					datetime_string = f"{row.DATE} {row.TIMESTAMP}"
					rf_date = dt.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")

					rf_obs_insert = RainfallObservation(
						rf_id = int(max_rf_id)+1,
						st=st_obj,  
						rf_date=rf_date,  
						rainFall=row.ACC_RF 
					)
					rf_obs_insert.save()

					# Do something with the extracted values
					print(f"STATION: {st_obj.id}:{st_obj.name} | DATETIME: {rf_date} | rainFall: {row.ACC_RF}")
					# x=x+1
					# if x >5:
					# 	break

				spinner.ok("✔")
				print("ARG Stations data stored successfully.")
		except Exception as e:
			spinner.fail("✗")
			print(f"An error occurred: {e}")


	def process_imd_stations_AWS_observations(self, fdate, state_list):
			"""
				##################################################
				### Store IMD stations data from web:
				### url: http://aws.imd.gov.in:8091/
				##################################################
			""" 
			
			try:
				with yaspin(Spinners.dots, text="ARG type station details storing...") as spinner:
					
					station_details_list = []
					
					# today_date = dt.now()
					today_date = dt.strptime(fdate, "%Y%m%d").date()
					yesterday = today_date - delt(days=1)
					formatted_date = yesterday.strftime('%Y-%m-%d')  # Date format = YYYYMMDD
					print("formatted_date: ", formatted_date)

					state_list = state_list

					combined_df_rf = None

					for state in state_list:
						obs_url = f"http://aws.imd.gov.in:8091/AWS/dataview.php?a=AWS&b={state}&c=ALL_DISTRICT&d=ALL_STATION&e={formatted_date}&f={formatted_date}&g=ALL_HOUR&h=ALL_MINUTE"
						print("obs_url: ", obs_url)

						tables = pd.read_html(obs_url)
						df_rf = tables[0]

						df_rf = df_rf[[
							'S NO.', 'DISTRICT', 'STATION', 'DATE(YYYY-MM-DD)', 'TIME (UTC)',
							'RAIN FALL CUM. SINCE 0300 UTC (mm)'
						]]
						df_rf.rename(
							columns={
								'DATE(YYYY-MM-DD)': 'DATE',
								'TIME (UTC)': 'TIMESTAMP',
								'RAIN FALL CUM. SINCE 0300 UTC (mm)': 'ACC_RF',
							}, inplace=True
						)
						df_rf['STATE'] = state
						df_rf['NETWORK'] = "AWS"

						# df_rf.sort_values(by=['STATION', 'DATE(YYYY-MM-DD)', 'TIME (UTC)'], inplace=True)
						# print("total row of DF: ", df_rf.shape[0])
						# print(" ####################################### ")

						combined_df_rf = pd.concat([combined_df_rf, df_rf], axis=0)

					# print("total row o/f combined_df_rf: ", combined_df_rf.shape[0])
					combined_df_rf.sort_values(
						by=['STATION', 'DATE', 'TIMESTAMP'],
						ascending=[True, True, True], inplace=True
					)
					print("total row of combined_df_rf: ", combined_df_rf.shape[0])
					print(combined_df_rf.head(10))
					# return

					x = 1
					for row in combined_df_rf.itertuples():
						max_rf_id = RainfallObservation.objects.aggregate(
							Max('rf_id')
						)['rf_id__max']
						print("max_rf_id: ", max_rf_id)

						st_obj = FfwcRainfallStation.objects.filter(
							name=row.STATION, 
							observe_data_source_network=row.NETWORK
						)
						if len(st_obj) == 0:
							continue
						else:
							st_obj = FfwcRainfallStation.objects.filter(
								name=row.STATION, 
								observe_data_source_network=row.NETWORK
							)[0]

						print("max_rf_id: ", max_rf_id)


						datetime_string = f"{row.DATE} {row.TIMESTAMP}"
						rf_date = dt.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")

						rf_obs_insert = RainfallObservation(
							rf_id = int(max_rf_id)+1,
							st=st_obj,  
							rf_date=rf_date,  
							rainFall=row.ACC_RF 
						)
						rf_obs_insert.save()

						# Do something with the extracted values
						print(f"STATION: {st_obj.id}:{st_obj.name} | DATETIME: {rf_date} | rainFall: {row.ACC_RF}")
						# x=x+1
						# if x >5:
						# 	break

					spinner.ok("✔")
					print("AWS Stations data stored successfully.")
			except Exception as e:
				spinner.fail("✗")
				print(f"An error occurred: {e}")


	def process_imd_stations_AGRO_observations(self, fdate, state_list):
			"""
				##################################################
				### Store IMD stations data from web:
				### url: http://aws.imd.gov.in:8091/
				##################################################
			""" 
			
			try:
				with yaspin(Spinners.dots, text="ARG type station details storing...") as spinner:
					
					station_details_list = []
					
					# today_date = dt.now()
					today_date = dt.strptime(fdate, "%Y%m%d").date()
					yesterday = today_date - delt(days=1)
					formatted_date = yesterday.strftime('%Y-%m-%d')  # Date format = YYYYMMDD
					print("formatted_date: ", formatted_date)

					state_list = state_list

					combined_df_rf = None

					for state in state_list:
						obs_url = f"http://aws.imd.gov.in:8091/AWS/dataview.php?a=AGRO&b={state}&c=ALL_DISTRICT&d=ALL_STATION&e={formatted_date}&f={formatted_date}&g=ALL_HOUR&h=ALL_MINUTE"
						print("obs_url: ", obs_url)

						tables = pd.read_html(obs_url)
						df_rf = tables[0]

						df_rf = df_rf[[
							'S NO.', 'DISTRICT', 'STATION', 'DATE(YYYY-MM-DD)', 'TIME (UTC)',
							'RAIN FALL CUM. SINCE 0300 UTC (mm)'
						]]
						df_rf.rename(
							columns={
								'DATE(YYYY-MM-DD)': 'DATE',
								'TIME (UTC)': 'TIMESTAMP',
								'RAIN FALL CUM. SINCE 0300 UTC (mm)': 'ACC_RF',
							}, inplace=True
						)
						df_rf['STATE'] = state
						df_rf['NETWORK'] = "AGRO"

						# df_rf.sort_values(by=['STATION', 'DATE(YYYY-MM-DD)', 'TIME (UTC)'], inplace=True)
						# print("total row of DF: ", df_rf.shape[0])
						# print(" ####################################### ")

						combined_df_rf = pd.concat([combined_df_rf, df_rf], axis=0)

					# print("total row o/f combined_df_rf: ", combined_df_rf.shape[0])
					combined_df_rf.sort_values(
						by=['STATION', 'DATE', 'TIMESTAMP'],
						ascending=[True, True, True], inplace=True
					)
					print("total row of combined_df_rf: ", combined_df_rf.shape[0])
					print(combined_df_rf.head(10))
					# return

					x = 1
					for row in combined_df_rf.itertuples():
						max_rf_id = RainfallObservation.objects.aggregate(
							Max('rf_id')
						)['rf_id__max']
						print("max_rf_id: ", max_rf_id)

						st_obj = FfwcRainfallStation.objects.filter(
							name=row.STATION, 
							observe_data_source_network=row.NETWORK
						)
						if len(st_obj) == 0:
							continue
						else:
							st_obj = FfwcRainfallStation.objects.filter(
								name=row.STATION, 
								observe_data_source_network=row.NETWORK
							)[0]


						datetime_string = f"{row.DATE} {row.TIMESTAMP}"
						rf_date = dt.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")

						rf_obs_insert = RainfallObservation(
							rf_id = int(max_rf_id)+1,
							st=st_obj,  
							rf_date=rf_date,  
							rainFall=row.ACC_RF 
						)
						rf_obs_insert.save()

						# Do something with the extracted values
						print(f"STATION: {st_obj.id}:{st_obj.name} | DATETIME: {rf_date} | rainFall: {row.ACC_RF}")
						# x=x+1
						# if x >5:
						# 	break

					spinner.ok("✔")
					print("AGRO Stations data stored successfully.")
			except Exception as e:
				spinner.fail("✗")
				print(f"An error occurred: {e}")

	
	def update_state(self, forecast_date, source_obj):
		"""
			Update system state
		"""

		if SystemState.objects.filter(source=source_obj.id, name=SYSTEM_STATE_NAME_ECMWF_HRES).count()==0:
			print('State dosent exists. Creating..')
			SystemState(source=source_obj,last_update=forecast_date, name=SYSTEM_STATE_NAME_ECMWF_HRES).save()	
		else:
			print('State exists. updating..')
			update_state = SystemState.objects.get(source=source_obj, name=SYSTEM_STATE_NAME_ECMWF_HRES)
			update_state.last_update=forecast_date
			update_state.save()
			
	
	def main(self, date):

		source_obj = Source.objects.filter(
			name="IMD_OBS",
			source_type="location_specific",
			source_data_type__name="Observed"
		)[0]

		state_list = ["MEGHALAYA", "ASSAM", "TRIPURA", "WEST_BENGAL"]

		self.process_imd_stations_ARG_observations(date, state_list) 
		self.process_imd_stations_AWS_observations(date, state_list) 
		self.process_imd_stations_AGRO_observations(date, state_list)
		
		# update state
		date_obj = dt.strptime(date, '%Y%m%d')
		self.update_state(date_obj, source_obj)
		


		


