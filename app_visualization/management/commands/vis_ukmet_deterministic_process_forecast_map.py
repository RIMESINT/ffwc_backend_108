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

# Use your project's constant settings
from ffwc_django_project.project_constant import app_visualization

SOURCE_NAME = 'UKMET_DETERMINISTIC_VIS'
SYSTEM_STATE_NAME = app_visualization['system_state_name'][12]

class Command(BaseCommand):
    help = 'Generate geojson and svg visualization for UKMET Deterministic Forecast'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date in YYYYMMDD format')

    def update_state(self, forecast_date, source_obj):
        state, created = SystemState.objects.update_or_create(
            source=source_obj, 
            name=SYSTEM_STATE_NAME,
            defaults={'last_update': forecast_date}
        )
        if created:
            print(f"Created new SystemState for {SOURCE_NAME}")
        else:
            print(f"Updated existing SystemState for {SOURCE_NAME}")

    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate']
        if fdate is None:
            fdate = dt.now().strftime('%Y%m%d')
        
        print(f"### Generating UKMET Visualization for date: {fdate}")

        # 1. Get Source Configuration
        try:
            source_obj = Source.objects.get(
                name=SOURCE_NAME, 
                source_type="vis",
                source_data_type__name="Forecast"
            )
        except Exception as e:
            self.stderr.write(f"Source {SOURCE_NAME} not found in database: {e}")
            return

        # 2. Setup Paths
        # New requested path
        ncfile = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_{fdate}.nc"
        
        # Output directory using destination_path from DB
        json_out_rel = source_obj.destination_path
        forecast_out_dir = os.path.join(settings.BASE_DIR, json_out_rel.strip('/'), fdate)
        
        print(f"Input file: {ncfile}")
        print(f"Output dir: {forecast_out_dir}")

        if not os.path.exists(ncfile):
            self.stderr.write(f"NetCDF file not found: {ncfile}")
            return

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir)

        # 3. Visualization Styling (Rainfall)
        rf_colors = ['#00DC00', '#A0E632', '#E6DC32', '#E6AF2D', '#F08228', '#FA3C3C', '#F00082']
        rf_levels = [1, 10, 20, 40, 80, 160, 250, 1000]
        bmd_pr_dly_cmap = mplcolors.ListedColormap(rf_colors)
        norm = mplcolors.BoundaryNorm(rf_levels, bmd_pr_dly_cmap.N)

        # 4. Read NetCDF
        nf = nco(ncfile, 'r')
        
        # Based on inspection: coordinates are 'latitude' and 'longitude'
        lat = nf.variables['latitude'][:]
        lon = nf.variables['longitude'][:]
        time_var = nf.variables['time']
        dates = num2date(time_var[:], time_var.units, time_var.calendar)
        
        # Deterministic rainfall variable is 'tp' (Total Precipitation)
        rf = nf.variables['tp'][:] 

        finfo = {
            'fdate'  : fdate,
            'rf'     : [],
        }

        # 5. Process loop (7 days available in UKMET file)
        # Note: Start step and end step are 1:1 since UKMET NC is usually daily aggregated
        for day in tqdm(range(len(dates)), desc="Generating Map Layers"):
            
            current_date_obj = dates[day]
            start_time = current_date_obj.strftime('%Y%m%d')
            start_time_bst = current_date_obj.strftime('%Y-%m-%d')
            
            # File naming conventions
            json_suffix = f'.F_{fdate}.S_{start_time}.E_{start_time}.geojson'
            cmap_suffix = f'.F_{fdate}.S_{start_time}.E_{start_time}.svg'

            # Get 2D slice for the specific day
            rf_d = rf[day, :, :]

            # Visualization Setup
            fig = pl.figure()
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')
            
            # Contour plot for GeoJSON and SVG
            # zoom(..., 4) is used for smoothing high-res data for the web map
            rf_cont_plot = ax.contourf(
                zoom(lon, 2), zoom(lat, 2), zoom(rf_d, 2), 
                levels=rf_levels, 
                cmap=bmd_pr_dly_cmap, 
                norm=norm,
                extend='max'
            )

            # Export to GeoJSON
            rf_geojson = gj.contourf_to_geojson(rf_cont_plot)
            with open(os.path.join(forecast_out_dir, f'rf{json_suffix}'), 'w') as jfw:
                jfw.write(rf_geojson)

            # Export to SVG (Cmap)
            pl.savefig(
                os.path.join(forecast_out_dir, f'rf{cmap_suffix}'), 
                transparent=True, 
                pad_inches=0, 
                bbox_inches='tight'
            )
            pl.close(fig)
        
            finfo['rf'].append({
                'file'  : f'rf{json_suffix}',
                'cmap'  : f'rf{cmap_suffix}',
                'start' : start_time_bst,
                'end'   : start_time_bst, # Same day end since it's a daily slice
            })

        # 6. Save Info JSON
        with open(os.path.join(forecast_out_dir, f'info.{fdate}.json'), 'w') as infojw:
            json.dump(finfo, infojw)
            
        # 7. Update System State
        date_obj = dt.strptime(fdate, '%Y%m%d')
        self.update_state(date_obj, source_obj)
        nf.close()