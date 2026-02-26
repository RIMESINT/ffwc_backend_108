'''
Process and insert upazilla specific
weather forecast processed from BMD-WRF9KM model

Note:
	- gust data is being processed form raw gfs forecast
'''

# -*- coding: utf-8 -*-

from hashlib import sha256
# from django.conf import settings
from django.core.management.base import BaseCommand
import json, os, sys, numpy as np, fiona
from datetime import datetime as dt, timedelta as delt 
from pyscissor import scissor 
from netCDF4 import Dataset as nco,num2date
from shapely.geometry import shape
from tqdm import tqdm


import shutil
from collections import defaultdict


from datetime import date as py_date_obj, datetime as dt

from django.conf import settings
# from ffwc_django_project import settings

# import middleware
from app_middlewares.permissions.dir_with_sub_dir_permissions import (
    DirectoryPermission
)

from app_visualization.models import (
	Source, Parameter, ForecastDaily, SystemState,  
	BasinDetails, ForecastSteps, 
)
# from user_authentication.models import (GeoData, GeoLevel)

from ffwc_django_project.project_constant import app_visualization
WRF_NC_LOC_ECMWF_HRES = app_visualization['ecmwf_hres']['WRF_NC_LOC_ECMWF_HRES']
JSON_OUT_LOC_ECMWF_HRES = app_visualization['ecmwf_hres']['JSON_OUT_LOC_ECMWF_HRES']

SOURCE_ECMWF_HRES = app_visualization['source']['ECMWF_HRES_VIS']
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][4]

PROJ_BASE_DIR = settings.BASE_DIR









print(" #################################################################")
print(" ########## delete_old_files_and_data ############################")
print(" #################################################################")
###################################################################
### PRINT CURRENT DATE TIME
###################################################################
curr_date_time = dt.now()
curr_date_time_str = curr_date_time.strftime("%d-%m-%Y %H:%M:%S")
print(" ########################## ", curr_date_time_str, " ##############")










