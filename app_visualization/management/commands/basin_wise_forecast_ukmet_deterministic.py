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
    help = 'Generate UKMET Deterministic Basin Forecast from /forecast/ukmet_det_data/'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date in format YYYYMMDD')

    def to_pydt(self, cf_date):
        """Helper to convert netCDF cftime objects to standard python datetime"""
        return pydt.datetime(cf_date.year, cf_date.month, cf_date.day, 
                             cf_date.hour, cf_date.minute, cf_date.second)

    def find_ukmet_file(self, date_str):
        """
        Looks for precip_YYYYMMDD.nc in the specific forecast directory.
        If the requested date is missing, it returns the most recent available .nc file.
        """
        # Path provided: /home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/
        base_dir = os.path.join(BMDWRF_BASE_URL, "forecast", "ukmet_det_data")
        
        # 1. Try specific date
        target_file = os.path.join(base_dir, f"precip_{date_str}.nc")
        if os.path.exists(target_file):
            return target_file, date_str

        # 2. Fallback: Scan for the latest file in that directory
        print(f"!!! File missing: {target_file}. Scanning for latest available...")
        search_pattern = os.path.join(base_dir, "precip_*.nc")
        files = sorted(glob.glob(search_pattern), reverse=True)

        if files:
            latest_file = files[0]
            # Extract date string from filename (assuming precip_YYYYMMDD.nc)
            # Filename is usually 'precip_20260317.nc'
            file_name = os.path.basename(latest_file)
            latest_date_str = file_name.split('_')[1].split('.')[0]
            print(f"Using latest file found: {file_name}")
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
        
        # UKMET Deterministic variable is usually 'tp' (Total Precipitation)
        rf_var = ncf.variables['tp'][:]
        rf_obj = Parameter.objects.get(name='rf')

        for idx, i_shape in enumerate(tqdm(shf, desc=f"Basin: {basin_details.name}")):
            try:
                geom_raw = i_shape.get('geometry')
                if not geom_raw: continue

                shape_obj = shape(geom_raw)
                if shape_obj.is_empty or shape_obj.geom_type not in ['Polygon', 'MultiPolygon']:
                    continue

                pys = scissor(shape_obj, lats, lons)
                weight_grid = pys.get_masked_weight() 

                upazila_data_daily = []
                # Process available days (UKMET is usually 6-7 days)
                num_steps = len(dates_raw)
                for day_idx in range(num_steps - 1):
                    
                    dt_start = timezone.make_aware(self.to_pydt(dates_raw[day_idx]))
                    dt_end   = timezone.make_aware(self.to_pydt(dates_raw[day_idx+1]))

                    # Extract rainfall grid for this step
                    rf_step = rf_var[day_idx, :, :]
                    
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
                # Silently continue to process next basin feature
                continue
        shf.close()

    def update_state(self, forecast_date_str, source_obj):
        date_obj = dt.strptime(forecast_date_str, '%Y-%m-%d')
        aware_date = timezone.make_aware(date_obj)
        SystemState.objects.update_or_create(
            source=source_obj, 
            name=SYSTEM_STATE_NAME_UKMET,
            defaults={'last_update': aware_date}
        )
        print(f"System state updated for UKMET to {forecast_date_str}")

    def main(self, date_str):
        nc_loc, actual_date_str = self.find_ukmet_file(date_str)
        
        if not nc_loc:
            print(f"Error: No UKMET files found in /forecast/ukmet_det_data/")
            return

        forecast_date = dt.strptime(actual_date_str, '%Y%m%d').strftime('%Y-%m-%d')
        
        try:
            source_obj = Source.objects.get(name='UKMET_DETERMINISTIC', source_type="basin_specific")
        except Source.DoesNotExist:
            print("Error: Source 'UKMET_DETERMINISTIC' missing in DB.")
            return

        ncf = nco(nc_loc, 'r')
        # Exclude basins marked as not working
        basin_list = BasinDetails.objects.all().exclude(name__icontains='_not_working')

        for basin in basin_list:
            if basin.shape_file_path:
                file_path = os.path.join(BMDWRF_BASE_URL, basin.shape_file_path.strip('/'))
                if os.path.exists(file_path):
                    # Clean up existing data for this date/source to prevent duplicates
                    ForecastDaily.objects.filter(source=source_obj, forecast_date=forecast_date, basin_details=basin).delete()
                    
                    self.gen_upazila_forecast(forecast_date, source_obj, ncf, file_path, basin)

        self.update_state(forecast_date, source_obj)
        ncf.close()

    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        self.main(fdate)