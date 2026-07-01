# management/commands/vis_ecmwf_hres_process_forecast_map.py

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import pylab as pl 
import numpy as np
import geojsoncontour as gj 
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
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][2]
ECMWF_BASE_URL = settings.BASE_DIR

class Command(BaseCommand):
    help = 'Generate forecast maps and GeoJSON data for ECMWF HRES'

    def add_arguments(self, parser):
        # 1. Positional argument support for manual CLI execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def update_state(self, forecast_date, source_obj):
        """Update system state last update time"""
        state_query = SystemState.objects.filter(source=source_obj, name=SYSTEM_STATE_NAME_ECMWF_HRES)
        if not state_query.exists():
            print('State does not exist. Creating...')
            SystemState(source=source_obj, last_update=forecast_date, name=SYSTEM_STATE_NAME_ECMWF_HRES).save()	
        else:
            print('State exists. Updating...')
            update_state = state_query.first()
            update_state.last_update = forecast_date
            update_state.save()

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if raw_date:
            # Clean dashboard template dashes safely: '2026-07-01' -> '20260701'
            fdate = raw_date.replace('-', '')
            print(f"###### Received date parameter: {raw_date} -> Normalized to: {fdate}")
        else:
            fdate = dt.now().strftime('%Y%m%d')
            print(f"###### No date provided. Defaulting to system time: {fdate}")
        
        # Resolve source visualization tracking parameters
        try:
            source_obj = Source.objects.get(pk=SOURCE_ECMWF_HRES)
        except Source.DoesNotExist:
            source_obj = Source.objects.filter(name='ECMWF_HRES_VIS', source_type="vis").first()

        if not source_obj:
            self.stdout.write(self.style.ERROR("Database configuration error: Source 'ECMWF_HRES_VIS' metadata not found."))
            return

        WRF_NC_LOC = source_obj.source_path
        JSON_OUT_LOC = source_obj.destination_path

        date_obj = dt.strptime(fdate, '%Y%m%d')
        
        # Construct absolute routing targets
        ncfile = os.path.join(str(ECMWF_BASE_URL), WRF_NC_LOC.strip('/'), fdate, 'tp.nc')
        forecast_out_dir = os.path.join(str(ECMWF_BASE_URL), JSON_OUT_LOC.strip('/'), fdate)
        
        print(" $$$$$$$$$$$ ncfile: ", ncfile)
        print(" $$$$$$$$$$$ forecast_out_dir: ", forecast_out_dir)

        if not os.path.exists(ncfile):
            self.stdout.write(self.style.ERROR(f"Target NetCDF file not found at: {ncfile}"))
            return

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir, exist_ok=True)

        # ECMWF Rainfall Colormap configuration boundaries
        rf_colors = ['#00DC00', '#A0E632', '#E6DC32', '#E6AF2D', '#F08228', '#FA3C3C', '#F00082']
        rf_levels = [1, 10, 20, 40, 80, 160, 250, 1000]  
        bmd_pr_dly_cmap = mplcolors.ListedColormap(rf_colors)
        norm = mplcolors.BoundaryNorm(rf_levels, bmd_pr_dly_cmap.N)
        
        nf = nco(ncfile, 'r')

        # Extract spatial dimensions and time axes coordinates
        lat = nf.variables['lat'][:]
        lon = nf.variables['lon'][:]
        time = nf.variables['time']
        dates = num2date(time[:], time.units, time.calendar)

        # Cumulative rainfall collection variable array
        rf = nf.variables['tp'][:]

        finfo = {
            'fdate': fdate,
            'rf': [], 'tmin': [], 'tmax': [], 'rh': [], 
            'ws': [], 'cldflo': [], 'thi_min': [], 'thi_max': [],
        }

        # Calculate time steps (ECMWF files hold 11 complete forecast steps)
        num_steps = len(dates)
        available_days = int((num_steps - 1) / 8)

        for day in tqdm(range(available_days), desc="Processing Visualization Days"):
            start_step = day * 8 
            end_step = day * 8 + 8 

            if end_step >= num_steps:
                break

            start_time = dates[start_step].strftime('%Y%m%d%H')
            end_time = dates[end_step].strftime('%Y%m%d%H')

            start_time_bst = (dt.strptime(start_time, '%Y%m%d%H') + delt(hours=6)).strftime('%Y-%m-%d %H:%M')
            end_time_bst = (dt.strptime(end_time, '%Y%m%d%H') + delt(hours=6)).strftime('%Y-%m-%d %H:%M')

            json_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.geojson'
            cmap_suffix = f'.F_{fdate}.S_{start_time}.E_{end_time}.svg'

            # De-accumulate cumulative total to obtain daily increments
            rf_d = rf[end_step, :, :] - rf[start_step, :, :]
            rf_d = np.maximum(0, rf_d)

            # == Generate Raster Layer Visuals ==
            ax = pl.axes()
            
            rf_cont_plot = pl.contourf(
                zoom(lon, 4), zoom(lat, 4), zoom(rf_d, 4), 
                levels=rf_levels, 
                cmap=bmd_pr_dly_cmap, 
                norm=norm,
                extend='max'
            )
            
            rf_geojson = gj.contourf_to_geojson(rf_cont_plot)

            with open(os.path.join(forecast_out_dir, f'rf{json_suffix}'), 'w') as jfw:
                jfw.write(rf_geojson)

            cbar = pl.colorbar(
                rf_cont_plot, orientation='horizontal', 
                ticks=rf_levels[:-1]
            )
            cbar.set_ticklabels(['1', '10', '20', '40', '80', '160', '250'])
            cbar.outline.set_visible(False)
            
            ax.remove()
            pl.savefig(os.path.join(forecast_out_dir, f'rf{cmap_suffix}'), pad_inches=0, bbox_inches='tight')
            pl.close()

            finfo['rf'].append({
                'file': f'rf{json_suffix}',
                'cmap': f'rf{cmap_suffix}',
                'start': start_time_bst,
                'end': end_time_bst,
            })
        
        # Save structural metadata file
        with open(os.path.join(forecast_out_dir, f'info.{fdate}.json'), 'w') as infojw:
            json.dump(finfo, infojw)

        # Commit system telemetry update tracking
        self.update_state(date_obj, source_obj)
        nf.close()