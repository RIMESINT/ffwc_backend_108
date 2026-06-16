from django.core.management import BaseCommand
from django.conf import settings
from datetime import datetime
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
    help = 'Generate Rainfall Distribution Map using latest data from database'

    # def add_arguments(self, parser):
    #     parser.add_argument('date', type=str, help='Date for generating Rainfall Distribution Map (YYYY-MM-DD)', default=None)

    def handle(self, *args, **kwargs):
        dateInput = kwargs.get('date')
        if dateInput:
            print('Date Input From Parameter:', dateInput)
        else:
            latest_observation = RainfallObservation.objects.filter(
                rainfall__gte=0
            ).order_by('-observation_date').first()
            
            if latest_observation:
                dateInput = latest_observation.observation_date.strftime('%Y-%m-%d')
                print('Latest Date from Database:', latest_observation.observation_date)
            else:
                dateInput = datetime.today().strftime('%Y-%m-%d')
                print('No valid data found, using today:', dateInput)

        self.main(dateInput)

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
                print(f"No rainfall data for {dateInput or latest_rf_date}.")
                return pd.DataFrame(), pd.DataFrame()
            
            # Rename columns to match the previous structure for consistency in later steps
            rainfall_data.rename(columns={
                'station_id__station_code': 'st_id',
                'observation_date': 'rf_date'
            }, inplace=True)

            all_data = rainfall_data.copy()
            all_data['rainfall'] = all_data['rainfall'].replace(-9999.0, np.nan)
            
            valid_data = rainfall_data[rainfall_data['rainfall'] >= 0].copy()
            if valid_data.empty:
                print(f"No valid rainfall data (rainfall >= 0) for {dateInput or latest_rf_date}.")
                return pd.DataFrame(), all_data
            
            # Load station metadata from RainfallStation to map st_id to station names
            stations = RainfallStation.objects.all().values('station_code', 'name')
            stations_df = pd.DataFrame(list(stations))
            
            # Map st_id (which is now station_code) to station name
            all_data_with_names = all_data.merge(stations_df, how='left', left_on='st_id', right_on='station_code')
            
            # Log rainfall values for specific stations
            target_st_codes = [19, 15, 14, 18]  # Corresponds to station_code
            for st_code in target_st_codes:
                station_data = all_data_with_names[all_data_with_names['st_id'] == st_code]
                if not station_data.empty:
                    station_name = station_data['name'].iloc[0] if pd.notna(station_data['name'].iloc[0]) else "Unknown"
                    print(f"Rainfall value for {station_name} (st_id {st_code}): {station_data['rainfall'].iloc[0]} mm")
                else:
                    print(f"Station with st_id {st_code} not found in data.")
            
            print("Valid DataFrame Columns:", valid_data.columns)
            print("Valid DataFrame Head:\n", valid_data.head())
            print("All DataFrame Head:\n", all_data.head())
            
            return valid_data[['st_id', 'rf_date', 'rainfall']], all_data[['st_id', 'rf_date', 'rainfall']]
        
        except Exception as e:
            print(f"Error querying database: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def generateGeoRainfall(self, dateInput):
        validDF, allDF = self.fromSql(dateInput)
        print('Valid Rainfall Data Frame:', validDF)
        print('All Rainfall Data Frame:', allDF)

        if validDF.empty:
            print("No valid rainfall data for the specified date.")
            return gpd.GeoDataFrame(), pd.DataFrame()

        validDF = validDF[['st_id', 'rainfall']].copy(deep=True)
        validDF.sort_values(by=["st_id"], inplace=True)
        validDF.reset_index(drop=True, inplace=True)

        # Load station metadata from RainfallStation
        try:
            rainfall_stations = RainfallStation.objects.all().values('station_code', 'name', 'latitude', 'longitude')
            rainfall_stations_df = pd.DataFrame(list(rainfall_stations))
        except Exception as e:
            print(f"Error querying RainfallStation: {e}")
            return gpd.GeoDataFrame(), pd.DataFrame()

        # Merge with rainfall data using st_id (from RainfallObservations, which is station_code) and station_code (from RainfallStation)
        rainfall_stations_df = rainfall_stations_df.merge(validDF, how='inner', left_on='station_code', right_on='st_id')
        if rainfall_stations_df.empty:
            print("No matching stations found after merging.")
            return gpd.GeoDataFrame(), pd.DataFrame()

        # Create GeoDataFrame with geometry
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
            print("Raster Data Type:", baseRasterFile.dtypes[0])
            meta = baseRasterFile.meta.copy()
            output_filename = os.path.join(settings.BASE_DIR, 'assets', 'tiffOutput', f'rainfall_distribution_idw_{dateInput}.tif')

            if os.path.exists(output_filename):
                os.remove(output_filename)
                print(f"Removed existing file: {output_filename}")

            # Define nodata value
            nodata_value = 32767

            # Create country mask (True for areas outside the country, False inside)
            country_shape = gpd.read_file(extent_shapefile)
            country_mask = geometry_mask(
                country_shape.geometry,
                out_shape=(baseRasterFile.height, baseRasterFile.width),
                transform=baseRasterFile.transform,
                invert=False
            )

            if geoRainfall.empty:
                # When no rainfall data is available, set the entire area inside the country to 0 (white)
                # and outside the country to nodata_value (transparent)
                height, width = baseRasterFile.height, baseRasterFile.width
                data_array = np.zeros((height, width), dtype=np.float64)  # Inside country: 0 (white)
                data_array[country_mask] = nodata_value  # Outside country: nodata (transparent)
                meta.update(
                    count=1,
                    dtype='float64',
                    nodata=nodata_value
                )
                with rasterio.open(output_filename, 'w', **meta) as std_idw:
                    std_idw.write(data_array, 1)
                    print(f'{output_filename} File Written (No Data Case)')
            else:
                column_name = 'rainfall'
                power = 4
                search_radius = 4
                obser_df = geoRainfall[['name']].copy()
                
                # Corrected way to get lon_index and lat_index for each point
                obser_df['lon_index'] = [baseRasterFile.index(x, y)[1] for x, y in zip(geoRainfall.geometry.x, geoRainfall.geometry.y)]
                obser_df['lat_index'] = [baseRasterFile.index(x, y)[0] for x, y in zip(geoRainfall.geometry.x, geoRainfall.geometry.y)]

                obser_df['data_value'] = geoRainfall[column_name]

                valid_data_mask = ~obser_df['data_value'].isna()
                obser_df = obser_df[valid_data_mask].copy()
                if obser_df.empty:
                    print("No valid rainfall data after filtering.")
                    height, width = baseRasterFile.height, baseRasterFile.width
                    data_array = np.zeros((height, width), dtype=np.float64)  # Inside country: 0 (white)
                    data_array[country_mask] = nodata_value  # Outside country: nodata (transparent)
                    meta.update(
                        count=1,
                        dtype='float64',
                        nodata=nodata_value
                    )
                    with rasterio.open(output_filename, 'w', **meta) as std_idw:
                        std_idw.write(data_array, 1)
                        print(f'{output_filename} File Written (No Valid Data)')
                    return

                print(f"Valid rainfall values min: {obser_df['data_value'].min()}, max: {obser_df['data_value'].max()}")
                idw_array = np.zeros((baseRasterFile.height, baseRasterFile.width), dtype=np.float64)  # Default to 0 (white)

                # Create a mask for stations with missing data (-9999.0 or NaN)
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
                            print(f"Marked station {st_id_val} at ({lat_idx}, {lon_idx}) as missing.")

                # Create a mask for actual station locations to preserve their values
                station_mask = np.zeros((baseRasterFile.height, baseRasterFile.width), dtype=bool)
                station_values = np.zeros((baseRasterFile.height, baseRasterFile.width), dtype=np.float64)
                for idx, row in obser_df.iterrows():
                    # The order for baseRasterFile.index is (longitude, latitude) but it returns (row, col)
                    # row is y, col is x. So, lat_index is row and lon_index is col.
                    y, x = int(row['lat_index']), int(row['lon_index'])
                    if 0 <= x < baseRasterFile.width and 0 <= y < baseRasterFile.height:
                        station_mask[y, x] = True
                        station_values[y, x] = row['data_value']
                        print(f"Station {row['name']} at ({y}, {x}) with value {row['data_value']} mm")

                # Perform IDW interpolation
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


                # Apply Gaussian smoothing to interpolated areas
                valid_mask = (idw_array > 0) & (~missing_mask) & (~station_mask)
                smoothed_array = idw_array.copy()
                if valid_mask.sum() > 0:
                    smoothed_data = gaussian_filter(idw_array[valid_mask], sigma=3)
                    smoothed_data = np.maximum(smoothed_data, 0)
                    smoothed_array[valid_mask] = smoothed_data
                smoothed_array[~valid_mask] = idw_array[~valid_mask]

                # Set areas with rainfall between 0 and 0.1 mm to 0 (white)
                low_rainfall_mask = (smoothed_array > 0) & (smoothed_array <= 0.1)
                smoothed_array[low_rainfall_mask] = 0
                print(f"Set {low_rainfall_mask.sum()} pixels to 0 (white) for rainfall between 0 and 0.1 mm.")

                # Ensure missing stations are set to 0 (white)
                smoothed_array[missing_mask] = 0
                print(f"Set {missing_mask.sum()} pixels to 0 (white) for missing stations.")

                # Ensure areas outside the country boundary are set to nodata (transparent)
                smoothed_array[country_mask] = nodata_value
                print(f"Set {country_mask.sum()} pixels to nodata ({nodata_value}) for areas outside country boundary.")

                meta.update(
                    count=1,
                    dtype='float64',
                    nodata=nodata_value
                )
                with rasterio.open(output_filename, 'w', **meta) as std_idw:
                    std_idw.write(smoothed_array, 1)
                    print(f'{output_filename} File Written (With Data Case)')


    def main(self, dateInput):
        # Changed extent_shapefile path to include 'shapes' subdirectory
        extent_shapefile = os.path.join(settings.BASE_DIR, 'assets', 'shapes', 'Bangladesh_Border.shp')
        geoRainfall, allDF = self.generateGeoRainfall(dateInput)
        print('Geo Rainfall: ')
        print(geoRainfall)

        if len(geoRainfall) > 0:
            print('Generating Rainfall Distribution Map...')
        else:
            print('No Data Available, generating white shape TIFF...')
        
        self.generateTiff(extent_shapefile, geoRainfall, allDF, dateInput)