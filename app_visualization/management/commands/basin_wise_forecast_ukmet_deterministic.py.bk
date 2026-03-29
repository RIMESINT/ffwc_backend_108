# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import os, sys, json, numpy as np, fiona, glob
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
SYSTEM_STATE_NAME_UKMET = app_visualization['system_state_name'][13]
BMDWRF_BASE_URL = settings.BASE_DIR

def r2(val):
    return round(float(val), 2) if val is not None else 0.0

class Command(BaseCommand):
    help = 'Generate UKMET Deterministic Basin Forecast (Modified for Incremental Day 0 Data)'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date in format YYYYMMDD')

    def to_pydt(self, cf_date):
        """Helper to convert netCDF cftime objects to standard python datetime"""
        return pydt.datetime(cf_date.year, cf_date.month, cf_date.day, 
                             cf_date.hour, cf_date.minute, cf_date.second)

    def find_ukmet_file(self, date_str):
        base_dir = os.path.join(BMDWRF_BASE_URL, "forecast", "ukmet_det_data")
        target_file = os.path.join(base_dir, f"precip_{date_str}.nc")
        if os.path.exists(target_file):
            return target_file, date_str

        search_pattern = os.path.join(base_dir, "precip_*.nc")
        files = sorted(glob.glob(search_pattern), reverse=True)
        if files:
            latest_file = files[0]
            file_name = os.path.basename(latest_file)
            latest_date_str = file_name.split('_')[1].split('.')[0]
            return latest_file, latest_date_str

        return None, None

    def gen_upazila_forecast(self, forecast_date, source_obj, ncf, file_path, basin_details):
        try:
            shf = fiona.open(file_path, 'r') 
        except:
            return

        lats = ncf.variables['latitude'][:]
        lons = ncf.variables['longitude'][:]
        times = ncf.variables['time']
        dates_raw = num2date(times[:], times.units, times.calendar)
        
        # Based on inspection: Units are mm, Data is incremental
        rf_var = ncf.variables['tp'][:]
        rf_obj = Parameter.objects.get(name='rf')

        # Initialization Date object
        run_date_obj = dt.strptime(forecast_date, '%Y-%m-%d').date()
        
        # Attribute safe check
        b_name = getattr(basin_details, 'name', getattr(basin_details, 'basin_name', f"ID: {basin_details.id}"))

        for idx, i_shape in enumerate(tqdm(shf, desc=f"Basin: {b_name}")):
            try:
                geom_raw = i_shape.get('geometry')
                if not geom_raw: continue

                shape_obj = shape(geom_raw)
                
                # GEOMETRY SANITIZER: Fix self-intersections
                if not shape_obj.is_valid:
                    shape_obj = shape_obj.buffer(0)

                if shape_obj.is_empty or shape_obj.geom_type not in ['Polygon', 'MultiPolygon']:
                    continue

                pys = scissor(shape_obj, lats, lons)
                weight_grid = pys.get_masked_weight() 

                upazila_data_daily = []
                num_steps = len(dates_raw)

                for d_idx in range(num_steps):
                    # Convert NC time to aware DT
                    curr_nc_dt = timezone.make_aware(self.to_pydt(dates_raw[d_idx]))
                    
                    if d_idx == 0:
                        # RECOVERY: Index 0 (March 29 00:00) is the rain for the Run Date (March 28)
                        dt_start = timezone.make_aware(dt.combine(run_date_obj, pydt.time.min))
                        dt_end   = curr_nc_dt
                    else:
                        # Standard sequence
                        dt_start = timezone.make_aware(self.to_pydt(dates_raw[d_idx-1]))
                        dt_end   = curr_nc_dt

                    # Extract rainfall grid for this standalone step (no subtraction needed)
                    rf_step = rf_var[d_idx, :, :]
                    
                    # Zero out numerical noise (negative values)
                    rf_step[rf_step < 0] = 0
                    
                    rf_masked = np.ma.masked_array(rf_step, mask=weight_grid.mask)
                    rf_avg = np.average(rf_step, weights=weight_grid)

                    upazila_data_daily.append(ForecastDaily(
                        parameter=rf_obj,
                        source=source_obj,
                        basin_details=basin_details,
                        step_start=dt_start,
                        step_end=dt_end,
                        forecast_date=forecast_date,
                        val_min=r2(rf_masked.min()),
                        val_avg=r2(rf_avg),
                        val_max=r2(rf_masked.max()),
                    ))

                if upazila_data_daily:
                    ForecastDaily.objects.bulk_create(upazila_data_daily)

            except Exception as e:
                continue
        shf.close()

    def update_state(self, forecast_date_str, source_obj):
        # Update system state last update to the current time (now)
        SystemState.objects.update_or_create(
            source=source_obj, 
            name=SYSTEM_STATE_NAME_UKMET,
            defaults={'last_update': timezone.now()}
        )
        print(f"System state updated for UKMET for run date: {forecast_date_str}")

    def main(self, date_str):
        nc_loc, actual_date_str = self.find_ukmet_file(date_str)
        
        if not nc_loc:
            print(f"Error: No UKMET files found.")
            return

        forecast_date = dt.strptime(actual_date_str, '%Y%m%d').strftime('%Y-%m-%d')
        
        try:
            source_obj = Source.objects.get(name='UKMET_DETERMINISTIC', source_type="basin_specific")
        except Source.DoesNotExist:
            print("Error: Source 'UKMET_DETERMINISTIC' missing in DB.")
            return

        ncf = nco(nc_loc, 'r')
        basin_list = BasinDetails.objects.all().exclude(name__icontains='_not_working')

        for basin in basin_list:
            if basin.shape_file_path:
                file_path = os.path.join(BMDWRF_BASE_URL, basin.shape_file_path.lstrip('/'))
                if os.path.exists(file_path):
                    # Clean up existing data for this specific run and basin
                    ForecastDaily.objects.filter(
                        source=source_obj, 
                        forecast_date=forecast_date, 
                        basin_details=basin
                    ).delete()
                    
                    self.gen_upazila_forecast(forecast_date, source_obj, ncf, file_path, basin)

        self.update_state(forecast_date, source_obj)
        ncf.close()
        print(f"🏁 Finished processing UKMET for {forecast_date}")

    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        self.main(fdate)