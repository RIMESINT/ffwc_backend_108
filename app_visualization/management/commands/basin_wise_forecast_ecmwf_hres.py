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
SYSTEM_STATE_NAME_ECMWF_HRES = app_visualization['system_state_name'][4]

def r2(val):
    return np.round(val, 2)

class Command(BaseCommand):
    help = 'Processes ECMWF HRES daily cumulative data starting from Run Date (Index 0)'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date in format YYYYMMDD')

    def handle(self, *args, **kwargs):
        fcst_date = kwargs.get('fdate') or dt.now().strftime('%Y%m%d')
        self.stdout.write(self.style.SUCCESS(f"🚀 Processing Forecast Run: {fcst_date}"))
        self.main(fcst_date)

    def gen_upazila_forecast(self, forecast_date, source_obj, ncf, file_path, basin_details):
        try:
            shf = fiona.open(file_path, 'r') 
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error opening SHP {file_path}: {e}"))
            return

        # 1. Setup Time and Coordinates
        lats, lons = ncf.variables['lat'][:], ncf.variables['lon'][:]
        times_var = ncf.variables['time']
        raw_dates = num2date(times_var[:], times_var.units, times_var.calendar)
        
        # Standardize dates to timezone-aware Python datetimes
        dates = []
        for d in raw_dates:
            std_dt = dt(d.year, d.month, d.day, d.hour, d.minute, d.second)
            dates.append(timezone.make_aware(std_dt) if timezone.is_naive(std_dt) else std_dt)

        # tp is cumulative (meters)
        rf = ncf.variables['tp'][:] * 1000 
        rf_obj = Parameter.objects.get(name='rf')
        
        # Initialization Date (e.g., 2026-03-28)
        run_date_obj = dt.strptime(forecast_date, '%Y-%m-%d').date()

        # Attribute safe check
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

            # 2. Logic: Index 0 is the Run Date's accumulation
            for d_idx in range(len(dates)):
                current_step_dt = dates[d_idx]
                
                if d_idx == 0:
                    # Based on inspection, rf[0] is the 24-hour total for the run date
                    rf_day = rf[0, :, :]
                    # Spans from run_date 00:00 to the first timestamp (next day 00:00)
                    step_start = timezone.make_aware(dt.combine(run_date_obj, dt.min.time()))
                    step_end = current_step_dt
                else:
                    # Standard daily increment: (Current - Previous)
                    rf_day = rf[d_idx, :, :] - rf[d_idx - 1, :, :]
                    step_start = dates[d_idx - 1]
                    step_end = current_step_dt

                # Cleanup numerical noise and spatial averaging
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
            source_obj = Source.objects.get(name='ECMWF_HRES', source_type="basin_specific")
        except Source.DoesNotExist:
            self.stdout.write(self.style.ERROR("ECMWF_HRES source not found in database."))
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
            
            # Final state update
            SystemState.objects.update_or_create(
                source=source_obj, name=SYSTEM_STATE_NAME_ECMWF_HRES,
                defaults={'last_update': forecast_date}
            )
            self.stdout.write(self.style.SUCCESS(f"🏁 Successfully processed run date: {forecast_date}"))