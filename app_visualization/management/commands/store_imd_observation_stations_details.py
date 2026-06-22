# management/commands/generate_forecast_data.py

import os
import ftplib 
import stat
import requests

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
    RainfallObservationIMDAWSStates, RainfallObservationIMDAWSDistricts,
    FfwcIMDRFObservationStationNetwork,
    FfwcIMDRFObservationStation,
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


	def collect_all_types_of_valid_stations_with_state_district(self):
			"""
				##################################################
				### Store IMD stations data from web:
				### url: http://aws.imd.gov.in:8091/
				##################################################
			""" 
			url_count = 1
			fin_stations_list = []

			try:
				with yaspin(Spinners.dots, text="AWS type station details storing...") as spinner:
					observe_data_source = Source.objects.filter(
						name= "IMD_OBS",
						source_type= "location_specific",
					)[0]					

					network_obj = FfwcIMDRFObservationStationNetwork.objects.filter(
						is_active = 1,
						# name = "AWS",
					)			

					for network in network_obj:
						state_obj = RainfallObservationIMDAWSStates.objects.filter(
							status=1,
						)
						for state in state_obj:
							
							dist_obj = RainfallObservationIMDAWSDistricts.objects.filter(
								imd_aws_states__id= state.id
							)
							for dist in dist_obj:
        
								# url = f"http://aws.imd.gov.in:8091/AWS/tabularstat.php?types=AGRO&states=ASSAM&disc=BAKSA"
								# url = f"http://aws.imd.gov.in:8091/AWS/tabularstat.php?types=AWS&states=ASSAM&disc=BAKSA"
								url = f"http://aws.imd.gov.in:8091/AWS/tabularstat.php?types={network.name}&states={state.name}&disc={dist.name}"
								print(f" $$$$$$$ {url_count} url: ", url)
								url_count=url_count+1

								response = requests.get(url)

								if response.status_code == 200:
									json_data = response.json()
									data_list = json_data.get("data", [])
									print("Data:", data_list)
									print("Data type:", type(data_list))
									for station in data_list:
										fin_stations_list.append(station)

										if (len(FfwcIMDRFObservationStation.objects.filter(
											name=station,
											district= dist.id,
											division= state.id,
										))==0):
											station_create = FfwcIMDRFObservationStation(
												name= station,
												district= dist.id,
												division= state.id,
												observe_data_source= observe_data_source,
												observe_data_source_network= network,
											)
											station_create.save()
										else:
											print(f"{station} is already inserted, so new insertion is skipping...")
								else:
									print("Failed to retrieve data. Status code:", response.status_code)
        
					print(" fin_stations_list: ", fin_stations_list)
					print(" fin_stations_list len: ", len(fin_stations_list))
					spinner.ok("✔")
					print("All Stations details stored successfully.")
			except Exception as e:
				spinner.fail("✗")
				print(f"An error occurred: {e}")


	def store_imd_all_networks_stations_details(self):
			"""
				##################################################
				### Store IMD stations data from web:
				### url: http://aws.imd.gov.in:8091/
				##################################################
			""" 
			
			try:
				with yaspin(Spinners.dots, text="Stations lat lon alt updating... \n") as spinner:
					
					network_obj = FfwcIMDRFObservationStationNetwork.objects.filter(
						is_active = 1,
						# name = "AWS",
					)		
					aws_columns = [
						'S NO.', 'STATE', 'DISTRICT', 'STATION', 
						'LATITUDE', 'LONGITUDE', 'ALTITUDE'
					]
					arg_columns = [
						'S NO.', 'STATE', 'DISTRICT', 'STATION', 
						'LATITUDE', 'LONGITUDE'
					]
					agro_columns = [
						'S NO.', 'STATE', 'DISTRICT', 'STATION', 
						'LATITUDE', 'LONGITUDE', 'ALTITUDE'
					]
    
    
					for network in network_obj:
						print(f"#################################################")
						print(f"Station: {network.name} is updating")
						print(f"#################################################")

						url = f"http://aws.imd.gov.in:8091/AWS/networkmeta.php?a={network.name}&b=ALL_STATE" 
						# url = f"http://aws.imd.gov.in:8091/AWS/networkmeta.php?a=AGRO&b=ALL_STATE" 
						# for ARG = http://aws.imd.gov.in:8091/AWS/networkmeta.php?a=ARG&b=ALL_STATE
						# for AGRO = http://aws.imd.gov.in:8091/AWS/networkmeta.php?a=AGRO&b=ALL_STATE

						tables = pd.read_html(url)
						df = tables[0]
						if network.name == "AWS":
							df.columns = aws_columns
						if network.name == "AGRO":
							df.columns = agro_columns
						elif network.name == "ARG":
							df.columns = arg_columns
						# df.head(10)

						print("total row of DF: ", df.shape[0])
						distinct_stations = df['STATION'].nunique()
						print("Distinct stations:", distinct_stations)
						print(" ####################################### ")

						df = df.drop_duplicates(subset='STATION')
						print("total row of DF: ", df.shape[0])
						distinct_stations = df['STATION'].nunique()
						print("Distinct stations:", distinct_stations)

						filtered_df = df[df['STATE'].isin(["MEGHALAYA", "ASSAM", "TRIPURA", "WEST_BENGAL"])]
						# print("total row of filtered_df: ", filtered_df.shape[0])
						# filtered_df

						filtered_df = filtered_df.sort_values(by='STATION')
						# filtered_df

						print("total row of DF: ", filtered_df.shape[0])
						filtered_distinct_stations = filtered_df['STATION'].nunique()
						print("Distinct stations:", filtered_distinct_stations) 

						for row in filtered_df.itertuples():
							states_obj = RainfallObservationIMDAWSStates.objects.filter(
								name=str(row.STATE).strip(),   
							)
							dist_obj = RainfallObservationIMDAWSDistricts.objects.filter(
								name=str(row.DISTRICT).strip(),   
							)
		
							if (len(states_obj)==1 and len(dist_obj)==1):
								states_obj = states_obj[0]
								dist_obj = dist_obj[0]
		
								station_obj = FfwcIMDRFObservationStation.objects.filter(
									name=str(row.STATION).strip(), 
									district=dist_obj.id, 
									division=states_obj.id, 
								)
								print("station_obj len:", len(station_obj)) 
			
								if len(station_obj)>0:
									station_obj = station_obj[0]

									if network.name == "AWS":
										FfwcIMDRFObservationStation.objects.filter(pk=station_obj.id).update(
											lat=str(row.LATITUDE).strip(),
											long=str(row.LONGITUDE).strip(),
											altitude=str(row.ALTITUDE).strip(),
										)
									elif network.name == "AGRO":
										FfwcIMDRFObservationStation.objects.filter(pk=station_obj.id).update(
											lat=str(row.LATITUDE).strip(),
											long=str(row.LONGITUDE).strip(),
											altitude=str(row.ALTITUDE).strip(),
										)
									elif network.name == "ARG":
										FfwcIMDRFObservationStation.objects.filter(pk=station_obj.id).update(
											lat=str(row.LATITUDE).strip(),
											long=str(row.LONGITUDE).strip(), 
										)

									# Do something with the extracted values
									print(f"STATION: {row.STATION} | STATE: {row.STATE} | DISTRICT: {row.DISTRICT} | LATITUDE: {row.LATITUDE} | LONGITUDE: {row.LONGITUDE} is updated")
								else:
									print(f"STATION: {row.STATION} | STATE: {row.STATE} | DISTRICT: {row.DISTRICT} is not available in our database")
							else:
								print(f"{row.STATE} or {row.DISTRICT} is not available in our database")
					spinner.ok("✔")
					print("AWS Stations details Updated successfully.")
			except Exception as e:
				spinner.fail("✗")
				print(f"An error occurred: {e}")


	def main(self, date):

		# self.collect_all_types_of_valid_stations_with_state_district()    
		self.store_imd_all_networks_stations_details()    
		


		


