from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import pylab as pl 
import numpy as np
import geojsoncontour as gj 
# import mysql.connector as mconn 
import matplotlib.colors as mplcolors
from netCDF4 import Dataset as nco, num2date
from datetime import datetime as dt, timedelta as delt 
from scipy.ndimage import zoom
from tqdm import tqdm

from app_visualization.models import (
    Source, SystemState
)


from ffwc_django_project.project_constant import app_visualization

SOURCE_ECMWF_HRES = app_visualization['source']['ECMWF_HRES_VIS']
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][1]

ECMWF_BASE_URL = settings.BASE_DIR

class Command(BaseCommand):
    help = 'Generate forecast data for BMDWRF'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')

    
    def calc_rh(self, temp:np.ndarray, dewtemp:np.ndarray)->np.ndarray:
        a = 17.625
        b = 243.04

        es_td = (a * dewtemp) / (b + dewtemp)
        es_t  = (a * temp)    / (b + temp)

        return 100 * ( np.exp(es_td) / np.exp(es_t) )
    
    
    def update_state(self, forecast_date, source_obj):
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
            formatted_date = today_date.strftime('%Y%m%d')
            fdate = formatted_date

        source_obj = Source.objects.filter(
			name='ECMWF_HRES_VIS', source_type="vis",
			source_data_type__name="Forecast"
		)[0]  

        WRF_NC_LOC_ECMWF_HRES = source_obj.source_path
        JSON_OUT_LOC_ECMWF_HRES = source_obj.destination_path
        
        date_obj = dt.strptime(fdate, '%Y%m%d')
        # formatted_date_string = date_obj.strftime('%d%m%Y')
        formatted_date_string = date_obj.strftime('%Y%m%d')
        print(">>>>>>>>>>>>>>>> formatted_date_string: ", formatted_date_string)
        print(">>>>>>>>>>>>>>>> formatted_date_string type: ", type(formatted_date_string))
        print(">>>>>>>>>>>>>>>> date_obj type: ", type(date_obj))

        ncfile = str(ECMWF_BASE_URL)+str(WRF_NC_LOC_ECMWF_HRES)+f'{formatted_date_string}/tp.nc'
        forecast_out_dir = str(ECMWF_BASE_URL)+str(JSON_OUT_LOC_ECMWF_HRES)+str(fdate)
        print("ncfile path: ", ncfile)
        print("forecast_out_dir path: ", forecast_out_dir)

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir)

        # Custom rainfall colormap with discrete boundaries
        rf_colors = ['#00DC00', '#A0E632', '#E6DC32', '#E6AF2D', '#F08228', '#FA3C3C', '#F00082']
        # Define the boundaries for each color
        rf_levels = [1, 10, 20, 40, 80, 160, 250, 1000]  # Added a high upper limit
        bmd_pr_dly_cmap = mplcolors.ListedColormap(rf_colors)
        norm = mplcolors.BoundaryNorm(rf_levels, bmd_pr_dly_cmap.N)

        nf = nco(ncfile, 'r')

        # get vars
        lat      = nf.variables['lat'][:]
        lon      = nf.variables['lon'][:]
        time 	 = nf.variables['time']
        dates 	 = num2date(time[:],time.units,time.calendar)

        # temp     = nf.variables['t2m'][:] - 273.15
        # dewtemp = nf.variables['d2m'][:] - 273.15
        # rh       = self.calc_rh(temp, dewtemp)
        # ws       = np.sqrt( np.square(nf.variables['u10'][:]) + np.square(nf.variables['v10'][:]) ) * 3.6
        # rf       = (nf.variables['lsp'][:] + nf.variables['cp'][:])*1000
        rf       = (nf.variables['tp'][:])*1000
        # thi      = 0.8*temp + (rh/100)*(temp-14.4) + 46.4

        finfo = {
            'fdate'  : fdate,
            'rf'     : [],
        }

        for day in tqdm(range(10), desc="Processing Days"):
            start_step = day*1 
            end_step   = day*1 + 1 

            start_time = dates[start_step].strftime('%Y%m%d%H')
            end_time   = dates[end_step].strftime('%Y%m%d%H')

            start_time_bst = (dt.strptime(start_time,'%Y%m%d%H')).strftime('%Y-%m-%d %H:%M')
            end_time_bst   = (dt.strptime(end_time,'%Y%m%d%H')).strftime('%Y-%m-%d %H:%M')

            json_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.geojson'
            cmap_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.svg'

            if day==0:
                rf_d = rf[end_step,:,:]
            else:
                rf_d = rf[end_step,:,:] - rf[start_step,:,:]

            # tmin_d    = np.amin(temp[start_step:end_step+1,:,:],axis=0) 
            # tmax_d    = np.amax(temp[start_step:end_step+1,:,:],axis=0)
            # rh_d      = np.average(rh[start_step:end_step+1,:,:],axis=0)
            # ws_d      = np.average(ws[start_step:end_step+1,:,:],axis=0) 
            # thi_min_d = np.amin(thi[start_step:end_step+1,:,:],axis=0)
            # thi_max_d = np.amax(thi[start_step:end_step+1,:,:],axis=0)

            # == Rainfall ==
            ax = pl.axes()
            
            # Use discrete colors with BoundaryNorm
            rf_cont_plot = pl.contourf(
                zoom(lon,4), zoom(lat,4), zoom(rf_d, 4), 
                levels=rf_levels, 
                cmap=bmd_pr_dly_cmap, 
                norm=norm,
                extend='max'
            )

            rf_geojson = gj.contourf_to_geojson(rf_cont_plot)

            with open(
                os.path.join(
                    forecast_out_dir,f'rf{json_suffix}'
                    ),'w'
            ) as jfw:
                jfw.write(rf_geojson)

            # Create colorbar with threshold values as labels
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
            pl.savefig(
                os.path.join(
                    forecast_out_dir,f'rf{cmap_suffix}'
                ), pad_inches=0, bbox_inches='tight'
            )
            pl.close()
        
            finfo['rf'].append(
                {
                'file'  : f'rf{json_suffix}',
                'cmap'  : f'rf{cmap_suffix}',
                'start' : start_time_bst,
                'end'   : end_time_bst,
                }
            )

        with open(os.path.join(f'{forecast_out_dir}',f'info.{fdate}.json'),'w') as infojw:
            json.dump(finfo, infojw)
            
        self.update_state(date_obj, source_obj)