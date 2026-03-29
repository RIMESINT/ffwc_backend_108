import xarray as xr
import numpy as np
import os
from datetime import datetime

# Adjust the date to a file you have in your directory
FDATE = "20260328"
NC_PATH = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/bmd_wrf/wrf_out_{FDATE}00.nc"

def inspect_wrf():
    if not os.path.exists(NC_PATH):
        print(f"❌ File not found: {NC_PATH}")
        return

    print(f"🔍 Inspecting BMD-WRF File: {os.path.basename(NC_PATH)}")
    print("="*60)
    
    # Open dataset
    ds = xr.open_dataset(NC_PATH)
    
    # 1. Coordinate Check
    print(f"📍 Coordinates: {list(ds.coords)}")
    for coord in ds.coords:
        size = ds.coords[coord].size
        vmin = ds.coords[coord].values.min()
        vmax = ds.coords[coord].values.max()
        print(f"   - {coord:10}: size={size}, range=[{vmin}, {vmax}]")

    # 2. Time Step Analysis
    print(f"\n📅 Time Step Analysis:")
    times = ds.time.values
    print(f"   - Total Steps: {len(times)}")
    print(f"   - Start Time : {times[0]}")
    print(f"   - End Time   : {times[-1]}")
    
    if len(times) > 1:
        diff = (times[1] - times[0]).astype('timedelta64[h]').astype(int)
        print(f"   - Frequency  : Every {diff} hours")
        # BMD-WRF logic usually looks for index 8 (24h mark)
        if len(times) >= 9:
            print(f"   - Checkpoint : Index 8 (24h mark) is {times[8]}")

    # 3. Variable Analysis (Rainfall)
    print(f"\n🌧️  Rainfall Variables:")
    # rainc = convective, rainnc = non-convective
    rain_vars = [v for v in ['rainc', 'rainnc'] if v in ds.data_vars]
    
    if rain_vars:
        for v in rain_vars:
            attrs = ds[v].attrs
            print(f"   - Variable '{v}':")
            print(f"     * Units: {attrs.get('units', 'N/A')}")
            print(f"     * Shape: {ds[v].shape}")
        
        # Behavior Check (Cumulative?)
        total_rain = ds['rainc'] + ds['rainnc']
        mean_start = total_rain.isel(time=0).mean().item()
        mean_end = total_rain.isel(time=-1).mean().item()
        
        print(f"\n📈 Accumulation Check (Mean across grid):")
        print(f"   - Start: {mean_start:.4f} mm")
        print(f"   - End  : {mean_end:.4f} mm")
        
        if mean_end >= mean_start:
            print("   - Result : ✅ Data appears CUMULATIVE (Subtraction required)")
        else:
            print("   - Result : ⚠️ Warning: Values decreasing. Check logic.")
    else:
        print("   ❌ Rainfall variables (rainc/rainnc) not found!")

    ds.close()
    print("="*60)

if __name__ == "__main__":
    inspect_wrf()