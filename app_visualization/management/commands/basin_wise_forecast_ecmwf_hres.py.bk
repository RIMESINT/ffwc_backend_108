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

from datetime import date as py_date_obj, datetime as dt

from django.conf import settings
# from ffwc_django_project import settings

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

BMDWRF_BASE_URL = settings.BASE_DIR









print(" #################################################################")
print(" ########## level_wise_forecast_ecmwf ############################")
print(" #################################################################")
###################################################################
### PRINT CURRENT DATE TIME
###################################################################
curr_date_time = dt.now()
curr_date_time_str = curr_date_time.strftime("%d-%m-%Y %H:%M:%S")
print(" ########################## ", curr_date_time_str, " ##############")













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
	


	def gen_upazila_forecast(
		self, forecast_date, source_obj, 
		ncf, file_path, basin_details ):
		# print('Forecast Date',forecast_date)

		# sf_loc = os.path.join(settings.BASE_DIR,settings.SHP_DIR,'bd_adm_l3_boundary.topo.zip')


		# shf = fiona.open(f'zip://{sf_loc}')
		shf = fiona.open(file_path, 'r') 

		# get nc data		
		lats = ncf.variables['lat'][:]
		lons = ncf.variables['lon'][:]
		times = ncf.variables['time']
		dates = num2date(times[:],times.units,times.calendar)
		

		rf      = (ncf.variables['tp'][:])*1000
		# rf      = (ncf.variables['lsp'][:] + ncf.variables['cp'][:])*1000
		# temp    = ncf.variables['t2m'][:] - 273.15     # K => C conversion
		
		# windspd = np.sqrt(
		# 		np.square(ncf.variables['u10'][:]) + np.square(ncf.variables['u10'][:])
		# 	)* 3.6      # m/s => kmph conversion
		
		# tempdew = ncf.variables['d2m'][:] - 273.15
		# rh = 100 - 5* (temp-tempdew)
		
		# THI = 0.8 * t_db + RH * (t_tdb − 14.4) + 46.4
		# thi     = 0.8*temp + (rh/100)*(temp-14.4) + 46.4


		# get object form db
		rf_obj       = Parameter.objects.get(name='rf')
		# temp_obj     = Parameter.objects.get(name='temp')
		# tmax_obj     = Parameter.objects.get(name='tmax')
		# tmin_obj     = Parameter.objects.get(name='tmin')
		# rh_obj       = Parameter.objects.get(name='rh')
		# windspd_obj  = Parameter.objects.get(name='windspd')
		# tempdew_obj  = Parameter.objects.get(name='tempdew')
		# thi_obj		 = Parameter.objects.get(name='thi')
		# et0_param_obj = Parameter.objects.get(name='et0')

		# print("et0_param_obj: ", et0_param_obj.name, " === ", et0_param_obj.full_name)

		###############################################################################
		### START Store ET0 part
		#############################################################################
		# et0_list = et0_ncf.variables['et0'][:]
	
		
		
		# iterate through upazillas
		for idx, i_shape in enumerate(tqdm(shf)):

			# print(f"Processing for {idx}:{i_shape['properties']['ADM3_EN']}")
			
			upazila_data_daily = []
			# upazila_data_steps = []

			shape_obj   = shape(i_shape['geometry'])
			# print(" ##################### shape_obj: ", shape_obj)
			

			pys         = scissor(shape_obj, lats, lons)
			weight_grid = pys.get_masked_weight() 

			# [iterate thorugh all days]
			for day in range(10):
				
				day_start_idx       = (day)*1
				day_end_idx         = (day+1)*1
				
				
				day_start      = dates[day_start_idx].strftime('%Y-%m-%d %M:%H')
				day_end        = dates[day_end_idx].strftime('%Y-%m-%d %M:%H')
    
				# et0_list_day   = et0_list[day:day+1, :, :]

				if day==0:
					rf_day          = rf[day_end_idx,:,:]
				else:
					rf_day          = rf[day_end_idx,:,:] - rf[day_start_idx,:,:]
				
				# temp_max_day     = np.amax(temp[day_start_idx:day_end_idx+1,:,:],axis=0)
				# temp_min_day     = np.amin(temp[day_start_idx:day_end_idx+1,:,:],axis=0)
				# temp_avg_day     = np.average(temp[day_start_idx:day_end_idx+1,:,:],axis=0)

				# rh_max_day       = np.amax(rh[day_start_idx:day_end_idx+1,:,:],axis=0)
				# rh_min_day       = np.amin(rh[day_start_idx:day_end_idx+1,:,:],axis=0)
				# rh_avg_day       = np.average(rh[day_start_idx:day_end_idx+1,:,:],axis=0)

				# windspd_max_day  = np.amax(windspd[day_start_idx:day_end_idx+1,:,:],axis=0)
				# windspd_min_day  = np.amin(windspd[day_start_idx:day_end_idx+1,:,:],axis=0)
				# windspd_avg_day  = np.average(windspd[day_start_idx:day_end_idx+1,:,:],axis=0)

				# tempdew_max_day  = np.amax(tempdew[day_start_idx:day_end_idx+1,:,:],axis=0)
				# tempdew_min_day  = np.amin(tempdew[day_start_idx:day_end_idx+1,:,:],axis=0)
				# tempdew_avg_day  = np.average(tempdew[day_start_idx:day_end_idx+1,:,:],axis=0)

				
				# # calculate them from upazilla extracted values
				# # temperature humidity index
				# thi_max_day =  np.amax(thi[day_start_idx:day_end_idx+1,:,:],axis=0)
				# thi_min_day =  np.amin(thi[day_start_idx:day_end_idx+1,:,:],axis=0)
				# thi_avg_day =  np.average(thi[day_start_idx:day_end_idx+1,:,:],axis=0)
    
    
				# # et0
				# et0_list_day_masked = np.ma.masked_array(et0_list_day, mask=weight_grid.mask)
				# et0_list_day_min_val    = et0_list_day_masked.min() 
				# et0_list_day_max_val    = et0_list_day_masked.max() 
				# et0_list_day_avg_val    = et0_list_day_masked.mean()
				
				# upazila_data_daily.append(ForecastDaily(
				# 	parameter= et0_param_obj,
				# 	source = source_obj,
				# 	basin_details=basin_details,	 
				# 	step_start = day_start,
				# 	step_end = day_end,
				# 	forecast_date=forecast_date,
				# 	val_min = r2(et0_list_day_min_val),
				# 	val_avg = r2(et0_list_day_avg_val),
				# 	val_max = r2(et0_list_day_max_val),
				# 	val_avg_day   = 0,
				# 	val_avg_night = 0,
				# 	)
				# )
				

				# rainfall
				rf_day_masked  = np.ma.masked_array(rf_day, mask=weight_grid.mask)
				rf_max_val_day = rf_day_masked.max()
				rf_min_val_day = rf_day_masked.min()
				rf_avg_val_day = np.average(rf_day,weights=weight_grid) #weighted

				upazila_data_daily.append(ForecastDaily(
					parameter= rf_obj,
					source = source_obj,
					basin_details=basin_details,	 
					step_start = day_start,
					step_end = day_end,
					forecast_date=forecast_date,
					val_min = r2(rf_min_val_day),
					val_avg = r2(rf_avg_val_day),
					val_max = r2(rf_max_val_day),
					val_avg_day   = 0,
					val_avg_night = 0,
					)
				)

				# # temperature
				# temp_min_day_masked = np.ma.masked_array(temp_min_day,mask=weight_grid.mask)
				# temp_min_val_day    = temp_min_day_masked.min()

				# temp_max_day_masked = np.ma.masked_array(temp_max_day,mask=weight_grid.mask)
				# temp_max_val_day    = temp_max_day_masked.max()

				# temp_avg_day_masked = np.ma.masked_array(temp_avg_day,mask=weight_grid.mask)
				# temp_avg_val_day    = temp_avg_day_masked.mean()
				
				# upazila_data_daily.append(ForecastDaily(
				# 	parameter= temp_obj,
				# 	source = source_obj,
				# 	basin_details=basin_details,		 
				# 	step_start = day_start,
				# 	step_end = day_end,
				# 	forecast_date=forecast_date,
				# 	val_min = r2(temp_min_val_day),
				# 	val_avg = r2(temp_avg_val_day),
				# 	val_max = r2(temp_max_val_day),
				# 	val_avg_day   =0,
				# 	val_avg_night =0,
				# 	)
				# )


				# # relative humidity
				# rh_min_day_masked = np.ma.masked_array(rh_min_day,mask=weight_grid.mask)
				# rh_min_val_day    = rh_min_day_masked.min()

				# rh_max_day_masked = np.ma.masked_array(rh_max_day,mask=weight_grid.mask)
				# rh_max_val_day    = rh_max_day_masked.max()

				# rh_avg_day_masked = np.ma.masked_array(rh_avg_day,mask=weight_grid.mask)
				# rh_avg_val_day    = rh_avg_day_masked.mean()

				# upazila_data_daily.append(ForecastDaily(
				# 	parameter= rh_obj,
				# 	source = source_obj,
				# 	basin_details=basin_details,	 
				# 	step_start = day_start,
				# 	step_end = day_end,
				# 	forecast_date=forecast_date,
				# 	val_min = r2(rh_min_val_day),
				# 	val_avg = r2(rh_avg_val_day),
				# 	val_max = r2(rh_max_val_day),
				# 	val_avg_day   =0,
				# 	val_avg_night =0,
				# 	)
				# )

				# # wind speed
				# windspd_min_day_masked = np.ma.masked_array(windspd_min_day,mask=weight_grid.mask)
				# windspd_min_val_day    = windspd_min_day_masked.min()

				# windspd_max_day_masked = np.ma.masked_array(windspd_max_day,mask=weight_grid.mask)
				# windspd_max_val_day    = windspd_max_day_masked.max()

				# windspd_avg_day_masked = np.ma.masked_array(windspd_avg_day,mask=weight_grid.mask)
				# windspd_avg_val_day    = windspd_avg_day_masked.mean()

				# upazila_data_daily.append(ForecastDaily(
				# 	parameter= windspd_obj,
				# 	source = source_obj,
				# 	basin_details=basin_details,	 
				# 	step_start = day_start,
				# 	step_end = day_end,
				# 	forecast_date=forecast_date,
				# 	val_min = r2(windspd_min_val_day),
				# 	val_avg = r2(windspd_avg_val_day),
				# 	val_max = r2(windspd_max_val_day),
				# 	val_avg_day   =0,
				# 	val_avg_night =0,
				# 	)
				# )


				# # [temperature humidity index]
				# thi_min_day_masked = np.ma.masked_array(thi_min_day,mask=weight_grid.mask)
				# thi_min_val_day = thi_min_day_masked.min()

				# thi_max_day_masked = np.ma.masked_array(thi_max_day,mask=weight_grid.mask)
				# thi_max_val_day = thi_max_day_masked.max()

				# thi_avg_day_masked = np.ma.masked_array(thi_avg_day,mask=weight_grid.mask)
				# thi_avg_val_day = thi_avg_day_masked.mean()

				# upazila_data_daily.append(ForecastDaily(
				# 	parameter= thi_obj,
				# 	source = source_obj,
				# 	basin_details=basin_details, 
				# 	step_start = day_start,
				# 	step_end = day_end,
				# 	forecast_date=forecast_date,
				# 	val_min = r2(thi_min_val_day),
				# 	val_avg = r2(thi_avg_val_day),
				# 	val_max = r2(thi_max_val_day),
				# 	val_avg_day   =0,
				# 	val_avg_night =0,
				# 	)
				# )

			# insert to database for this shapefile of all days forecast
			ForecastDaily.objects.bulk_create(upazila_data_daily)

			upazila_data_daily=[] # to free excess memory

			# [===== 6hourly steps for first 4 day =====]

			# for fist eight step [temp,rh,temp,rh,ws] 
			# note end step is +1 no need +1 at range end
			
			# for t_step in range(0,17):

			# 	step_start_idx       = t_step
			# 	step_end_idx         = t_step+1
				
			# 	# date_fmt    = '%Y-%m-%d %M:%H'
			# 	date_fmt    = '%Y-%m-%d %H:%M:%S'
			# 	step_start  = (dt.strptime(dates[step_start_idx].strftime(date_fmt),date_fmt)+delt(hours=6)).strftime(date_fmt)
			# 	step_end    = (dt.strptime(dates[step_end_idx].strftime(date_fmt),date_fmt)+delt(hours=6)).strftime(date_fmt)

				
			# 	temp_max_step    = np.amax(temp[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	temp_min_step    = np.amin(temp[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	temp_avg_step    = np.average(temp[step_start_idx:step_end_idx+1,:,:],axis=0)

			# 	rh_max_step      = np.amax(rh[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	rh_min_step      = np.amin(rh[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	rh_avg_step      = np.average(rh[step_start_idx:step_end_idx+1,:,:],axis=0)

			# 	windspd_max_step = np.amax(windspd[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	windspd_min_step = np.amin(windspd[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	windspd_avg_step = np.average(windspd[step_start_idx:step_end_idx+1,:,:],axis=0)

				
			# 	# rainfall
			# 	if t_step==0:
			# 		rf_max_step      = rf[step_end_idx,:,:]
			# 	else:
			# 		rf_max_step      = rf[step_end_idx,:,:]-rf[step_start_idx,:,:]

			# 	# temperature humidity index
			# 	thi_max_step = np.amax(thi[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	thi_min_step = np.amin(thi[step_start_idx:step_end_idx+1,:,:],axis=0)
			# 	thi_avg_step = np.average(thi[step_start_idx:step_end_idx+1,:,:],axis=0)

				
			# 	# [db data preperation]

			# 	# [rainfall]

			# 	rf_max_val_step = np.average(rf_max_step,weights=weight_grid) 

			# 	upazila_data_steps.append(ForecastSteps(
			# 		parameter= rf_obj,
			# 		source = source_obj,
			# 		basin_details=basin_details,	 
			# 		step_start = step_start,
			# 		step_end = step_end,
			# 		forecast_date=forecast_date,
			# 		val_min = 0,
			# 		val_avg = 0,
			# 		val_max = r2(rf_max_val_step)
			# 		)
			# 	)

			# 	# # temperature
			# 	# temp_min_step_masked = np.ma.masked_array(temp_min_step,mask=weight_grid.mask)
			# 	# temp_min_val_step = temp_min_step_masked.min()

			# 	# temp_max_step_masked = np.ma.masked_array(temp_max_step,mask=weight_grid.mask)
			# 	# temp_max_val_step = temp_max_step_masked.max()

			# 	# temp_avg_step_masked = np.ma.masked_array(temp_avg_step,mask=weight_grid.mask)
			# 	# temp_avg_val_step = temp_avg_step_masked.mean()

			# 	# # break
			# 	# upazila_data_steps.append(ForecastSteps(
			# 	# 	parameter= temp_obj,
			# 	# 	source = source_obj,
			# 	# 	basin_details=basin_details,	 
			# 	# 	step_start = step_start,
			# 	# 	step_end = step_end,
			# 	# 	forecast_date=forecast_date,
			# 	# 	val_min = r2(temp_min_val_step),
			# 	# 	val_avg = r2(temp_avg_val_step),
			# 	# 	val_max = r2(temp_max_val_step)
			# 	# 	)
			# 	# )


			# 	# # relative humidity
			# 	# rh_min_step_masked = np.ma.masked_array(rh_min_step,mask=weight_grid.mask)
			# 	# rh_min_val_step = rh_min_step_masked.min()

			# 	# rh_max_step_masked = np.ma.masked_array(rh_max_step,mask=weight_grid.mask)
			# 	# rh_max_val_step = rh_max_step_masked.max()

			# 	# rh_avg_step_masked = np.ma.masked_array(rh_avg_step,mask=weight_grid.mask)
			# 	# rh_avg_val_step = rh_avg_step_masked.mean()


			# 	# upazila_data_steps.append(ForecastSteps(
			# 	# 	parameter= rh_obj,
			# 	# 	source = source_obj,
			# 	# 	basin_details=basin_details,	 
			# 	# 	step_start = step_start,
			# 	# 	step_end = step_end,
			# 	# 	forecast_date=forecast_date,
			# 	# 	val_min = r2(rh_min_val_step),
			# 	# 	val_avg = r2(rh_avg_val_step),
			# 	# 	val_max = r2(rh_max_val_step)
			# 	# 	)
			# 	# )

			# 	# # wind speed
			# 	# windspd_min_step_masked = np.ma.masked_array(windspd_min_step,mask=weight_grid.mask)
			# 	# windspd_min_val_step = windspd_min_step_masked.min()

			# 	# windspd_max_step_masked = np.ma.masked_array(windspd_max_step,mask=weight_grid.mask)
			# 	# windspd_max_val_step = windspd_max_step_masked.max()

			# 	# windspd_avg_step_masked = np.ma.masked_array(windspd_avg_step,mask=weight_grid.mask)
			# 	# windspd_avg_val_step = windspd_avg_step_masked.mean()


			# 	# upazila_data_steps.append(ForecastSteps(
			# 	# 	parameter= windspd_obj,
			# 	# 	source = source_obj,
			# 	# 	basin_details=basin_details,	 
			# 	# 	step_start = step_start,
			# 	# 	step_end = step_end,
			# 	# 	forecast_date=forecast_date,
			# 	# 	val_min = r2(windspd_min_val_step),
			# 	# 	val_avg = r2(windspd_avg_val_step),
			# 	# 	val_max = r2(windspd_max_val_step)
			# 	# 	)
			# 	# )


			# 	# # [ temperature humidity index ]
			# 	# thi_min_step_masked = np.ma.masked_array(thi_min_step,mask=weight_grid.mask)
			# 	# thi_min_val_step = thi_min_step_masked.min()

			# 	# thi_max_step_masked = np.ma.masked_array(thi_max_step,mask=weight_grid.mask)
			# 	# thi_max_val_step = thi_max_step_masked.max()

			# 	# thi_avg_step_masked = np.ma.masked_array(thi_avg_step,mask=weight_grid.mask)
			# 	# thi_avg_val_step = thi_avg_step_masked.mean()

				

			# 	# upazila_data_steps.append(ForecastSteps(
			# 	# 	parameter= thi_obj,
			# 	# 	source = source_obj,
			# 	# 	basin_details=basin_details,	 
			# 	# 	step_start = step_start,
			# 	# 	step_end = step_end,
			# 	# 	forecast_date=forecast_date,
			# 	# 	val_min = r2(thi_min_val_step),
			# 	# 	val_avg = r2(thi_avg_val_step),
			# 	# 	val_max = r2(thi_max_val_step)
			# 	# 	)
			# 	# )



			# # inserting to database
			# ForecastSteps.objects.bulk_create(upazila_data_steps)



	def parameter_reduced_step(self,forecast_date,source_obj,ncf, file_path, my_country_id):

		print('generating parameter-reduced values...')

		lats = ncf.variables['latitude'][:]
		lons = ncf.variables['longitude'][:]
		times = num2date(ncf.variables['time'][:], ncf.variables['time'].units)

		t2 = ncf.variables['t2m'][:,:,:] - 273.15

		tempdew = ncf.variables['d2m'][:] - 273.15
		rh2 = 100 - 5* (t2-tempdew)
		
		# THI = 0.8 * t_db + RH * (t_tdb − 14.4) + 46.4
		thi = 0.8*t2 + (rh2/100) * (t2 - 14.4) + 46.4

		# admin - 0
		
		adm0_obj = GeoLevel.objects.get(
			parent__isnull=BD_GEO_LEVEL['Country']['parent_is_null'], 
			ordering=BD_GEO_LEVEL['Country']['ordering'],
			country=my_country_id
		)
		# adm0_obj = adm_level.objects.get(level=0)
		
		# adm0_sf_loc = os.path.join(settings.BASE_DIR,settings.SHP_DIR,'gadm36_BGD_0.zip')
		# adm0_sf = fiona.open(f'zip://{adm0_sf_loc}')
		adm0_sf = fiona.open(file_path,'r')


		rec = next(iter(adm0_sf))
		adm0_shape_obj = shape(rec['geometry'])
		
		pys_obj = scissor(adm0_shape_obj,lats,lons)
		adm0_wg = pys_obj.get_masked_weight_recursive()


		# Parameter objects
		thi_param_obj = Parameter.objects.get(name='thi')

		data = []
			
		for i,time in enumerate(times):
			step_time_str = time.strftime('%Y-%m-%d %H:%M')
			step_time_unx = dt.timestamp(
					dt.strptime(step_time_str, '%Y-%m-%d %H:%M')
				)*1000
			

			thi_masked_step = np.ma.masked_array(data=thi[i],mask=adm0_wg.mask)
			min_val = r2(thi_masked_step.min())
			max_val = r2(thi_masked_step.max())

			data.append(ParameterReducedStep(
				level=adm0_obj,
				source= source_obj,
				parameter = thi_param_obj,
				loc_id= 99, # may be country code
				forecast_date = forecast_date,
				step_time = step_time_str,
				step_time_unx = int(step_time_unx),
				val_min = min_val,
				val_max = max_val 
			))

		ParameterReducedStep.objects.bulk_create(data)

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

		forecast_date = dt.strptime(date,'%Y%m%d').strftime('%Y-%m-%d')
		nc_fmt_date = dt.strptime(date,'%Y%m%d').strftime('%Y%m%d')
		# nc_fmt_date = dt.strptime(date,'%Y%m%d').strftime('%d%m%Y')
		
		source_list = Source.objects.filter(
			name='ECMWF_HRES', source_type="basin_specific",
			source_data_type__name="Forecast"
		) 

		for my_source_details in source_list: 

			source_obj = Source.objects.get(
				name='ECMWF_HRES', source_type="basin_specific",
				source_data_type__name="Forecast"
			)
			MY_ECMWF_HRES_DIR = Source.objects.filter(
				name='ECMWF_HRES', source_type="basin_specific",
				source_data_type__name="Forecast"
			)[0].source_path #settings.ECMWF_HRES_DIR
			
			
			nc_loc = str(BMDWRF_BASE_URL)+str(MY_ECMWF_HRES_DIR)+f'{nc_fmt_date}/tp.nc'
			# nc_loc = os.path.join(MY_ECMWF_HRES_DIR,f'{nc_fmt_date}.nc')
			ncf = nco(nc_loc, 'r')

			# ###############################################################################
			# ### START Store ET0 part
			# #############################################################################
			# # Get date as YYYYMMDD format
            # # current_date =  date.today()
			# current_date =  dt.now()
			# current_date_str = current_date.strftime("%d%m%Y")
			# # current_date_str = '01102023'
            
			# et0_obj = ET0CalculationConfiguration.objects.filter(source='ECMWF_HRES')[0]
			# et0_file_path = str(BASE_DIR) + str(et0_obj.destination_path) +  "ECMWF_HRES" + '/' + str(current_date_str) + '.nc'
			# et0_ncf = nco(et0_file_path, 'r')
			# ###############################################################################
			# ### END Store ET0 part
			# #############################################################################


			##############################################################################
			### Level wise forecast dumping
			##############################################################################

			basin_shape_file_path_obj = BasinDetails.objects.all()
			for basin_details in basin_shape_file_path_obj:
				# print("$$$$$$$$$$$$$ setting_level.name : ", setting_level.name)

				file_path = str(BMDWRF_BASE_URL) + str(basin_details.shape_file_path)
				# print("############ path : ", file_path)

				self.gen_upazila_forecast(forecast_date, source_obj, ncf, file_path, basin_details)
				# self.parameter_reduced_step(forecast_date, source_obj, ncf, file_path, my_country_id)
			self.update_state(forecast_date, source_obj)

			ncf.close()


		


