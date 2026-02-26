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

from app_visualization.models import (
    Source, SystemState, FfwcRainfallStation,
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
			formatted_date = today_date.strftime('%Y%m%d')  # Date format = YYYYMMDD
			print("formatted_date: ", formatted_date)
			fcst_date = formatted_date
		
		# fcst_date = '20230516'
		self.main(fcst_date)


	
			

	def store_imd_stations_ARG_details(self):
		"""
			##################################################
			### Store IMD stations data from web:
			### url: http://aws.imd.gov.in:8091/
			##################################################
		""" 
		
		try:
			with yaspin(Spinners.dots, text="ARG type station details storing...") as spinner:
				
				station_details_list = []
				
				url = "http://aws.imd.gov.in:8091/AWS/networkmeta.php?a=ARG&b=ALL_STATE"

				tables = pd.read_html(url)
				df = tables[0]
				df.columns = [
					'S NO.', 'STATE', 'DISTRICT', 'STATION', 
					'LATITUDE', 'LONGITUDE'
				]
				# df.head(10)

				print("total row of DF: ", df.shape[0])
				distinct_stations = df['STATION'].nunique()
				print("Distinct stations:", distinct_stations)
				print(" ####################################### ")

				df = df.drop_duplicates(subset='STATION')
				print("total row of DF: ", df.shape[0])
				distinct_stations = df['STATION'].nunique()
				print("Distinct stations:", distinct_stations)

				filtered_df = df[df['STATE'].isin(["WEST_BENGAL"])]
				# print("total row of filtered_df: ", filtered_df.shape[0])
				# filtered_df

				filtered_df = filtered_df.sort_values(by='STATION')
				# filtered_df

				print("total row of DF: ", filtered_df.shape[0])
				filtered_distinct_stations = filtered_df['STATION'].nunique()
				print("Distinct stations:", filtered_distinct_stations)
				# return

				for row in filtered_df.itertuples():
					source_obj = Source.objects.filter(
						name="IMD_OBS", source_type="location_specific",
						source_data_type__name="Observed"
					)[0]

					station_details_list.append(FfwcRainfallStation.objects.create(
						name=str(row.STATION),  
						basin=None,  
						division=str(row.STATE),  
						district=str(row.DISTRICT),  
						upazilla=None,  
						lat=str(row.LATITUDE),  
						long=str(row.LONGITUDE),  
						altitude=None, 
						status=1,  
						unit='mm',  
						observe_data_source=source_obj,
						observe_data_source_network='ARG', 
						basin_details=None
					))

					# Do something with the extracted values
					print(f"STATION: {row.STATION} | STATE: {row.STATE} | DISTRICT: {row.DISTRICT} | LATITUDE: {row.LATITUDE} | LONGITUDE: {row.LONGITUDE}")
				# insert to database for this shapefile of all days forecast
				FfwcRainfallStation.objects.bulk_create(station_details_list)

				spinner.ok("✔")
				print("ARG Stations details stored successfully.")
		except Exception as e:
			spinner.fail("✗")
			print(f"An error occurred: {e}")


	def store_imd_stations_AWS_details(self):
			"""
				##################################################
				### Store IMD stations data from web:
				### url: http://aws.imd.gov.in:8091/
				##################################################
			""" 
			
			try:
				with yaspin(Spinners.dots, text="AWS type station details storing...") as spinner:
					
					station_details_list = []
					
					url = "http://aws.imd.gov.in:8091/AWS/networkmeta.php?a=AWS&b=ALL_STATE"

					tables = pd.read_html(url)
					df = tables[0]
					df.columns = [
						'S NO.', 'STATE', 'DISTRICT', 'STATION', 
						'LATITUDE', 'LONGITUDE', 'ALTITUDE'
					]
					# df.head(10)

					print("total row of DF: ", df.shape[0])
					distinct_stations = df['STATION'].nunique()
					print("Distinct stations:", distinct_stations)
					print(" ####################################### ")

					df = df.drop_duplicates(subset='STATION')
					print("total row of DF: ", df.shape[0])
					distinct_stations = df['STATION'].nunique()
					print("Distinct stations:", distinct_stations)

					filtered_df = df[df['STATE'].isin(["WEST_BENGAL"])]
					# print("total row of filtered_df: ", filtered_df.shape[0])
					# filtered_df

					filtered_df = filtered_df.sort_values(by='STATION')
					# filtered_df

					print("total row of DF: ", filtered_df.shape[0])
					filtered_distinct_stations = filtered_df['STATION'].nunique()
					print("Distinct stations:", filtered_distinct_stations)
					# return

					for row in filtered_df.itertuples():
						source_obj = Source.objects.filter(
							name="IMD_OBS", source_type="location_specific",
							source_data_type__name="Observed"
						)[0]

						station_details_list.append(FfwcRainfallStation.objects.create(
							name=str(row.STATION),  
							basin=None,  
							division=str(row.STATE),  
							district=str(row.DISTRICT),  
							upazilla=None,  
							lat=str(row.LATITUDE),  
							long=str(row.LONGITUDE),  
							altitude=str(row.ALTITUDE), 
							status=1,  
							unit='mm',  
							observe_data_source=source_obj,
							observe_data_source_network='AWS', 
							basin_details=None
						))

						# Do something with the extracted values
						print(f"STATION: {row.STATION} | STATE: {row.STATE} | DISTRICT: {row.DISTRICT} | LATITUDE: {row.LATITUDE} | LONGITUDE: {row.LONGITUDE}")
					# insert to database for this shapefile of all days forecast
					FfwcRainfallStation.objects.bulk_create(station_details_list)

					spinner.ok("✔")
					print("AWS Stations details stored successfully.")
			except Exception as e:
				spinner.fail("✗")
				print(f"An error occurred: {e}")


	def store_imd_stations_AGRO_details(self):
			"""
				##################################################
				### Store IMD stations data from web:
				### url: http://aws.imd.gov.in:8091/
				##################################################
			""" 
			
			try:
				with yaspin(Spinners.dots, text="AWS type station details storing...") as spinner:
					
					station_details_list = []
					
					url = "http://aws.imd.gov.in:8091/AWS/networkmeta.php?a=AGRO&b=ALL_STATE"

					tables = pd.read_html(url)
					df = tables[0]
					df.columns = [
						'S NO.', 'STATE', 'DISTRICT', 'STATION', 
						'LATITUDE', 'LONGITUDE', 'ALTITUDE'
					]
					# df.head(10) 

					print("total row of DF: ", df.shape[0])
					distinct_stations = df['STATION'].nunique()
					print("Distinct stations:", distinct_stations)
					print(" ####################################### ")

					df = df.drop_duplicates(subset='STATION')
					print("total row of DF: ", df.shape[0])
					distinct_stations = df['STATION'].nunique()
					print("Distinct stations:", distinct_stations)

					filtered_df = df[df['STATE'].isin(["WEST_BENGAL"])]
					# print("total row of filtered_df: ", filtered_df.shape[0])
					# filtered_df

					filtered_df = filtered_df.sort_values(by='STATION')
					# filtered_df

					print("total row of DF: ", filtered_df.shape[0])
					filtered_distinct_stations = filtered_df['STATION'].nunique()
					print("Distinct stations:", filtered_distinct_stations)
					# return

					for row in filtered_df.itertuples():
						source_obj = Source.objects.filter(
							name="IMD_OBS", source_type="location_specific",
							source_data_type__name="Observed"
						)[0]

						station_details_list.append(FfwcRainfallStation.objects.create(
							name=str(row.STATION),  
							basin=None,  
							division=str(row.STATE),  
							district=str(row.DISTRICT),  
							upazilla=None,  
							lat=str(row.LATITUDE),  
							long=str(row.LONGITUDE),  
							altitude=str(row.ALTITUDE), 
							status=1,  
							unit='mm',  
							observe_data_source=source_obj,
							observe_data_source_network='AGRO', 
							basin_details=None
						))

						# Do something with the extracted values
						print(f"STATION: {row.STATION} | STATE: {row.STATE} | DISTRICT: {row.DISTRICT} | LATITUDE: {row.LATITUDE} | LONGITUDE: {row.LONGITUDE}")
					# insert to database for this shapefile of all days forecast
					FfwcRainfallStation.objects.bulk_create(station_details_list)

					spinner.ok("✔")
					print("AGRO Stations details stored successfully.")
			except Exception as e:
				spinner.fail("✗")
				print(f"An error occurred: {e}")

	def main(self, date):

		self.store_imd_stations_ARG_details() 
		self.store_imd_stations_AWS_details() 
		self.store_imd_stations_AGRO_details()
		


		


