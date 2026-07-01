# management/commands/vis_imd_wrf_process_forecast_map.py

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

from app_visualization.models import Source, SystemState
from ffwc_django_project.project_constant import app_visualization

SOURCE_NAME = 'IMD_WRF_VIS'
SYSTEM_STATE_NAME = app_visualization['system_state_name'][2]
IMD_WRF_BASE_URL = settings.BASE_DIR

class Command(BaseCommand):
    help = 'Generate geojson and svg colorbar legends for IMD WRF Forecast Maps'

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Date in YYYYMMDD format')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def update_state(self, forecast_date, source_obj):
        SystemState.objects.update_or_create(
            source=source_obj, 
            name=SYSTEM_STATE_NAME,
            defaults={'last_update': forecast_date}
        )

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if raw_date:
            fdate = raw_date.replace('-', '')
            self.stdout.write(self.style.SUCCESS(f"###### Received date parameter: {raw_date} -> Normalized to: {fdate}"))
        else:
            fdate = dt.now().strftime('%Y%m%d')
            self.stdout.write(self.style.NOTICE(f"###### No date provided. Defaulting to system time: {fdate}"))

        try:
            source_obj = Source.objects.get(
                name=SOURCE_NAME, 
                source_type="vis",
                source_data_type__name="Forecast"
            )
        except Exception as e:
            self.stderr.write(f"Source {SOURCE_NAME} not found: {e}")
            return

        # Setup Paths
        WRF_NC_LOC = source_obj.source_path
        JSON_OUT_LOC = source_obj.destination_path
        ncfile = os.path.join(IMD_WRF_BASE_URL, WRF_NC_LOC.strip('/'), fdate, 'tp.nc')
        forecast_out_dir = os.path.join(IMD_WRF_BASE_URL, JSON_OUT_LOC.strip('/'), fdate)

        if not os.path.exists(ncfile):
            self.stderr.write(f"File not found: {ncfile}")
            return

        if not os.path.exists(forecast_out_dir):
            os.makedirs(forecast_out_dir)

        # Visualization Styling
        rf_colors = ['#00DC00', '#A0E632', '#E6DC32', '#E6AF2D', '#F08228', '#FA3C3C', '#F00082']
        rf_levels = [1, 10, 20, 40, 80, 160, 250, 1000]
        bmd_pr_dly_cmap = mplcolors.ListedColormap(rf_colors)
        norm = mplcolors.BoundaryNorm(rf_levels, bmd_pr_dly_cmap.N)

        # Read NetCDF
        nf = nco(ncfile, 'r')
        lat = nf.variables['lat'][:]
        lon = nf.variables['lon'][:]
        time_var = nf.variables['time']
        dates_raw = num2date(time_var[:], time_var.units, time_var.calendar)
        
        # Determine variable target name dynamically
        target_var = 'APCP_surface' if 'APCP_surface' in nf.variables else 'tp'
        rf = nf.variables[target_var][:]

        finfo = {
            'fdate' : fdate,
            'rf'    : [],
        }

        num_steps = len(dates_raw)
        
        # Process available forecast cycles step-by-step
        for day in tqdm(range(num_steps - 1), desc="Processing IMD WRF Map Layers"):
            valid_start_dt = dates_raw[day]
            valid_end_dt = dates_raw[day + 1]
            
            start_f = valid_start_dt.strftime('%Y%m%d%H')
            end_f   = valid_end_dt.strftime('%Y%m%d%H')
            
            start_bst = (valid_start_dt + delt(hours=6)).strftime('%Y-%m-%d %H:%M')
            end_bst   = (valid_end_dt + delt(hours=6)).strftime('%Y-%m-%d %H:%M')

            json_suffix = f'.F_{fdate}.S_{start_f}.E_{end_f}.geojson'
            cmap_suffix = f'.F_{fdate}.S_{start_f}.E_{end_f}.svg'

            # Calculate slice intervals from accumulation steps
            rf_d = rf[day + 1, :, :] - rf[day, :, :]
            rf_d = np.maximum(rf_d, 0)

            # --- 1. Generate GeoJSON Map Layer ---
            fig_map = pl.figure()
            ax_map = fig_map.add_axes([0, 0, 1, 1])
            ax_map.axis('off')
            
            rf_cont_plot = ax_map.contourf(
                zoom(lon, 4), zoom(lat, 4), zoom(rf_d, 4), 
                levels=rf_levels, 
                cmap=bmd_pr_dly_cmap, 
                norm=norm,
                extend='max'
            )

            rf_geojson = gj.contourf_to_geojson(rf_cont_plot)
            with open(os.path.join(forecast_out_dir, f'rf{json_suffix}'), 'w') as jfw:
                jfw.write(rf_geojson)
            pl.close(fig_map)

            # --- 2. Generate SVG Legend ---
            ax_leg = pl.axes()
            rf_leg_plot = pl.contourf(
                zoom(lon, 2), zoom(lat, 2), zoom(rf_d, 2), 
                levels=rf_levels, 
                cmap=bmd_pr_dly_cmap, 
                norm=norm,
                extend='max'
            )
            
            cbar = pl.colorbar(
                rf_leg_plot, 
                orientation='horizontal', 
                ticks=rf_levels[:-1]
            )
            cbar.set_ticklabels(['1', '10', '20', '40', '80', '160', '250'])
            cbar.outline.set_visible(False)
            
            ax_leg.remove()
            pl.savefig(
                os.path.join(forecast_out_dir, f'rf{cmap_suffix}'), 
                transparent=True, 
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

        # Save Structural Info Metadata
        with open(os.path.join(forecast_out_dir, f'info.{fdate}.json'), 'w') as infojw:
            json.dump(finfo, infojw, indent=2)
            
        # Update Telemetry State Record
        self.update_state(dt.strptime(fdate, '%Y%m%d'), source_obj)
        nf.close()