# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime, timedelta
import pandas as pd
import geopandas as gpd
from pyidw import idw
import rasterio
import numpy as np
from scipy.ndimage import gaussian_filter
from rasterio.features import geometry_mask
import os
import matplotlib.pyplot as plt
import matplotlib.contour as cntr
from shapely.geometry import LineString, Point
import json
from data_load.models import RainfallObservation, RainfallStation

class Command(BaseCommand):
    help = 'Generate Rainfall Distribution Map (V2) using latest database indices with Day-1 Fallback'

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Target date in YYYYMMDD format')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Target date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if not raw_date:
            latest_observation = RainfallObservation.objects.filter(
                rainfall__gte=0
            ).order_by('-observation_date').first()
            
            if latest_observation:
                date_input = latest_observation.observation_date.strftime('%Y-%m-%d')
                self.stdout.write(f"Latest Date pulled from Database: {latest_observation.observation_date}")
            else:
                date_input = datetime.today().strftime('%Y-%m-%d')
                self.stdout.write(f"No valid data found anywhere, defaulting to current system date: {date_input}")
        else:
            date_input = raw_date
            if "-" not in date_input:
                try:
                    date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
                except:
                    pass

        # Execute processing chain with recursive historical day fallbacks
        if not self.run_pipeline_for_date(date_input):
            try:
                current_dt = datetime.strptime(date_input, '%Y-%m-%d')
                yesterday_str = (current_dt - timedelta(days=1)).strftime('%Y-%m-%d')
                self.stdout.write(self.style.WARNING(f"⚠️ Data missing for target date: {date_input}. Attempting historical fallback to: {yesterday_str}..."))
                self.run_pipeline_for_date(yesterday_str)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Critical failure executing date fallback processing chain: {str(e)}"))

    def run_pipeline_for_date(self, date_input):
        self.stdout.write(self.style.NOTICE(f"--- Processing Rainfall Distribution Map V2 for: {date_input} ---"))
        extent_shapefile = os.path.join(settings.BASE_DIR, 'assets', 'shapes', 'Bangladesh_Border.shp')
        
        geoRainfall, allDF = self.generateGeoRainfall(date_input)
        
        # If both tracking metrics are empty, signal failure to trigger fallback loop
        if geoRainfall.empty and allDF.empty:
            return False
            
        self.generateTiff(extent_shapefile, geoRainfall, allDF, date_input)
        return True

    def fromSql(self, dateInput):
        try:
            if dateInput:
                observedDate = datetime.strptime(dateInput, '%Y-%m-%d')
                rainfall_data = RainfallObservation.objects.filter(
                    observation_date__year=observedDate.year,
                    observation_date__month=observedDate.month,
                    observation_date__day=observedDate.day,
                ).values('station_id__station_code', 'observation_date', 'rainfall')
            else:
                latest_observation = RainfallObservation.objects.filter(
                    rainfall__gte=0
                ).order_by('-observation_date').first()
                
                if not latest_observation:
                    print("No valid rainfall data found.")
                    return pd.DataFrame(), pd.DataFrame()
                
                latest_rf_date = latest_observation.observation_date
                rainfall_data = RainfallObservation.objects.filter(
                    observation_date=latest_rf_date,
                ).values('station_id__station_code', 'observation_date', 'rainfall')
            
            rainfall_data = pd.DataFrame(list(rainfall_data))
            
            if rainfall_data.empty:
                print(f"No rainfall data for {dateInput}.")
                return pd.DataFrame(), pd.DataFrame()
            
            # Rename columns for consistency
            rainfall_data.rename(columns={
                'station_id__station_code': 'st_id',
                'observation_date': 'rf_date'
            }, inplace=True)

            all_data = rainfall_data.copy()
            all_data['rainfall'] = all_data['rainfall'].replace(-9999.0, np.nan)
            
            valid_data = rainfall_data[rainfall_data['rainfall'] >= 0].copy()
            if valid_data.empty:
                print(f"No valid rainfall data (rainfall >= 0) for {dateInput}.")
                return pd.DataFrame(), all_data
            
            stations = RainfallStation.objects.all().values('station_code', 'name')
            stations_df = pd.DataFrame(list(stations))
            
            all_data_with_names = all_data.merge(stations_df, how='left', left_on='st_id', right_on='station_code')
            
            target_st_codes = [19, 15, 14, 18]
            for st_code in target_st_codes:
                station_data = all_data_with_names[all_data_with_names['st_id'] == st_code]
                if not station_data.empty:
                    station_name = station_data['name'].iloc[0] if pd.notna(station_data['name'].iloc[0]) else "Unknown"
                    print(f"Rainfall value for {station_name} (st_id {st_code}): {station_data['rainfall'].iloc[0]} mm")
            
            return valid_data[['st_id', 'rf_date', 'rainfall']], all_data[['st_id', 'rf_date', 'rainfall']]
        
        except Exception as e:
            print(f"Error querying database: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def generateGeoRainfall(self, dateInput):
        validDF, allDF = self.fromSql(dateInput)
        if validDF.empty and allDF.empty:
            return gpd.GeoDataFrame(), pd.DataFrame()

        if validDF.empty:
            print("No valid positive rainfall values available for mapping.")
            return gpd.GeoDataFrame(), allDF

        validDF = validDF[['st_id', 'rainfall']].copy(deep=True)
        validDF.sort_values(by=["st_id"], inplace=True)
        validDF.reset_index(drop=True, inplace=True)

        try:
            rainfall_stations = RainfallStation.objects.all().values('station_code', 'name', 'latitude', 'longitude')
            rainfall_stations_df = pd.DataFrame(list(rainfall_stations))
        except Exception as e:
            print(f"Error querying RainfallStation: {e}")
            return gpd.GeoDataFrame(), allDF

        rainfall_stations_df = rainfall_stations_df.merge(validDF, how='inner', left_on='station_code', right_on='st_id')
        if rainfall_stations_df.empty:
            return gpd.GeoDataFrame(), allDF

        geoRainfall = gpd.GeoDataFrame(
            rainfall_stations_df,
            geometry=gpd.points_from_xy(rainfall_stations_df.longitude, rainfall_stations_df.latitude)
        )
        geoRainfall = geoRainfall.set_crs(4326, allow_override=True)

        return geoRainfall, allDF

    def generateTiff(self, extent_shapefile, geoRainfall, allDF, dateInput):
        idw.blank_raster(extent_shapefile)
        blank_filename = extent_shapefile.rsplit('.', 1)[0] + '_blank.tif'
        output_resolution = 1000
        idw.crop_resize(
            input_raster_filename=blank_filename,
            extent_shapefile_name=extent_shapefile,
            max_height_or_width=output_resolution
        )
        resized_raster_name = blank_filename.rsplit('.', 1)[0] + '_resized.tif'

        with rasterio.open(resized_raster_name) as baseRasterFile:
            meta = baseRasterFile.meta.copy()
            output_filename = os.path.join(settings.BASE_DIR, 'assets', 'tiffOutput', f'rainfall_distribution_idw_{dateInput}.tif')

            if os.path.exists(output_filename):
                os.remove(output_filename)

            nodata_value = 32767
            country_shape = gpd.read_file(extent_shapefile)
            country_mask = geometry_mask(
                country_shape.geometry,
                out_shape=(baseRasterFile.height, baseRasterFile.width),
                transform=baseRasterFile.transform,
                invert=False
            )

            if geoRainfall.empty:
                height, width = baseRasterFile.height, baseRasterFile.width
                data_array = np.zeros((height, width), dtype=np.float64)
                data_array[country_mask] = nodata_value
                meta.update(count=1, dtype='float64', nodata=nodata_value)
                with rasterio.open(output_filename, 'w', **meta) as std_idw:
                    std_idw.write(data_array, 1)
                    print(f'{output_filename} File Written (Blank Matrix Case)')
            else:
                column_name = 'rainfall'
                power = 4
                search_radius = 4
                obser_df = geoRainfall[['name']].copy()
                
                obser_df['lon_index'] = [baseRasterFile.index(x, y)[1] for x, y in zip(geoRainfall.geometry.x, geoRainfall.geometry.y)]
                obser_df['lat_index'] = [baseRasterFile.index(x, y)[0] for x, y in zip(geoRainfall.geometry.x, geoRainfall.geometry.y)]
                obser_df['data_value'] = geoRainfall[column_name]

                valid_data_mask = ~obser_df['data_value'].isna()
                obser_df = obser_df[valid_data_mask].copy()

                idw_array = np.zeros((baseRasterFile.height, baseRasterFile.width), dtype=np.float64)

                rainfall_stations = RainfallStation.objects.all().values('station_code', 'name', 'latitude', 'longitude')
                rainfall_stations_df = pd.DataFrame(list(rainfall_stations))
                all_stations = rainfall_stations_df.merge(allDF, how='inner', left_on='station_code', right_on='st_id')
                all_geo = gpd.GeoDataFrame(
                    all_stations,
                    geometry=gpd.points_from_xy(all_stations.longitude, all_stations.latitude)
                )
                all_geo = all_geo.set_crs(4326, allow_override=True)

                missing_stations_st_id = allDF[allDF['rainfall'].isna()]['st_id']
                missing_mask = np.zeros((baseRasterFile.height, baseRasterFile.width), dtype=bool)
                for st_id_val in missing_stations_st_id:
                    station = all_geo[all_geo['st_id'] == st_id_val]
                    if not station.empty:
                        lon_idx, lat_idx = baseRasterFile.index(station.geometry.x.iloc[0], station.geometry.y.iloc[0])
                        if 0 <= lat_idx < baseRasterFile.height and 0 <= lon_idx < baseRasterFile.width:
                            missing_mask[lat_idx, lon_idx] = True

                station_mask = np.zeros((baseRasterFile.height, baseRasterFile.width), dtype=bool)
                station_values = np.zeros((baseRasterFile.height, baseRasterFile.width), dtype=np.float64)
                for idx, row in obser_df.iterrows():
                    y, x = int(row['lat_index']), int(row['lon_index'])
                    if 0 <= x < baseRasterFile.width and 0 <= y < baseRasterFile.height:
                        station_mask[y, x] = True
                        station_values[y, x] = row['data_value']

                for x_col in range(baseRasterFile.width):
                    for y_row in range(baseRasterFile.height):
                        if country_mask[y_row, x_col]:
                            continue
                        if missing_mask[y_row, x_col]:
                            idw_array[y_row][x_col] = 0
                            continue
                        if station_mask[y_row, x_col]:
                            idw_array[y_row][x_col] = station_values[y_row, x_col]
                            continue
                        value = idw.standard_idw(
                            lon=x_col,
                            lat=y_row,
                            longs=obser_df['lon_index'],
                            lats=obser_df['lat_index'],
                            d_values=obser_df['data_value'],
                            id_power=power,
                            s_radious=search_radius
                        )
                        idw_array[y_row][x_col] = max(0, value)

                valid_mask = (idw_array > 0) & (~missing_mask) & (~station_mask)
                smoothed_array = idw_array.copy()
                if valid_mask.sum() > 0:
                    smoothed_data = gaussian_filter(idw_array[valid_mask], sigma=3)
                    smoothed_data = np.maximum(smoothed_data, 0)
                    smoothed_array[valid_mask] = smoothed_data
                smoothed_array[~valid_mask] = idw_array[~valid_mask]

                low_rainfall_mask = (smoothed_array > 0) & (smoothed_array <= 0.1)
                smoothed_array[low_rainfall_mask] = 0
                smoothed_array[missing_mask] = 0
                smoothed_array[country_mask] = nodata_value

                meta.update(count=1, dtype='float64', nodata=nodata_value)
                with rasterio.open(output_filename, 'w', **meta) as std_idw:
                    std_idw.write(smoothed_array, 1)
                    print(f'{output_filename} File Written Successfully.')