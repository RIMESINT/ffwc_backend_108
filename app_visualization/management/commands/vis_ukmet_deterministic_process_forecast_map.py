# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
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

from ffwc_django_project.project_constant import app_visualization
from app_visualization.models import Source, SystemState

SOURCE_NAME = 'UKMET_DETERMINISTIC_VIS'
SYSTEM_STATE_NAME = app_visualization['system_state_name'][12]

class Command(BaseCommand):
    help = 'Generate geojson maps and legends for UKMET (Exact BMD-WRF Style)'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date in YYYYMMDD format')

    def update_state(self, forecast_date, source_obj):
        aware_date = timezone.make_aware(forecast_date) if timezone.is_naive(forecast_date) else forecast_date
        SystemState.objects.update_or_create(
            source=source_obj, 
            name=SYSTEM_STATE_NAME,
            defaults={'last_update': aware_date}
        )

    def handle(self, *args, **kwargs):
        fdate = kwargs.get('fdate') or dt.now().strftime('%Y%m%d')
        
        try:
            source_obj = Source.objects.get(
                name=SOURCE_NAME, 
                source_type="vis",
                source_data_type__name="Forecast"
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Source {SOURCE_NAME} not found: {e}"))
            return

        # Setup Paths
        ncfile = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_{fdate}.nc"
        json_out_rel = source_obj.destination_path
        forecast_out_dir = os.path.join(settings.BASE_DIR, json_out_rel.strip('/'), fdate)
        
        if not os.path.exists(ncfile):
            self.stderr.write(self.style.ERROR(f"File not found: {ncfile}"))
            return

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir)

        # Exact BMD Rainfall Styling
        rf_colors = ['#00DC00', '#A0E632', '#E6DC32', '#E6AF2D', '#F08228', '#FA3C3C', '#F00082']
        rf_levels = [1, 10, 20, 40, 80, 160, 250, 1000]
        bmd_pr_dly_cmap = mplcolors.ListedColormap(rf_colors)
        norm = mplcolors.BoundaryNorm(rf_levels, bmd_pr_dly_cmap.N)

        nf = nco(ncfile, 'r')
        lat = nf.variables['latitude'][:]
        lon = nf.variables['longitude'][:]
        time_var = nf.variables['time']
        dates_raw = num2date(time_var[:], time_var.units, time_var.calendar)
        rf_total = nf.variables['tp'][:] 

        finfo = {
            'fdate'  : fdate,
            'rf'     : [],
            'tmin'   : [], 'tmax': [], 'rh': [], 'ws': [],
            'cldflo' : [], 'thi_min': [], 'thi_max': []
        }

        # Processing loop
        for day_idx in tqdm(range(len(dates_raw)), desc="Processing UKMET Map Layers"):
            
            valid_end_dt = dates_raw[day_idx]
            valid_start_dt = valid_end_dt - delt(days=1)
            
            start_f = valid_start_dt.strftime('%Y%m%d00')
            end_f   = valid_end_dt.strftime('%Y%m%d00')
            start_bst = valid_start_dt.strftime('%Y-%m-%d 06:00')
            end_bst   = valid_end_dt.strftime('%Y-%m-%d 06:00')

            json_suffix = f'.F_{fdate}.S_{start_f}.E_{end_f}.geojson'
            cmap_suffix = f'.F_{fdate}.S_{start_f}.E_{end_f}.svg'

            # UKMET standalone incremental data
            rf_d = rf_total[day_idx, :, :]


            ax = pl.axes()
            

            rf_cont_plot = pl.contourf(
                zoom(lon, 4), zoom(lat, 4), zoom(rf_d, 4), 
                levels=rf_levels, 
                cmap=bmd_pr_dly_cmap, 
                norm=norm,
                extend='max'
            )
            
            # Save GeoJSON
            rf_geojson = gj.contourf_to_geojson(rf_cont_plot)
            with open(os.path.join(forecast_out_dir, f'rf{json_suffix}'), 'w') as jfw:
                jfw.write(rf_geojson)

            cbar = pl.colorbar(
                rf_cont_plot, 
                orientation='horizontal', 
                ticks=rf_levels[:-1]
            )
            cbar.set_ticklabels(['1', '10', '20', '40', '80', '160', '250'])
            cbar.outline.set_visible(False)
            
            ax.remove()
            pl.savefig(
                os.path.join(forecast_out_dir, f'rf{cmap_suffix}'), 
                pad_inches=0, 
                bbox_inches='tight'
            )
            pl.close()

        
            finfo['rf'].append({
                'file'  : f'rf{json_suffix}',
                'cmap'  : f'rf{cmap_suffix}',
                'start' : start_bst,
                'end'   : end_bst,
            })

        with open(os.path.join(forecast_out_dir, f'info.{fdate}.json'), 'w') as infojw:
            json.dump(finfo, infojw, indent=2)
            
        self.update_state(dt.strptime(fdate, '%Y%m%d'), source_obj)
        nf.close()
        self.stdout.write(self.style.SUCCESS(f"Finished UKMET map generation for {fdate}"))