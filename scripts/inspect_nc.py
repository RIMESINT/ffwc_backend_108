import xarray as xr
import numpy as np
import pandas as pd
import os

# The specific file you mentioned
NC_FILE = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/25032026.nc"

def inspect_netcdf(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    print(f"🔍 Inspecting: {file_path}")
    print("-" * 60)

    try:
        # We use decode_times=True to see the human-readable dates
        ds = xr.open_dataset(file_path)
        
        # 1. Basic Structure
        print("\n📂 DATASET STRUCTURE:")
        print(ds)

        # 2. Coordinate Check
        print("\n📍 COORDINATES:")
        for coord in ds.coords:
            c_data = ds[coord]
            print(f"  - {coord}: size={c_data.size}, min={c_data.min().values}, max={c_data.max().values}")

        # 3. Time Check (Crucial for your 'Day 1' logic)
        print("\n📅 TIME STEPS (First 5):")
        time_values = ds.time.values
        for t in time_values[:5]:
            print(f"  - {pd.to_datetime(t)}")

        # 4. Variable Inspection (Looking for 'tp')
        target_var = None
        for var in ['tp', 'total_precipitation', 'precip']:
            if var in ds.data_vars:
                target_var = var
                break

        if target_var:
            data = ds[target_var]
            print(f"\n🧪 VARIABLE DETAIL: '{target_var}'")
            print(f"  - Units: {data.attrs.get('units', 'Unknown')}")
            print(f"  - Shape: {data.shape}")
            
            # Check for actual data (is the file empty/all zeros?)
            v_min = float(data.min())
            v_max = float(data.max())
            v_mean = float(data.mean())
            
            print(f"  - Statistics:")
            print(f"    * Min:  {v_min}")
            print(f"    * Max:  {v_max}")
            print(f"    * Mean: {v_mean}")

            if v_max == 0 and v_min == 0:
                print("⚠️ WARNING: This variable contains ONLY ZEROS.")
            
            # Check for NaNs
            nan_count = np.isnan(data.values).sum()
            if nan_count > 0:
                print(f"⚠️ WARNING: Found {nan_count} NaN values.")

        else:
            print("\n❌ ERROR: Could not find a precipitation variable (tp/total_precipitation).")

        ds.close()

    except Exception as e:
        print(f"💥 Critical Error during inspection: {e}")

if __name__ == "__main__":
    inspect_netcdf(NC_FILE)