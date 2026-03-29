import xarray as xr
import pandas as pd
import numpy as np
import os

# Target file path
NC_FILE = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/28032026.nc"

def perform_inspection(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # Open dataset
    ds = xr.open_dataset(file_path)
    
    print(f"🔍 Dataset Summary: {os.path.basename(file_path)}")
    print("=" * 60)
    print(ds)
    print("-" * 60)

    # 1. Coordinate Check
    print("\n📍 Coordinate Ranges:")
    for coord in ds.coords:
        print(f"  {coord:10}: min={ds[coord].min().values}, max={ds[coord].max().values}, length={ds[coord].size}")

    # 2. Time Step Analysis
    print("\n📅 First 5 Time Steps:")
    for t in ds.time.values[:5]:
        print(f"  {pd.to_datetime(t)}")

    # 3. Precipitation Variable Detection & Cumulative Test
    print("\n🧪 Variable Analysis:")
    found_vars = [v for v in ['tp', 'cp', 'lsp', 'precip'] if v in ds.data_vars]
    
    if not found_vars:
        print("  ❌ No precipitation variables found.")
    else:
        for var in found_vars:
            data = ds[var]
            v_min = float(data.min())
            v_max = float(data.max())
            
            # Check for cumulative behavior
            # If the mean value of the last time step is significantly higher than the first, it's cumulative
            first_mean = float(data.isel(time=0).mean())
            last_mean = float(data.isel(time=-1).mean())
            is_cumulative = last_mean > first_mean and last_mean > 0
            
            print(f"  Variable: '{var}'")
            print(f"    - Units:      {data.attrs.get('units', 'Unknown')}")
            print(f"    - Max Value:  {v_max}")
            print(f"    - Mean Start: {first_mean}")
            print(f"    - Mean End:   {last_mean}")
            print(f"    - Behavior:   {'✅ CUMULATIVE' if is_cumulative else '🕒 INCREMENTAL'}")

    ds.close()

if __name__ == "__main__":
    perform_inspection(NC_FILE)