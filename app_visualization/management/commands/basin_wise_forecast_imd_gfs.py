# -*- coding: utf-8 -*-
import os
import numpy as np
import fiona
import warnings
from datetime import datetime as dt, timedelta as delt
from tqdm import tqdm

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from pyscissor import scissor 
from netCDF4 import Dataset as nco, num2date
from shapely.geometry import shape

from app_visualization.models import (
    Source, Parameter, ForecastDaily, SystemState, BasinDetails
)
from ffwc_django_project.project_constant import app_visualization

# Constants
BMDWRF_BASE_URL = settings.BASE_DIR
SYSTEM_STATE_NAME_IMD_GFS = app_visualization['system_state_name'][5]

def r2(val):
    if val is None or np.isnan(val):
        return 0.0
    return max(0.0, np.round(float(val), 2))

class Command(BaseCommand):
    help = 'Processes IMD GFS daily cumulative data and performs weighted spatial grid averaging'

    def add_arguments(self, parser):
        # 1. Support positional arguments for direct crontab entries or manual console executions
        parser.add_argument('fdate', nargs='?', type=str, help='Date in format YYYYMMDD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if raw_date:
            fcst_date = raw_date.replace('-', '')
            self.stdout.write(self.style.SUCCESS(f"###### Received date parameter: {raw_date} -> Normalized to: {fcst_date}"))
        else:
            fcst_date = dt.now().strftime('%Y%m%d')
            self.stdout.write(self.style.NOTICE(f"###### No date provided. Defaulting to system date: {fcst_date}"))

        self.main(fcst_date)

    def gen_upazila_forecast(self, forecast_date, source_obj, ncf, file_path, basin_details):
        try:
            shf = fiona.open(file_path, 'r') 
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error opening SHP {file_path}: {e}"))
            return

        lats, lons = ncf.variables['lat'][:], ncf.variables['lon'][:]
        times_var = ncf.variables['time']
        raw_dates = num2date(times_var[:], times_var.units, times_var.calendar)
        
        dates = []
        for d in raw_dates:
            std_dt = dt(d.year, d.month, d.day, d.hour, d.minute, d.second)
            dates.append(timezone.make_aware(std_dt) if timezone.is_naive(std_dt) else std_dt)

        # Determine variable target name dynamically based on source definitions
        target_var = 'APCP_surface' if 'APCP_surface' in ncf.variables else 'tp'
        rf = ncf.variables[target_var][:]
        rf_obj = Parameter.objects.get(name='rf')
        
        run_date_obj = dt.strptime(forecast_date, '%Y-%m-%d').date()
        display_name = getattr(basin_details, 'basin_name', getattr(basin_details, 'name', f"Basin_{basin_details.id}"))

        for idx, i_shape in enumerate(tqdm(shf, desc=f"Extracting: {display_name}")):
            try:
                geom = shape(i_shape['geometry'])
                if not geom.is_valid: geom = geom.buffer(0)
                if geom.geom_type not in ['Polygon', 'MultiPolygon'] or geom.is_empty: continue
                
                pys = scissor(geom, lats, lons)
                weight_grid = pys.get_masked_weight() 
            except Exception: continue

            upazila_data_daily = []

            for d_idx in range(len(dates) - 1):
                step_start = dates[d_idx]
                step_end = dates[d_idx + 1]

                # De-accumulate total steps cleanly to pull incremental rainfall boundaries
                rf_day = rf[d_idx + 1, :, :] - rf[d_idx, :, :]

                rf_day[rf_day < 0] = 0
                rf_day_masked = np.ma.masked_array(rf_day, mask=weight_grid.mask)
                avg_val = np.average(rf_day, weights=weight_grid)

                upazila_data_daily.append(ForecastDaily(
                    parameter=rf_obj,
                    source=source_obj,
                    basin_details=basin_details,     
                    step_start=step_start,
                    step_end=step_end,
                    forecast_date=forecast_date,
                    val_min=r2(rf_day_masked.min()),
                    val_avg=r2(avg_val),
                    val_max=r2(rf_day_masked.max()),
                    val_avg_day=0,
                    val_avg_night=0,
                ))
                
                if len(upazila_data_daily) >= 10: break

            if upazila_data_daily:
                ForecastDaily.objects.bulk_create(upazila_data_daily)
        
        shf.close()

    def main(self, date_str):
        forecast_date = dt.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        
        try:
            source_obj = Source.objects.get(name='IMD_GFS', source_type="basin_specific")
        except Source.DoesNotExist:
            self.stdout.write(self.style.ERROR("IMD_GFS source not found in database configuration mappings."))
            return

        nc_loc = os.path.join(BMDWRF_BASE_URL, source_obj.source_path.lstrip('/'), date_str, 'tp.nc')

        if not os.path.exists(nc_loc):
            self.stdout.write(self.style.ERROR(f"File not found: {nc_loc}"))
            return

        with nco(nc_loc, 'r') as ncf:
            basins = BasinDetails.objects.all()
            for basin in basins:
                shp_path = os.path.join(BMDWRF_BASE_URL, basin.shape_file_path.lstrip('/'))
                if os.path.exists(shp_path):
                    self.gen_upazila_forecast(forecast_date, source_obj, ncf, shp_path, basin)
            
            SystemState.objects.update_or_create(
                source=source_obj, name=SYSTEM_STATE_NAME_IMD_GFS,
                defaults={'last_update': forecast_date}
            )
            self.stdout.write(self.style.SUCCESS(f"🏁 Successfully processed run date: {forecast_date}"))