import ast
import json 
import os 
import sys
import numpy as np
import fiona
import io

from netCDF4 import Dataset as nco, num2date
from datetime import datetime
from tqdm import tqdm
from shapely.geometry import shape
from pyscissor import scissor 

from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.shortcuts import render

from datetime import datetime as dt

from rest_framework import status 
from rest_framework.response import Response 
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework import generics
from rest_framework.exceptions import APIException

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.conf import settings


from app_visualization.models import (
    Parameter, Source, BasinDetails,
    ForecastDaily, ForecastSteps, SystemState
)

from app_visualization.basin_wise_forecast_from_nc_file.serializers import (
    ForcastStateDDReqSerializer
) 


BMDWRF_BASE_URL = settings.BASE_DIR










def r2(val):
	return round(val,2)

def thi_(temp:float,rh:float)->float:
	# THI = 0.8 * t_db + RH * (t_tdb − 14.4) + 46.4
	return (0.8*temp) + (rh/100)*(temp-14.4) + 46.4

@method_decorator(csrf_exempt, name='dispatch') 
class BasinWiseForcastFromNcFileViewSet(viewsets.ViewSet):
    """
        API for various forecast 
    """  
    
    permission_classes = (IsAuthenticated,)


    def level_wise_forecast_date_wise_all_loc_from_nc_file(self, request):
        """ 
            Purpose: list of sources drop down

            Method: GET
            Args:
                None

            Returns:
                JSON response containing message, status and data if applicable:
                    Success:
                        status: Positive Integer 
                        results: List of JSON
                    Failure:
                        message: JSON
                        status: Numbers 
        """

        data = {}

        requested_data = self.request.data  #.dict()
        print("requested_data: ", requested_data)
        req_serializer = ForcastStateDDReqSerializer(data=requested_data)
        if req_serializer.is_valid():

            # parameter = request.GET.getlist('parameter') 
            source = requested_data['source']
            my_date_str   = requested_data['forecast_date']
            forecast_date   = requested_data['forecast_date']
            basin_shape = requested_data['basin_shape'] 
            # basin_shape_bytes = io.BytesIO(json.dumps(basin_shape).encode('utf-8'))
            print("basin_shape: ", basin_shape) 
            
        
            if source==None: 
                return JsonResponse({'error':'no source defined'})
            elif Source.objects.filter(id=source).count()!=1:
                return JsonResponse({'error':'invalid source'})
            
            source_obj = Source.objects.filter(pk=source)[0]
            
            if source_obj.name == "BMDWRF":
                        
                shape_file_path = str(BMDWRF_BASE_URL)+"/forecast/api_req_shape_file.geojson"
                with open(shape_file_path, 'w') as file:
                    json.dump(basin_shape, file, indent=4)
                    
                
                if forecast_date==None:
                    return JsonResponse({'error':'FDATE not defined'})
                else:
                    try:
                        forecast_date = dt.strptime(forecast_date,'%Y%m%d').strftime('%Y-%m-%d')
                        print("type of forecast_date: ", (forecast_date))
                        print("type of forecast_date: ", type(forecast_date))
                    except:
                        return JsonResponse({'error':'invalid date format. provide YYYYMMDD format'})

                source_obj = Source.objects.get(
                    id=requested_data['source']
                )
                            
                MY_BMD_WRF_DIR = Source.objects.filter(
                    id=requested_data['source'] 
                )[0].source_path 

                nc_loc = str(BMDWRF_BASE_URL)+str(MY_BMD_WRF_DIR)+f'wrf_out_{my_date_str}00.nc'
                ncf = nco(nc_loc,'r')
                print("nc_loc: ", nc_loc)
                
                shf = fiona.open(shape_file_path,'r')  
                # shf = fiona.open(basin_shape_bytes, 'r', driver='GeoJSON')  
                
                lats = ncf.variables['lat'][:]
                lons = ncf.variables['lon'][:]
                times = ncf.variables['time']
                dates = num2date(times[:],times.units,times.calendar)
                

                rf      = ncf.variables['rainc'][:] + ncf.variables['rainnc'][:]
                temp    = ncf.variables['t2'][:] - 273.15     # K => C conversion
                rh      = ncf.variables['rh2'][:]
                windspd = ncf.variables['ws10'][:] * 3.6      # m/s => kmph conversion 
                cldcvr  = ncf.variables['clflo'][:] / 0.125   # frac => okta conversion
                winddir = ncf.variables['wd10'][:]
                smois = ncf.variables['smois'][:]  
                thi     = 0.8*temp + (rh/100)*(temp-14.4) + 46.4

                # get object form db
                rf_obj       = Parameter.objects.get(name='rf')
                temp_obj     = Parameter.objects.get(name='temp')
                tmax_obj     = Parameter.objects.get(name='tmax')
                tmin_obj     = Parameter.objects.get(name='tmin')
                rh_obj       = Parameter.objects.get(name='rh')
                windspd_obj  = Parameter.objects.get(name='windspd')
                tempdew_obj  = Parameter.objects.get(name='tempdew')
                cldcvr_obj   = Parameter.objects.get(name='cldcvr')
                winddir_obj  = Parameter.objects.get(name='winddir') 
                thi_obj		 = Parameter.objects.get(name='thi')
                smois_obj	 = Parameter.objects.get(name='smois')
                print(" $$$$$$$ rf_obj: ", rf_obj.name)
                
                # iterate through upazillas
                for idx, i_shape in enumerate(tqdm(shf)): 
                    
                    upazila_data_daily = [] 

                    shape_obj   = shape(i_shape['geometry'])

                    pys         = scissor(shape_obj, lats, lons)
                    weight_grid = pys.get_masked_weight()  

                    # [iterate thorugh all days]
                    for day in range(10):
                        
                        day_start_idx       = (day)*8
                        day_end_idx         = (day+1)*8
                        
                        day_start      = dates[day_start_idx].strftime('%Y-%m-%d %M:%H')
                        day_end        = dates[day_end_idx].strftime('%Y-%m-%d %M:%H')

                        rf_day          = rf[day_end_idx,0,:,:] - rf[day_start_idx,0,:,:]
                        
                        temp_max_day     = np.amax(temp[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        temp_min_day     = np.amin(temp[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        temp_avg_day     = np.average(temp[day_start_idx:day_end_idx+1,0,:,:],axis=0)

                        rh_max_day       = np.amax(rh[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        rh_min_day       = np.amin(rh[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        rh_avg_day       = np.average(rh[day_start_idx:day_end_idx+1,0,:,:],axis=0)

                        windspd_max_day  = np.amax(windspd[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        windspd_min_day  = np.amin(windspd[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        windspd_avg_day  = np.average(windspd[day_start_idx:day_end_idx+1,0,:,:],axis=0)

                        winddir_max_day  = np.amax(winddir[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        winddir_min_day  = np.amin(winddir[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        winddir_avg_day  = np.average(winddir[day_start_idx:day_end_idx+1,0,:,:],axis=0)

                        # save day in min
                        cldcvr_avg_day   = np.average(cldcvr[day_start_idx:day_start_idx+4+1,0,:,:],axis=0)
                        # save night in max
                        cldcvr_avg_night = np.average(cldcvr[day_start_idx+4:day_end_idx+1,0,:,:],axis=0)

                        # calculate them from upazilla extracted values
                        # temperature humidity index
                        thi_max_day =  np.amax(thi[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        thi_min_day =  np.amin(thi[day_start_idx:day_end_idx+1,0,:,:],axis=0)
                        thi_avg_day =  np.average(thi[day_start_idx:day_end_idx+1,0,:,:],axis=0)

                        # temperature humidity index
                        smois_max_day =  np.amax(smois[day_start_idx:day_end_idx+1,2,:,:],axis=0)
                        smois_min_day =  np.amin(smois[day_start_idx:day_end_idx+1,2,:,:],axis=0)
                        smois_avg_day =  np.average(smois[day_start_idx:day_end_idx+1,2,:,:],axis=0)
                        
                        '''
                        0   1   2   3   4
                        06  09  12  15  18
                        4   5   6   7   8
                        18  21  24  03  06 

                        '''
                        # rainfall
                        rf_day_masked  = np.ma.masked_array(rf_day,mask=weight_grid.mask)
                        rf_max_val_day = rf_day_masked.max()
                        rf_min_val_day = rf_day_masked.min()
                        rf_avg_val_day = np.average(rf_day,weights=weight_grid) #weighted

                        upazila_data_daily.append(dict(
                            parameter= dict(
                                id=rf_obj.id,
                                name=rf_obj.name,
                                full_name=rf_obj.full_name
                            ),
                            source = dict(
                                id=source_obj.id,
                                name=source_obj.name 
                            ), 
                            step_start = day_start,
                            step_end = day_end,
                            forecast_date=forecast_date,
                            val_min = str(r2(rf_min_val_day)),
                            val_avg = str(r2(rf_avg_val_day)),
                            val_max = str(r2(rf_max_val_day)),
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

                        # # soil moisture
                        # smois_min_day_masked = np.ma.masked_array(smois_min_day,mask=weight_grid.mask)
                        # smois_min_val_day    = smois_min_day_masked.min()

                        # smois_max_day_masked = np.ma.masked_array(smois_max_day,mask=weight_grid.mask)
                        # smois_max_val_day    = smois_max_day_masked.max()

                        # smois_avg_day_masked = np.ma.masked_array(smois_avg_day,mask=weight_grid.mask)
                        # smois_avg_val_day    = smois_avg_day_masked.mean()


                        # upazila_data_daily.append(ForecastDaily(
                        # 	parameter= smois_obj,
                        # 	source = source_obj, 
                        # 	step_start = day_start,
                        # 	step_end = day_end,
                        # 	forecast_date=forecast_date,
                        # 	val_min = r2(smois_min_val_day),
                        # 	val_avg = r2(smois_avg_val_day),
                        # 	val_max = r2(smois_max_val_day),
                        # 	val_avg_day   =0,
                        # 	val_avg_night =0,
                        # 	)
                        # )


                        # # dew point temperature [disabled]
                        # tempdew_min_day_masked = np.ma.masked_array(tempdew_min_day,mask=weight_grid.mask)
                        # tempdew_min_val = tempdew_min_day_masked.mean()

                        # tempdew_max_day_masked = np.ma.masked_array(tempdew_max_day,mask=weight_grid.mask)
                        # tempdew_max_val = tempdew_max_day_masked.mean()

                        # tempdew_avg_day_masked = np.ma.masked_array(tempdew_avg_day,mask=weight_grid.mask)
                        # tempdew_avg_val = tempdew_avg_day_masked.mean()


                        # upazila_data_daily.append(ForecastDaily(
                        # 	Parameter= tempdew_obj,
                        # 	source = source_obj, 
                        # 	step_start = day_start,
                        # 	step_end = day_end,
                        # 	forecast_date=forecast_date,
                        # 	val_min = tempdew_min_val,
                        # 	val_avg = tempdew_avg_val,
                        # 	val_max = tempdew_max_val
                        # 	)
                        # )

                        # # wind direction
                        # winddir_min_day_masked = np.ma.masked_array(winddir_min_day,mask=weight_grid.mask)
                        # winddir_min_val_day = winddir_min_day_masked.min()

                        # winddir_max_day_masked = np.ma.masked_array(winddir_max_day,mask=weight_grid.mask)
                        # winddir_max_val_day = winddir_max_day_masked.max()

                        # winddir_avg_day_masked = np.ma.masked_array(winddir_avg_day,mask=weight_grid.mask)
                        # winddir_avg_val_day = winddir_avg_day_masked.mean()


                        # upazila_data_daily.append(ForecastDaily(
                        # 	parameter= winddir_obj,
                        # 	source = source_obj, 
                        # 	step_start = day_start,
                        # 	step_end = day_end,
                        # 	forecast_date=forecast_date,
                        # 	val_min = r2(winddir_min_val_day),
                        # 	val_avg = r2(winddir_avg_val_day),
                        # 	val_max = r2(winddir_max_val_day),
                        # 	val_avg_day   =0,
                        # 	val_avg_night =0,
                        # 	)
                        # )

                        # # cloud_cover
                        # cldcvr_avg_day_masked = np.ma.masked_array(cldcvr_avg_day,mask=weight_grid.mask)
                        # cldcvr_dayavg_val_day = cldcvr_avg_day_masked.mean()

                        # cldcvr_avg_night_masked = np.ma.masked_array(cldcvr_avg_night,mask=weight_grid.mask)
                        # cldcvr_nightavg_val = cldcvr_avg_night_masked.mean()


                        # upazila_data_daily.append(ForecastDaily(
                        # 	parameter= cldcvr_obj,
                        # 	source = source_obj, 
                        # 	step_start = day_start,
                        # 	step_end = day_end,
                        # 	forecast_date=forecast_date,
                        # 	val_min = 0,
                        # 	val_avg = 0,
                        # 	val_max = 0,
                        # 	val_avg_day   = r2(cldcvr_dayavg_val_day),
                        # 	val_avg_night = r2(cldcvr_nightavg_val),
                        # 	)
                        # )

                        # # wind direction
                        # windgust_min_day_masked = np.ma.masked_array(windgust_min_day,mask=weight_grid_g.mask)
                        # windgust_min_val_day = windgust_min_day_masked.min()

                        # windgust_max_day_masked = np.ma.masked_array(windgust_max_day,mask=weight_grid_g.mask)
                        # windgust_max_val_day = windgust_max_day_masked.max()

                        # windgust_avg_day_masked = np.ma.masked_array(windgust_avg_day,mask=weight_grid_g.mask)
                        # windgust_avg_val_day = windgust_avg_day_masked.mean()


                        # upazila_data_daily.append(ForecastDaily(
                        # 	parameter= windgust_obj,
                        # 	source = source_obj, 
                        # 	step_start = day_start,
                        # 	step_end = day_end,
                        # 	forecast_date=forecast_date,
                        # 	val_min = r2(windgust_min_val_day),
                        # 	val_avg = r2(windgust_avg_val_day),
                        # 	val_max = r2(windgust_max_val_day),
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
                    # ForecastDaily.objects.bulk_create(upazila_data_daily)




                data['rf']=upazila_data_daily
                # data['data']=[forecast.to_dict() for forecast in upazila_data_daily]

                return JsonResponse(data, json_dumps_params={'indent': 4}) 
            return Response(dict(message="source is not valid"), status=status.HTTP_400_BAD_REQUEST)
        
        return Response(dict(message="data is not valid"), status=status.HTTP_400_BAD_REQUEST)