class Command(BaseCommand):
	

	help = '[Generate location Forecast]'
	# USER_OS = 'sajib'
	USER_OS = 'rimes'
	# USER_OS = 'root'


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
	


	def delete_BMDWRF_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting BMD WRF old data ... ")
		print("########################################################")
		print("$$$$$$$$ user of os: ", self.USER_OS)
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR)+"/forecast/bmd_wrf/"       #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/bmd_wrf"
		num_of_file_want_to_delete = num_of_file_want_to_delete		

		print("$$$$$$$$ user of directory: ", directory)

		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
		# DirectoryPermission.directory_all_files_and_folder_permissions_v3(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)
	
		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		files = defaultdict(list)
		for file_name in os.listdir(directory):
			file_path = os.path.join(directory, file_name)
			if os.path.isfile(file_path):
				modified_time = os.path.getmtime(file_path)
				files[modified_time].append(file_path)

		sorted_files = sorted(files.items(), reverse=True)

		if len(sorted_files) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} files in the directory. Nothing to delete."))
			return

		files_to_delete = [file_path for modified_time, file_paths in sorted_files[num_of_file_want_to_delete:] for file_path in file_paths]
		for file_path in files_to_delete:
			os.remove(file_path)
			self.stdout.write(self.style.SUCCESS(f"Deleted file: {file_path}"))
    
		print("########################################################")
		print("##### BMD WRF Data Deleted Successfully. ")
		print("########################################################")
    
    
	def delete_ECMWF_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting ECMWF old data ... ")
		print("########################################################")
		
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR)+"/forecast/ecmwrf_hres/"       #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/ecmwrf_hres"
		num_of_file_want_to_delete = num_of_file_want_to_delete*3		

		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)
	
		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		files = defaultdict(list)
		for file_name in os.listdir(directory):
			file_path = os.path.join(directory, file_name)
			if os.path.isfile(file_path):
				modified_time = os.path.getmtime(file_path)
				files[modified_time].append(file_path)

		sorted_files = sorted(files.items(), reverse=True)

		if len(sorted_files) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} files in the directory. Nothing to delete."))
			return

		files_to_delete = [file_path for modified_time, file_paths in sorted_files[num_of_file_want_to_delete:] for file_path in file_paths]
		for file_path in files_to_delete:
			os.remove(file_path)
			self.stdout.write(self.style.SUCCESS(f"Deleted file: {file_path}"))

		print("########################################################")
		print("##### ECMWF Data Deleted Successfully. ")
		print("########################################################")

	
	def delete_IMD_GFS_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting IMD_GFS old data ... ")
		print("########################################################")
		
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR)+"/forecast/imd_gfs/"       #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/ecmwrf_hres"
		num_of_file_want_to_delete = num_of_file_want_to_delete*3


		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)

		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		files = defaultdict(list)
		for file_name in os.listdir(directory):
			file_path = os.path.join(directory, file_name)
			if os.path.isfile(file_path):
				modified_time = os.path.getmtime(file_path)
				files[modified_time].append(file_path)

		sorted_files = sorted(files.items(), reverse=True)

		if len(sorted_files) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} files in the directory. Nothing to delete."))
			return

		files_to_delete = [file_path for modified_time, file_paths in sorted_files[num_of_file_want_to_delete:] for file_path in file_paths]
		for file_path in files_to_delete:
			os.remove(file_path)
			self.stdout.write(self.style.SUCCESS(f"Deleted file: {file_path}"))

		print("########################################################")
		print("##### IMD_GFS Data Deleted Successfully. ")
		print("########################################################")

	
	def delete_IMD_WRF_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting IMD_WRF old data ... ")
		print("########################################################")
		
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR) + "/forecast/imd_wrf/"	 #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/imd_wrf"
		num_of_file_want_to_delete = num_of_file_want_to_delete


		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)
	
		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		directories = defaultdict(list)
		for dir_name in os.listdir(directory):
			dir_path = os.path.join(directory, dir_name)
			if os.path.isdir(dir_path):
				modified_time = os.path.getmtime(dir_path)
				directories[modified_time].append(dir_path)

		sorted_directories = sorted(directories.items(), reverse=True)

		if len(sorted_directories) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} directories in the directory. Nothing to delete."))
			return

		directories_to_delete = [dir_path for modified_time, dir_paths in sorted_directories[num_of_file_want_to_delete:] for dir_path in dir_paths]
		for dir_path in directories_to_delete:
			try:
				# os.rmdir(dir_path)	# command for delete empty directory
				shutil.rmtree(dir_path)	# command for delete NON Empty directory
				self.stdout.write(self.style.SUCCESS(f"Deleted directory: {dir_path}"))
			except OSError as e:
				self.stdout.write(self.style.ERROR(f"Error deleting directory {dir_path}: {e}"))

		print("########################################################")
		print("##### IMD_WRF Data Deleted Successfully. ")
		print("########################################################")
	
		
	#####################################################
	### OLD RASTER DATA DELETION PART
	#####################################################
	def delete_BMD_WRF_RASTER_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting BMD_WRF RASTER old data ... ")
		print("########################################################")
		
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR) + "/assets/assets/bmd_wrf/forecast_map/"	 #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/cd assets/assets/bmd_wrf/forecast_map/"
		num_of_file_want_to_delete = num_of_file_want_to_delete


		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)
	
		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		directories = defaultdict(list)
		for dir_name in os.listdir(directory):
			dir_path = os.path.join(directory, dir_name)
			if os.path.isdir(dir_path):
				modified_time = os.path.getmtime(dir_path)
				directories[modified_time].append(dir_path)

		sorted_directories = sorted(directories.items(), reverse=True)

		if len(sorted_directories) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} directories in the directory. Nothing to delete."))
			return

		directories_to_delete = [dir_path for modified_time, dir_paths in sorted_directories[num_of_file_want_to_delete:] for dir_path in dir_paths]
		for dir_path in directories_to_delete:
			try:
				# os.rmdir(dir_path)	# command for delete empty directory
				shutil.rmtree(dir_path)	# command for delete NON Empty directory
				self.stdout.write(self.style.SUCCESS(f"Deleted directory: {dir_path}"))
			except OSError as e:
				self.stdout.write(self.style.ERROR(f"Error deleting directory {dir_path}: {e}"))

		print("########################################################")
		print("##### BMD_WRF RASTER Data Deleted Successfully. ")
		print("########################################################")
	
	def delete_ECMWF_RASTER_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting ECMWF HRES RASTER old data ... ")
		print("########################################################")
		
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR) + "/assets/assets/ecmwrf_hres/forecast_map/"	 #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/cd assets/assets/ecmwrf_hres/forecast_map/"
		num_of_file_want_to_delete = num_of_file_want_to_delete


		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)
	
		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		directories = defaultdict(list)
		for dir_name in os.listdir(directory):
			dir_path = os.path.join(directory, dir_name)
			if os.path.isdir(dir_path):
				modified_time = os.path.getmtime(dir_path)
				directories[modified_time].append(dir_path)

		sorted_directories = sorted(directories.items(), reverse=True)

		if len(sorted_directories) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} directories in the directory. Nothing to delete."))
			return

		directories_to_delete = [dir_path for modified_time, dir_paths in sorted_directories[num_of_file_want_to_delete:] for dir_path in dir_paths]
		for dir_path in directories_to_delete:
			try:
				# os.rmdir(dir_path)	# command for delete empty directory
				shutil.rmtree(dir_path)	# command for delete NON Empty directory
				self.stdout.write(self.style.SUCCESS(f"Deleted directory: {dir_path}"))
			except OSError as e:
				self.stdout.write(self.style.ERROR(f"Error deleting directory {dir_path}: {e}"))

		print("########################################################")
		print("##### ECMWF HRES RASTER Data Deleted Successfully. ")
		print("########################################################")
	
	def delete_IMD_GFS_RASTER_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting IMD_GFS RASTER old data ... ")
		print("########################################################")
		
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR) + "/assets/assets/imd_gfs/forecast_map/"	 #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/cd assets/assets/imd_gfs/forecast_map/"
		num_of_file_want_to_delete = num_of_file_want_to_delete


		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)

		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		directories = defaultdict(list)
		for dir_name in os.listdir(directory):
			dir_path = os.path.join(directory, dir_name)
			if os.path.isdir(dir_path):
				modified_time = os.path.getmtime(dir_path)
				directories[modified_time].append(dir_path)

		sorted_directories = sorted(directories.items(), reverse=True)

		if len(sorted_directories) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} directories in the directory. Nothing to delete."))
			return

		directories_to_delete = [dir_path for modified_time, dir_paths in sorted_directories[num_of_file_want_to_delete:] for dir_path in dir_paths]
		for dir_path in directories_to_delete:
			try:
				# os.rmdir(dir_path)	# command for delete empty directory
				shutil.rmtree(dir_path)	# command for delete NON Empty directory
				self.stdout.write(self.style.SUCCESS(f"Deleted directory: {dir_path}"))
			except OSError as e:
				self.stdout.write(self.style.ERROR(f"Error deleting directory {dir_path}: {e}"))

		print("########################################################")
		print("##### IMD_GFS RASTER Data Deleted Successfully. ")
		print("########################################################")
	
	def delete_IMD_WRF_RASTER_old_data(self, num_of_file_want_to_delete):
		print("########################################################")
		print("##### Deleting IMD_WRF RASTER old data ... ")
		print("########################################################")
		
		# directory = kwargs['directory']
		directory = str(PROJ_BASE_DIR) + "/assets/assets/imd_wrf/forecast_map/"	 #"/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/cd assets/assets/imd_wrf/forecast_map/"
		num_of_file_want_to_delete = num_of_file_want_to_delete


		# change directory permission as chmod 777
		DirectoryPermission.directory_all_files_and_folder_permissions_v2(
			directory_path=(directory),
			permission_mode=0o777,
			user_name=self.USER_OS
		)

		if not os.path.isdir(directory):
			self.stdout.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
			return

		directories = defaultdict(list)
		for dir_name in os.listdir(directory):
			dir_path = os.path.join(directory, dir_name)
			if os.path.isdir(dir_path):
				modified_time = os.path.getmtime(dir_path)
				directories[modified_time].append(dir_path)

		sorted_directories = sorted(directories.items(), reverse=True)

		if len(sorted_directories) <= num_of_file_want_to_delete:
			self.stdout.write(self.style.WARNING(f"There are less than {num_of_file_want_to_delete} directories in the directory. Nothing to delete."))
			return

		directories_to_delete = [dir_path for modified_time, dir_paths in sorted_directories[num_of_file_want_to_delete:] for dir_path in dir_paths]
		for dir_path in directories_to_delete:
			try:
				# os.rmdir(dir_path)	# command for delete empty directory
				shutil.rmtree(dir_path)	# command for delete NON Empty directory
				self.stdout.write(self.style.SUCCESS(f"Deleted directory: {dir_path}"))
			except OSError as e:
				self.stdout.write(self.style.ERROR(f"Error deleting directory {dir_path}: {e}"))

		print("########################################################")
		print("##### IMD_WRF RASTER Data Deleted Successfully. ")
		print("########################################################")
	
	

	def main(self, date):

		# path_list = [
		# 	'/home/ffwc/backend/ffwc_django_project/forecast/',
		# 	'/home/ffwc/backend/ffwc_django_project/assets/assets'
		# ]
		# user_name = 'rimes'
		# group_name = 'rimes'
		# for path in path_list:
		# 	DirectoryPermission.recursive_chown_change_ownership( 
		# 		directory_path=path,
		# 		user_name=user_name,
		# 		group_name=group_name
		# 	)
		


		num_of_file_want_to_delete = 7
		#######################################################
		### Deleting old forecast data
		#######################################################
		self.delete_BMDWRF_old_data(num_of_file_want_to_delete)
		self.delete_ECMWF_old_data(num_of_file_want_to_delete)
		self.delete_IMD_GFS_old_data(num_of_file_want_to_delete)
		self.delete_IMD_WRF_old_data(num_of_file_want_to_delete)

		#######################################################
		### Deleting old RASTER data
		#######################################################
		self.delete_BMD_WRF_RASTER_old_data(num_of_file_want_to_delete)
		self.delete_ECMWF_RASTER_old_data(num_of_file_want_to_delete)
		self.delete_IMD_GFS_RASTER_old_data(num_of_file_want_to_delete)
		self.delete_IMD_WRF_RASTER_old_data(num_of_file_want_to_delete)
    
		print("########################################################")
		print("##### All Old Deleted Successfully. ")
		print("########################################################")


		


