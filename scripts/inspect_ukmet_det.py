import xarray as xr
import os
import pandas as pd

# Path based on your script's logic
NC_FILE = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_20260327.nc"

def inspect():
    if not os.path.exists(NC_FILE):
        print(f"❌ File not found: {NC_FILE}")
        return

    ds = xr.open_dataset(NC_FILE)
    print(f"📂 Inspecting UKMET Deterministic File")
    print("-" * 60)

    # 1. Variable Check
    var_name = next((v for v in ['tp', 'thickness_of_rainfall_amount', 'precipitation'] if v in ds.data_vars), None)
    if var_name:
        var = ds[var_name]
        print(f"✅ Found variable: {var_name}")
        print(f"   Units: {var.attrs.get('units', 'Unknown')}")
        print(f"   Max Value: {float(var.max()):.4f}")
    else:
        print(f"❌ No known precipitation variable found.")

    # 2. Time Step Check (CRITICAL)
    times = ds.indexes['time']
    interval = (times[1] - times[0]).total_seconds() / 3600
    print(f"🕒 Time Interval: {interval} hours")
    print(f"   Steps per day: {24/interval}")
    
    # 3. Coordinate Check
    lat = ds.latitude.values
    print(f"📍 Latitude: {lat[0]} to {lat[-1]} ({'Decreasing' if lat[0] > lat[-1] else 'Increasing'})")
    
    ds.close()

if __name__ == "__main__":
    inspect()