import xarray as xr
import os
import pandas as pd

# Path to the file your script targets
NC_FILE = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/25032026.nc"

def inspect():
    if not os.path.exists(NC_FILE):
        print(f"❌ File not found: {NC_FILE}")
        return

    ds = xr.open_dataset(NC_FILE)
    print(f"📂 Inspecting ECMWF 0.2 File for Pre-Monsoon Logic")
    print("-" * 60)

    # 1. Variable Verification (Your code specifically asks for 'cp')
    if 'cp' in ds.data_vars:
        cp_var = ds['cp']
        print(f"✅ Found 'cp' variable (Convective Precipitation)")
        print(f"   Units: {cp_var.attrs.get('units', 'Unknown')}")
        
        # Check if values are in meters (common for ECMWF)
        v_max = float(cp_var.max())
        if v_max < 1.0:
            print(f"   Note: Max value is {v_max:.4f}m. Multiplier * 1000 is REQUIRED.")
    else:
        print(f"❌ ERROR: Variable 'cp' not found. Available: {list(ds.data_vars)}")

    # 2. Coordinate Sorting Check
    lat = ds.latitude.values
    if lat[0] > lat[-1]:
        print(f"⚠️  Latitude is DECREASING ({lat[0]} to {lat[-1]}).")
        print(f"   Logic Check: Your code uses '.sortby(['latitude', 'longitude'])'. This is CORRECT.")

    # 3. Time Step Check (3-hourly vs 24-hourly)
    times = ds.indexes['time']
    time_diff = (times[1] - times[0]).total_seconds() / 3600
    print(f"🕒 Time Step Interval: {time_diff} hours")
    print(f"   First Time: {times[0]}")
    print(f"   Last Time:  {times[-1]}")

    # 4. Cumulative Check
    first_val = float(ds['cp'].isel(time=0).mean())
    last_val = float(ds['cp'].isel(time=-1).mean())
    if last_val > first_val:
        print(f"📈 Behavior: CUMULATIVE. (Subtraction logic 'curr - prev' is REQUIRED).")
    
    ds.close()

if __name__ == "__main__":
    inspect()