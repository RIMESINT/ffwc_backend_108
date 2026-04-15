import xarray as xr
import numpy as np
import pandas as pd
import os

# --- Path to your IMD-GFS file ---
IMD_FILE = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/imd_gfs/20260412.nc'

def inspect_imd_gfs():
    print("="*60)
    print(f"INSPECTING IMD-GFS DATA: {os.path.basename(IMD_FILE)}")
    print("="*60)

    if not os.path.exists(IMD_FILE):
        print(f"ERROR: File {IMD_FILE} not found.")
        return

    try:
        # Open dataset
        ds = xr.open_dataset(IMD_FILE)
        
        # 1. Basic Structure
        print("\n[1] DATASET STRUCTURE")
        print(ds)

        # 2. Variable Investigation
        print("\n[2] VARIABLE DETAILS")
        for var in ds.data_vars:
            attrs = ds[var].attrs
            dtype = ds[var].dtype
            print(f"\nVariable: {var}")
            print(f"  - Units: {attrs.get('units', 'N/A')}")
            print(f"  - Long Name: {attrs.get('long_name', 'N/A')}")
            print(f"  - Data Type: {dtype}")
            
            # Sample stats to check data range
            sample = ds[var].isel(time=0).values
            print(f"  - Min/Max (Step 0): {np.nanmin(sample):.6f} / {np.nanmax(sample):.6f}")

        # 3. Coordinate Check
        print("\n[3] COORDINATES & GRID")
        # Checking for standard naming or common IMD variants
        lat_name = 'lat' if 'lat' in ds.coords else 'latitude'
        lon_name = 'lon' if 'lon' in ds.coords else 'longitude'
        
        lats = ds[lat_name].values
        lons = ds[lon_name].values
        print(f"  - Latitude: {lats.min()} to {lats.max()} (Res: {abs(lats[1]-lats[0])})")
        print(f"  - Longitude: {lons.min()} to {lons.max()} (Res: {abs(lons[1]-lons[0])})")

        # 4. Time Resolution
        print("\n[4] TIME STEPS")
        time_vals = pd.to_datetime(ds.time.values)
        print(f"  - Start Time: {time_vals[0]}")
        print(f"  - End Time:   {time_vals[-1]}")
        if len(time_vals) > 1:
            diff = (time_vals[1] - time_vals[0]).total_seconds() / 3600
            print(f"  - Frequency:  {diff} hourly")

    except Exception as e:
        print(f"ERROR: Could not inspect file. {e}")

if __name__ == "__main__":
    inspect_imd_gfs()