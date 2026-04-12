import xarray as xr
import numpy as np
import pandas as pd
import sys

# --- Path to your ECMWF file ---
ECMWF_FILE = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/10042026.nc'

def inspect_ecmwf():
    print("="*60)
    print(f"INSPECTING ECMWF DATA: {os.path.basename(ECMWF_FILE)}")
    print("="*60)

    try:
        # Open dataset
        ds = xr.open_dataset(ECMWF_FILE)
        
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
            
            # Sample stats to check for zero/nulls
            sample = ds[var].isel(time=0).values
            print(f"  - Min/Max (Step 0): {np.nanmin(sample):.6f} / {np.nanmax(sample):.6f}")

        # 3. Coordinate Check
        print("\n[3] COORDINATES & GRID")
        lats = ds.latitude.values
        lons = ds.longitude.values
        print(f"  - Lat Range: {lats.min()} to {lats.max()} (Resolution: {abs(lats[1]-lats[0])})")
        print(f"  - Lon Range: {lons.min()} to {lons.max()} (Resolution: {abs(lons[1]-lons[0])})")

        # 4. Time Resolution
        print("\n[4] TIME STEPS")
        time_vals = pd.to_datetime(ds.time.values)
        print(f"  - Start Time: {time_vals[0]}")
        print(f"  - End Time:   {time_vals[-1]}")
        if len(time_vals) > 1:
            diff = (time_vals[1] - time_vals[0]).total_seconds() / 3600
            print(f"  - Frequency:  {diff} hourly")

        # 5. Accumulation Logic Check
        # If max value increases over time, it is accumulated.
        if 'cp' in ds.data_vars:
            first_max = ds['cp'].isel(time=0).max().values
            last_max = ds['cp'].isel(time=-1).max().values
            if last_max > first_max:
                print("\n[ALERT] 'cp' variable appears to be ACCUMULATED (Bucket).")
            else:
                print("\n[ALERT] 'cp' variable appears to be INSTANTANEOUS.")

    except Exception as e:
        print(f"ERROR: Could not inspect file. {e}")

if __name__ == "__main__":
    import os
    inspect_ecmwf()