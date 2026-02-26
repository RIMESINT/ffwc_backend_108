# management/commands/generate_forecast_data.py

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
import datetime as datetime_pkg
from scipy.ndimage import zoom
from tqdm import tqdm

from app_visualization.models import (
    Source, SystemState
)


from ffwc_django_project.project_constant import app_visualization
# WRF_NC_LOC_ECMWF_HRES = app_visualization['ecmwf_hres']['WRF_NC_LOC_ECMWF_HRES']
# JSON_OUT_LOC_ECMWF_HRES = app_visualization['ecmwf_hres']['JSON_OUT_LOC_ECMWF_HRES']

SOURCE_ECMWF_HRES = app_visualization['source']['ECMWF_HRES_VIS']
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][12]

ECMWF_BASE_URL = settings.BASE_DIR










class Command(BaseCommand):
    help = 'Generate forecast data for BMDWRF'

    def add_arguments(self, parser): 
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')
    
    
    def day_of_year(self, year, month, day):
        """
        Returns the day number within the year for the given date.
        E.g. June 1, 2025 → 152
        """
        date_obj = datetime_pkg.date(int(year), int(month), int(day))
        day_number = date_obj.timetuple().tm_yday
        day_number_str = str(day_number)
        if len(day_number_str)==1:
            day_number_str = '00'+day_number_str
        elif len(day_number_str)==2:
            day_number_str = '0'+day_number_str
        return day_number_str
    
    
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
            yesterday_date = today_date - delt(days=1)
            formatted_date = yesterday_date.strftime('%Y%m%d')  # Date format = YYYYMMDD
            # print("formatted_date: ", formatted_date)
            fdate = formatted_date
        print(" $$$$$ fdate: ", fdate) 

        day_of_year_obj = self.day_of_year(fdate[:4], fdate[4:6], fdate[6:])
        print(" $$$$$ day_of_year_obj: ", day_of_year_obj) 
        nc_file_name_format = str(fdate[:4]) + day_of_year_obj
        
        source_obj = Source.objects.filter(
			name='MSWEP_OBS', source_type="vis",
			source_data_type__name="Observed"
		)[0]  

        WRF_NC_LOC_ECMWF_HRES = source_obj.source_path
        JSON_OUT_LOC_ECMWF_HRES = source_obj.destination_path
        
        # read nc 
        date_obj = dt.strptime(fdate, '%Y%m%d') 

        ncfile 			 = str(ECMWF_BASE_URL)+str(WRF_NC_LOC_ECMWF_HRES)+f'{nc_file_name_format}.nc'
        forecast_out_dir = str(ECMWF_BASE_URL)+str(JSON_OUT_LOC_ECMWF_HRES)+str(fdate)
        print("ncfile path: ", ncfile)
        print("forecast_out_dir path: ", forecast_out_dir)

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir)
        # return

        #bmd rainfall colormap
        rf_colors=['#00dc00','#a0e632','#e6dc32','#e6af2d','#f08228','#fa3c3c','#f00082']
        rf_lvls = np.array([1,5,10,20,30,40,60,70,80])
        bmd_pr_dly_cmap = mplcolors.LinearSegmentedColormap.from_list('bmd_pr_dly_cmap',rf_colors)

        nf = nco(ncfile, 'r')

        # get vars
        lat      = nf.variables['lat'][:]
        lon      = nf.variables['lon'][:]
        time 	 = nf.variables['time']
        # dates 	 = num2date(time[:],time.units,time.calendar)
        dates = num2date(time[:], time.units, getattr(time, 'calendar', 'standard'))

        
        rf       = nf.variables['precipitation'][:]
        # rf       = (nf.variables['lsp'][:] + nf.variables['cp'][:])*1000 # m2mm : *1000 

        # generate daily rainfall geojson
        # 81 steps
        finfo = {
            'fdate'  : fdate,
            'rf'     : [],
        }

        for day in tqdm(range(1), desc="Processing Days"): 

            start_step = day    
            end_step   = day    

            start_time = dates[start_step].strftime('%Y%m%d%H')
            end_time   = dates[end_step].strftime('%Y%m%d%H')

            start_time_bst = (dt.strptime(start_time,'%Y%m%d%H')+delt(hours=6)).strftime('%Y-%m-%d %H:%M')
            end_time_bst   = (dt.strptime(end_time,'%Y%m%d%H')+delt(hours=6)).strftime('%Y-%m-%d %H:%M')


            json_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.geojson'
            cmap_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.svg'


            if day==0:
                rf_d = rf[end_step,:,:]
            else:
                rf_d = rf[end_step,:,:] - rf[start_step,:,:]
            # rf_d      = rf[end_step] - rf[start_step]
            # print("rf_d: ", rf_d)
            
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

            # generate finfo.json
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

