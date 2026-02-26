# management/commands/generate_forecast_data.py

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import pylab as pl 
import numpy as np
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
# WRF_NC_LOC = app_visualization['bmdwrf']['WRF_NC_LOC']
# JSON_OUT_LOC = app_visualization['bmdwrf']['JSON_OUT_LOC']

SOURCE_ECMWF_HRES = app_visualization['source']['BMDWRF_HRES_VIS'] 
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][2]

BMDWRF_BASE_URL = settings.BASE_DIR










class Command(BaseCommand):
    help = 'Generate forecast data for BMDWRF'

    def add_arguments(self, parser):
        # parser.add_argument('fdate', type=str, help='Date for forecast data in format YYYYMMDD')
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')

    
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

    
    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate']

        if fdate is None:
            today_date = dt.now()
            formatted_date = today_date.strftime('%Y%m%d')  # Date format = YYYYMMDD
            print("formatted_date: ", formatted_date)
            fdate = formatted_date
        
        # source object
        # source_obj = Source.objects.filter(pk=SOURCE_ECMWF_HRES)[0] 
        source_obj = Source.objects.filter(
			name='BMDWRF_HRES_VIS', source_type="vis",
			source_data_type__name="Forecast"
		)[0]  

        WRF_NC_LOC = source_obj.source_path
        JSON_OUT_LOC = source_obj.destination_path

        # read nc
        date_obj = dt.strptime(fdate, '%Y%m%d')

        
        ncfile = str(BMDWRF_BASE_URL)+str(WRF_NC_LOC)+f'wrf_out_{fdate}00.nc'
        forecast_out_dir = str(BMDWRF_BASE_URL)+str(JSON_OUT_LOC)+str(fdate)
        # ncfile = os.path.join(WRF_NC_LOC, f'wrf_out_{fdate}00.nc')
        # forecast_out_dir = os.path.join(settings.JSON_OUT_LOC, fdate)
        print(" $$$$$$$$$$$ ncfile: ", ncfile)
        print(" $$$$$$$$$$$ forecast_out_dir: ", forecast_out_dir)

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir)

        #bmd rainfall colormap
        rf_colors=['#00dc00','#a0e632','#e6dc32','#e6af2d','#f08228','#fa3c3c','#f00082']
        rf_lvls = np.array([1,5,10,20,30,40,60,70,80])
        bmd_pr_dly_cmap = mplcolors.LinearSegmentedColormap.from_list('bmd_pr_dly_cmap',rf_colors)

        nf = nco(ncfile,'r')

        # get vars
        lat      = nf.variables['lat'][:]
        lon      = nf.variables['lon'][:]
        time 	 = nf.variables['time']
        dates 	 = num2date(time[:],time.units,time.calendar)

        # print(list(zip(np.arange(81),dates)))

        temp     = nf.variables['t2'][:,0,:,:]-273.15
        rh       = nf.variables['rh2'][:,0,:,:]
        ws       = nf.variables['ws10'][:,0,:,:]*3.6  # m/s to km/h
        clflo 	 = nf.variables['clflo'][:,0,:,:] / 0.125  # cldfralo to okta
        rf       = nf.variables['rainc'][:,0,:,:]+nf.variables['rainnc'][:,0,:,:]
        thi      = 0.8*temp + (rh/100)*(temp-14.4) + 46.4
        

        # generate daily rainfall geojson


        # 81 steps

        finfo = {
            'fdate'  : fdate,
            'rf'     : [],
            'tmin'   : [],
            'tmax'   : [],
            'rh'     : [],  # avg
            'ws'     : [],  # avg
            'cldflo' : [],  # avg
            'thi_min': [],
            'thi_max': [],
        }

        for day in tqdm(range(10), desc="Processing Days"):
        # for day in range(10):

            start_step = day*8 
            end_step   = day*8 +8 

            start_time = dates[start_step].strftime('%Y%m%d%H')
            end_time   = dates[end_step].strftime('%Y%m%d%H')

            start_time_bst = (dt.strptime(start_time,'%Y%m%d%H')+delt(hours=6)).strftime('%Y-%m-%d %H:%M')
            end_time_bst   = (dt.strptime(end_time,'%Y%m%d%H')+delt(hours=6)).strftime('%Y-%m-%d %H:%M')


            json_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.geojson'
            cmap_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.svg'

            
            rf_d      = rf[end_step] - rf[start_step]
            tmin_d    = np.amin(temp[start_step:end_step+1,:,:],axis=0) 
            tmax_d    = np.amax(temp[start_step:end_step+1,:,:],axis=0)
            rh_d      = np.average(rh[start_step:end_step+1,:,:],axis=0)
            ws_d      = np.average(ws[start_step:end_step+1,:,:],axis=0) 
            cldflo_d  = np.average(clflo[start_step:end_step+1,:,:],axis=0)
            
            thi_min_d = np.amin(thi[start_step:end_step+1,:,:],axis=0)
            thi_max_d = np.amax(thi[start_step:end_step+1,:,:],axis=0)
            


            # == Rainfall ==
            ax      = pl.axes()
            max_rf  = int(rf_d.max()) 
            rf_diff    = int((max_rf-1)/20)
            #rf_levels = np.arange(1,max_rf+rf_diff,rf_diff)
            rf_levels    = np.array([1,5,10,20,30,50,70,100,150,200,250])

            rf_cont_plot = pl.contourf(zoom(lon,4),zoom(lat,4),zoom(rf_d,4),cmap='Spectral_r',levels=rf_levels,extend='max',vmin=1)

            rf_geojson   = gj.contourf_to_geojson(rf_cont_plot)

            with open(os.path.join(forecast_out_dir,f'rf{json_suffix}'),'w') as jfw:
                jfw.write(rf_geojson)

            cbar = pl.colorbar(orientation='horizontal')
            cbar.outline.set_visible(False)
            ax.remove()
            pl.savefig(os.path.join(forecast_out_dir,f'rf{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            pl.close()


            # # == Temperature Min == #
            # ax = pl.axes()
            # tmin_cont_plot = pl.contourf(zoom(lon,4),zoom(lat,4),zoom(tmin_d,4),cmap='bwr',levels=[-5,*list(range(0,42,3))],extend='both')

            # tmin_geojson   = gj.contourf_to_geojson(tmin_cont_plot)

            # with open(os.path.join(forecast_out_dir,f'tmin{json_suffix}'),'w') as jfw:
            #     jfw.write(tmin_geojson)

            # cbar = pl.colorbar(orientation='horizontal')
            # cbar.outline.set_visible(False)
            # ax.remove()
            # pl.savefig(os.path.join(forecast_out_dir,f'tmin{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            # pl.close()

            # # == Temperature Max == #
            # ax = pl.axes()
            # tmax_cont_plot = pl.contourf(zoom(lon,4),zoom(lat,4),zoom(tmax_d,4),cmap='bwr',levels=[-5,*list(range(0,42,3))] ,extend='both')

            # tmax_geojson   = gj.contourf_to_geojson(tmax_cont_plot)

            # with open(os.path.join(forecast_out_dir,f'tmax{json_suffix}'),'w') as jfw:
            #     jfw.write(tmax_geojson)

            # cbar = pl.colorbar(orientation='horizontal')
            # cbar.outline.set_visible(False)
            # ax.remove()
            # pl.savefig(os.path.join(forecast_out_dir,f'tmax{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            # pl.close()



            # # == Relative Humidity (avg)== #
            # ax = pl.axes()
            # rhavg_cont_plot = pl.contourf(lon,lat,rh_d,cmap='summer_r')

            # rhavg_geojson   = gj.contourf_to_geojson(rhavg_cont_plot)

            # with open(os.path.join(forecast_out_dir,f'rh{json_suffix}'),'w') as jfw:
            #     jfw.write(rhavg_geojson)

            # cbar = pl.colorbar(orientation='horizontal')
            # cbar.outline.set_visible(False)
            # ax.remove()
            # pl.savefig(os.path.join(forecast_out_dir,f'rh{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            # pl.close()


            # # == Wind Speed (avg)== #
            # ax = pl.axes()
            
            # ws_levels=[1,2,3,5,7,10,15,20,30,40,50,60,70,80,90,100,110,120]
            # ws_cont_plot = pl.contourf(zoom(lon,4),zoom(lat,4),zoom(ws_d,4),cmap='GnBu',levels=ws_levels,extend='max')

            # ws_geojson   = gj.contourf_to_geojson(ws_cont_plot)

            # with open(os.path.join(forecast_out_dir,f'ws{json_suffix}'),'w') as jfw:
            #     jfw.write(ws_geojson)

            # cbar = pl.colorbar(orientation='horizontal')
            # cbar.outline.set_visible(False)
            # ax.remove()
            # pl.savefig(os.path.join(forecast_out_dir,f'ws{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            # pl.close()


            # # == Cloud Fraction (avg)== #
            # ax = pl.axes()

            # cldflo_cont_plot = pl.contourf(zoom(lon,4),zoom(lat,4),zoom(cldflo_d,4),cmap='cool',levels=range(1,9))

            # cldflo_geojson   = gj.contourf_to_geojson(cldflo_cont_plot)

            # with open(os.path.join(forecast_out_dir,f'cldflo{json_suffix}'),'w') as jfw:
            #     jfw.write(cldflo_geojson)

            # cbar = pl.colorbar(orientation='horizontal')
            # cbar.outline.set_visible(False)
            # ax.remove()
            # pl.savefig(os.path.join(forecast_out_dir,f'cldflo{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            # pl.close()
            
            # # == Temperature Humidity Index - Max ==#
            # thi_levels = range(70,101,1)
            
            # ax = pl.axes()

            # thi_max_cont_plot = pl.contourf(zoom(lon,4),zoom(lat,4),zoom(thi_max_d,4),cmap='YlOrBr',levels=thi_levels,extend='both')

            # thi_max_geojson   = gj.contourf_to_geojson(thi_max_cont_plot)

            # with open(os.path.join(forecast_out_dir,f'thi_max{json_suffix}'),'w') as jfw:
            #     jfw.write(thi_max_geojson)

            # cbar = pl.colorbar(orientation='horizontal')
            # cbar.outline.set_visible(False)
            # ax.remove()
            # pl.savefig(os.path.join(forecast_out_dir,f'thi_max{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            # pl.close()
            
            # # == Temperature Humidity Index - Min ==#
            
            # ax = pl.axes()

            # thi_min_cont_plot = pl.contourf(zoom(lon,4),zoom(lat,4),zoom(thi_min_d,4),cmap='YlOrBr',levels=thi_levels,extend='both')

            # thi_min_geojson   = gj.contourf_to_geojson(thi_min_cont_plot)

            # with open(os.path.join(forecast_out_dir,f'thi_min{json_suffix}'),'w') as jfw:
            #     jfw.write(thi_max_geojson)

            # cbar = pl.colorbar(orientation='horizontal')
            # cbar.outline.set_visible(False)
            # ax.remove()
            # pl.savefig(os.path.join(forecast_out_dir,f'thi_min{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            # pl.close()

            # generate finfo.json


            finfo['rf'].append(
                {
                'file'  : f'rf{json_suffix}',
                'cmap'  : f'rf{cmap_suffix}',
                'start' : start_time_bst,
                'end'   : end_time_bst,
                }
            )
            # finfo['ws'].append(
            #     {
            #     'file':f'ws{json_suffix}',
            #     'cmap':f'ws{cmap_suffix}',
            #     'start' : start_time_bst,
            #     'end'   : end_time_bst,
            #     }
            # )
            # finfo['rh'].append(
            #     {
            #     'file':f'rh{json_suffix}',
            #     'cmap':f'rh{cmap_suffix}',
            #     'start' : start_time_bst,
            #     'end'   : end_time_bst,
            #     }
            # )
            # finfo['tmax'].append(
            #     {
            #     'file':f'tmax{json_suffix}',
            #     'cmap':f'tmax{cmap_suffix}',
            #     'start' : start_time_bst,
            #     'end'   : end_time_bst,
            #     }
            # )
            # finfo['tmin'].append(
            #     {
            #     'file':f'tmin{json_suffix}', 
            #     'cmap':f'tmin{cmap_suffix}',
            #     'start' : start_time_bst,
            #     'end'   : end_time_bst,
            #     }
            # )
            # finfo['cldflo'].append(
            #     {
            #     'file':f'cldflo{json_suffix}',
            #     'cmap':f'cldflo{cmap_suffix}',
            #     'start' : start_time_bst,
            #     'end'   : end_time_bst,
            #     }
            # )
            
            # finfo['thi_min'].append(
            #     {
            #     'file':f'thi_min{json_suffix}',
            #     'cmap':f'thi_min{cmap_suffix}',
            #     'start' : start_time_bst,
            #     'end'   : end_time_bst,
            #     }
            # )
            
            # finfo['thi_max'].append(
            #     {
            #     'file':f'thi_max{json_suffix}',
            #     'cmap':f'thi_max{cmap_suffix}',
            #     'start' : start_time_bst,
            #     'end'   : end_time_bst,
            #     }
            # )
            # break
        

        # save forecast info
        with open(os.path.join(f'{forecast_out_dir}',f'info.{fdate}.json'),'w') as infojw:
            json.dump(finfo, infojw)

        # update state
        self.update_state(date_obj, source_obj)

