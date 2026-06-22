# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import os, sys, json, numpy as np, fiona
import datetime as pydt
from datetime import datetime as dt, timedelta as delt
from pyscissor import scissor 
from netCDF4 import Dataset as nco, num2date
from shapely.geometry import shape
from tqdm import tqdm

from app_visualization.models import (
    Source, Parameter, ForecastDaily, SystemState,  
    BasinDetails, ForecastSteps
)
from ffwc_django_project.project_constant import app_visualization

# Constants
# Changed to index [4] to correspond with BMDWRF basin_specific source intent
SYSTEM_STATE_NAME_BMD = app_visualization['system_state_name'][4]
BMDWRF_BASE_URL = settings.BASE_DIR

def r2(val):
    return round(val, 2) if val is not None else 0.0

class Command(BaseCommand):
    help = 'Process BMDWRF NetCDF into ForecastDaily for Source ID 4 (BMDWRF)'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date in format YYYYMMDD')

    def to_pydt(self, cf_date):
        """Helper to convert netCDF cftime objects to standard python datetime"""
        return pydt.datetime(cf_date.year, cf_date.month, cf_date.day, 
                             cf_date.hour, cf_date.minute, cf_date.second)

    def gen_upazila_forecast(self, forecast_date, source_obj, ncf, file_path, basin_details):
        try:
            shf = fiona.open(file_path, 'r') 
        except Exception as e:
            print(f"Error opening {file_path}: {e}")
            return

        lats = ncf.variables['lat'][:]
        lons = ncf.variables['lon'][:]
        times = ncf.variables['time']
        dates_raw = num2date(times[:], times.units, times.calendar)
        
        # Rainfall calculation
        rf_total = ncf.variables['rainc'][:] + ncf.variables['rainnc'][:]
        rf_obj = Parameter.objects.get(name='rf')

        for idx, i_shape in enumerate(tqdm(shf, desc=f"Processing {basin_details.name}")):
            try:
                geom_raw = i_shape.get('geometry')
                if not geom_raw:
                    continue

                shape_obj = shape(geom_raw)
                if shape_obj.is_empty or shape_obj.geom_type not in ['Polygon', 'MultiPolygon']:
                    continue

                pys = scissor(shape_obj, lats, lons)
                weight_grid = pys.get_masked_weight() 

                # Process 10 Days
                upazila_data_daily = []
                for day in range(10):
                    day_start_idx = (day) * 8
                    day_end_idx   = (day + 1) * 8
                    
                    # Convert cftime to Timezone-Aware Python Datetime
                    dt_start = timezone.make_aware(self.to_pydt(dates_raw[day_start_idx]))
                    dt_end   = timezone.make_aware(self.to_pydt(dates_raw[day_end_idx]))

                    rf_day = rf_total[day_end_idx, 0, :, :] - rf_total[day_start_idx, 0, :, :]
                    
                    rf_day_masked  = np.ma.masked_array(rf_day, mask=weight_grid.mask)
                    rf_max_val_day = rf_day_masked.max()
                    rf_min_val_day = rf_day_masked.min()
                    rf_avg_val_day = np.average(rf_day, weights=weight_grid)

                    upazila_data_daily.append(ForecastDaily(
                        parameter=rf_obj,
                        source=source_obj, 
                        basin_details=basin_details,
                        step_start=dt_start,
                        step_end=dt_end,
                        forecast_date=forecast_date,
                        val_min=r2(rf_min_val_day),
                        val_avg=r2(rf_avg_val_day),
                        val_max=r2(rf_max_val_day),
                    ))

                if upazila_data_daily:
                    ForecastDaily.objects.bulk_create(upazila_data_daily)

                # Process 3-Hourly Steps
                upazila_data_steps = []
                for t_step in range(0, 32):
                    s_idx, e_idx = t_step, t_step + 1
                    dt_s = timezone.make_aware(self.to_pydt(dates_raw[s_idx]) + delt(hours=6))
                    dt_e = timezone.make_aware(self.to_pydt(dates_raw[e_idx]) + delt(hours=6))

                    rf_step = rf_total[e_idx, 0, :, :] - rf_total[s_idx, 0, :, :]
                    rf_avg_step = np.average(rf_step, weights=weight_grid)

                    upazila_data_steps.append(ForecastSteps(
                        parameter=rf_obj,
                        source=source_obj,
                        basin_details=basin_details,
                        step_start=dt_s,
                        step_end=dt_e,
                        forecast_date=forecast_date,
                        val_max=r2(rf_avg_step)
                    ))
                
                if upazila_data_steps:
                    ForecastSteps.objects.bulk_create(upazila_data_steps)

            except Exception as e:
                print(f"\n[CRITICAL ERROR] Failed index {idx} in {basin_details.name}: {e}")
                continue
        
        shf.close()

    def update_state(self, forecast_date_str, source_obj):
        date_obj = dt.strptime(forecast_date_str, '%Y-%m-%d')
        aware_date = timezone.make_aware(date_obj)
        SystemState.objects.update_or_create(
            source=source_obj, 
            name=SYSTEM_STATE_NAME_BMD,
            defaults={'last_update': aware_date}
        )
        print(f"System state updated for {source_obj.name}")

    def main(self, date_str):
        forecast_date = dt.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d') 
        
        # TARGET SOURCE ID 4 (BMDWRF / basin_specific)
        try:
            source_obj = Source.objects.get(pk=4)
        except Source.DoesNotExist:
            # Fallback by name/type if ID is not exactly 4
            source_obj = Source.objects.get(
                name='BMDWRF', 
                source_type="basin_specific"
            )

        # Get the directory path directly from source_obj (ID 4)
        nc_dir = source_obj.source_path
        nc_loc = os.path.join(BMDWRF_BASE_URL, nc_dir.strip('/'), f'wrf_out_{date_str}00.nc')
        
        if not os.path.exists(nc_loc):
            print(f"Error: NC file not found at {nc_loc}")
            return

        ncf = nco(nc_loc, 'r')
        basin_list = BasinDetails.objects.all()

        for basin in basin_list:
            if basin.shape_file_path:
                file_path = os.path.join(BMDWRF_BASE_URL, basin.shape_file_path.strip('/'))
                if os.path.exists(file_path):
                    self.gen_upazila_forecast(forecast_date, source_obj, ncf, file_path, basin)

        self.update_state(forecast_date, source_obj)
        ncf.close()

    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        self.main(fdate)