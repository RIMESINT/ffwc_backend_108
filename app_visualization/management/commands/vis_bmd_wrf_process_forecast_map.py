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

SOURCE_ECMWF_HRES = app_visualization['source']['BMDWRF_HRES_VIS'] 
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][2]

BMDWRF_BASE_URL = settings.BASE_DIR

class Command(BaseCommand):
    help = 'Generate forecast data for BMDWRF'

    def add_arguments(self, parser):
        # 1. Positional argument support for manual CLI cron execution tasks
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

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
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')

        if ui_date:
            # Drop incoming dashboard calendar template dashes safely: '2026-06-30' -> '20260630'
            fdate = ui_date.replace('-', '')
            print(f"###### Received date via UI Selector: {ui_date} -> Normalized to: {fdate}")
        elif positional_date:
            fdate = positional_date
            print(f"###### Received date via Positional CLI: {fdate}")
        else:
            today_date = dt.now()
            fdate = today_date.strftime('%Y%m%d')  # Default fallback layout = YYYYMMDD
            print(f"###### No date provided. Defaulting to system date: {fdate}")
        
        # source object
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
        print(" $$$$$$$$$$$ ncfile: ", ncfile)
        print(" $$$$$$$$$$$ forecast_out_dir: ", forecast_out_dir)

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir)

        rf_colors = ['#00DC00', '#A0E632', '#E6DC32', '#E6AF2D', '#F08228', '#FA3C3C', '#F00082']
        rf_levels = [1, 10, 20, 40, 80, 160, 250, 1000]  
        bmd_pr_dly_cmap = mplcolors.ListedColormap(rf_colors)
        norm = mplcolors.BoundaryNorm(rf_levels, bmd_pr_dly_cmap.N)
        
        nf = nco(ncfile,'r')

        # get vars
        lat      = nf.variables['lat'][:]
        lon      = nf.variables['lon'][:]
        time 	 = nf.variables['time']
        dates 	 = num2date(time[:],time.units,time.calendar)

        temp     = nf.variables['t2'][:,0,:,:]-273.15
        rh       = nf.variables['rh2'][:,0,:,:]
        ws       = nf.variables['ws10'][:,0,:,:]*3.6  
        clflo 	 = nf.variables['clflo'][:,0,:,:] / 0.125  
        rf       = nf.variables['rainc'][:,0,:,:]+nf.variables['rainnc'][:,0,:,:]
        thi      = 0.8*temp + (rh/100)*(temp-14.4) + 46.4
        
        finfo = {
            'fdate'  : fdate,
            'rf'     : [],
            'tmin'   : [],
            'tmax'   : [],
            'rh'     : [],  
            'ws'     : [],  
            'cldflo' : [],  
            'thi_min': [],
            'thi_max': [],
        }

        for day in tqdm(range(10), desc="Processing Days"):
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
            
            rf_cont_plot = pl.contourf(
                zoom(lon,4), zoom(lat,4), zoom(rf_d,4), 
                levels=rf_levels, 
                cmap=bmd_pr_dly_cmap, 
                norm=norm,
                extend='max'
            )
            
            rf_geojson   = gj.contourf_to_geojson(rf_cont_plot)

            with open(
                os.path.join(
                    forecast_out_dir,f'rf{json_suffix}'
                ),'w'
            ) as jfw:
                jfw.write(rf_geojson)

            cbar = pl.colorbar(
                rf_cont_plot, orientation='horizontal', 
                ticks=rf_levels[:-1]
            )
            cbar.set_ticklabels(
                [
                    '1', '10', '20', '40', 
                    '80', '160', '250'
                ]
            )
            cbar.outline.set_visible(False)
            
            ax.remove()
            pl.savefig(os.path.join(forecast_out_dir,f'rf{cmap_suffix}'),pad_inches=0,bbox_inches = 'tight')
            pl.close()

            finfo['rf'].append(
                {
                'file'  : f'rf{json_suffix}',
                'cmap'  : f'rf{cmap_suffix}',
                'start' : start_time_bst,
                'end'   : end_time_bst,
                }
            )
        
        # save forecast info
        with open(os.path.join(f'{forecast_out_dir}',f'info.{fdate}.json'),'w') as infojw:
            json.dump(finfo, infojw)

        # update state
        self.update_state(date_obj, source_obj)