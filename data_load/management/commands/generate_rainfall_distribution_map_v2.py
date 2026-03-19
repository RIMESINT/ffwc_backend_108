import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from datetime import datetime
from django.core.management import BaseCommand
from django.conf import settings
from django.utils import timezone
from pyidw import idw
from scipy.ndimage import gaussian_filter
from rasterio.features import geometry_mask
from data_load.models import RainfallObservation, RainfallStation

class Command(BaseCommand):
    help = 'Generate Rainfall Distribution Map for current date (blank TIFF if no data)'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format', default=None)

    def handle(self, *args, **kwargs):
        # Determine the target date (default to today)
        date_param = kwargs.get('date')
        if date_param:
            date_input = date_param
        else:
            date_input = datetime.now().strftime('%Y-%m-%d')
        
        print(f"Target Process Date: {date_input}")
        self.main(date_input)

    def from_sql(self, date_input):
        try:
            # Parse date and make it timezone aware for Django DB filtering
            naive_date = datetime.strptime(date_input, '%Y-%m-%d')
            target_date = timezone.make_aware(naive_date).date()
            
            rainfall_data = RainfallObservation.objects.filter(
                observation_date=target_date
            ).values('station_id__station_code', 'observation_date', 'rainfall')
            
            df = pd.DataFrame(list(rainfall_data))
            
            if df.empty:
                print(f"No database records found for {target_date}.")
                return pd.DataFrame(), pd.DataFrame()
            
            df.rename(columns={'station_id__station_code': 'st_id', 'observation_date': 'rf_date'}, inplace=True)
            
            all_df = df.copy()
            all_df['rainfall'] = all_df['rainfall'].replace(-9999.0, np.nan)
            
            # Valid data for interpolation
            valid_df = df[df['rainfall'] >= 0].copy()
            
            return valid_df, all_df
        except Exception as e:
            print(f"Error querying database: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def generate_geo_rainfall(self, date_input):
        valid_df, all_df = self.from_sql(date_input)

        if valid_df.empty:
            return gpd.GeoDataFrame(), all_df

        stations = RainfallStation.objects.all().values('station_code', 'name', 'latitude', 'longitude')
        stations_df = pd.DataFrame(list(stations))
        
        merged_df = stations_df.merge(valid_df, left_on='station_code', right_on='st_id')
        
        if merged_df.empty:
            return gpd.GeoDataFrame(), all_df

        geo_rainfall = gpd.GeoDataFrame(
            merged_df,
            geometry=gpd.points_from_xy(merged_df.longitude, merged_df.latitude),
            crs="EPSG:4326"
        )
        return geo_rainfall, all_df

    def generate_tiff(self, extent_shapefile, geo_rainfall, all_df, date_input):
        # 1. Path Configuration
        output_dir = os.path.join(settings.BASE_DIR, 'assets', 'tiffOutput')
        os.makedirs(output_dir, exist_ok=True)
        
        # Exact requested naming convention
        output_filename = os.path.join(output_dir, f'rainfall_distribution_idw_{date_input}.tif')
        
        # pyidw creates temporary files near the shapefile
        idw.blank_raster(extent_shapefile)
        blank_file = extent_shapefile.rsplit('.', 1)[0] + '_blank.tif'
        resized_file = extent_shapefile.rsplit('.', 1)[0] + '_blank_resized.tif'
        
        idw.crop_resize(blank_file, extent_shapefile, 1000)

        # 2. Raster Generation
        with rasterio.open(resized_file) as src:
            meta = src.meta.copy()
            nodata_value = 32767
            
            # Country Boundary Mask
            country_shape = gpd.read_file(extent_shapefile)
            country_mask = geometry_mask(
                country_shape.geometry,
                out_shape=(src.height, src.width),
                transform=src.transform,
                invert=False # False = inside country
            )

            # CASE: No Data -> Create Blank White Map
            if geo_rainfall.empty:
                print(f"Data is missing. Creating white map for {date_input}")
                data_array = np.zeros((src.height, src.width), dtype=np.float64) # 0 = White/No Rain
                data_array[country_mask] = nodata_value
            
            # CASE: Data Exists -> Perform Interpolation
            else:
                print(f"Performing IDW for {len(geo_rainfall)} stations...")
                idw_array = np.zeros((src.height, src.width), dtype=np.float64)
                
                # Get pixel coords for stations
                lons = [src.index(x, y)[1] for x, y in zip(geo_rainfall.geometry.x, geo_rainfall.geometry.y)]
                lats = [src.index(x, y)[0] for x, y in zip(geo_rainfall.geometry.x, geo_rainfall.geometry.y)]
                values = geo_rainfall['rainfall'].values

                for r in range(src.height):
                    for c in range(src.width):
                        if country_mask[r, c]:
                            idw_array[r, c] = nodata_value
                        else:
                            val = idw.standard_idw(c, r, lons, lats, values, id_power=4, s_radious=4)
                            idw_array[r, c] = max(0, val)
                
                data_array = gaussian_filter(idw_array, sigma=1)
                data_array[country_mask] = nodata_value

            # Save the file
            meta.update(dtype='float64', nodata=nodata_value, count=1)
            with rasterio.open(output_filename, 'w', **meta) as dst:
                dst.write(data_array, 1)

        # 3. Cleanup and Verification
        for temp in [blank_file, resized_file]:
            if os.path.exists(temp):
                os.remove(temp)

        if os.path.exists(output_filename):
            print(f"SUCCESS: {output_filename} generated.")
        else:
            print("ERROR: File generation failed.")

    def main(self, date_input):
        extent_path = os.path.join(settings.BASE_DIR, 'assets', 'shapes', 'Bangladesh_Border.shp')
        
        if not os.path.exists(extent_path):
            print(f"Shapefile missing at: {extent_path}")
            return

        geo_rainfall, all_df = self.generate_geo_rainfall(date_input)
        self.generate_tiff(extent_path, geo_rainfall, all_df, date_input)