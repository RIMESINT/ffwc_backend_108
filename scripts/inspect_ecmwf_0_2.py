import xarray as xr
import geopandas as gpd
import os

# Paths
nc_file = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/16032026.nc"
json_file = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/assets/floodForecastStations/muslimpur.json"

print("--- NetCDF File Inspection ---")
if os.path.exists(nc_file):
    ds = xr.open_dataset(nc_file)
    print(f"Variables: {list(ds.data_vars)}")
    print(f"Coordinates: {list(ds.coords)}")
    
    # Check Latitude Bounds
    if 'latitude' in ds.coords:
        lat = ds.latitude.values
        print(f"Latitude range: {lat.min()} to {lat.max()}")
    
    # Check Longitude Bounds (Crucial for 0-360 vs -180-180 issues)
    if 'longitude' in ds.coords:
        lon = ds.longitude.values
        print(f"Longitude range: {lon.min()} to {lon.max()}")
else:
    print("NetCDF file not found!")

print("\n--- Basin Geometry Inspection (Muslimpur) ---")
if os.path.exists(json_file):
    gdf = gpd.read_file(json_file)
    print(f"Basin Bounds: {gdf.total_bounds}") # [minx, miny, maxx, maxy]
    print(f"Basin CRS: {gdf.crs}")
else:
    print("Basin JSON file not found!")