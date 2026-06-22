import xarray as xr
import os
import pandas as pd
import numpy as np

# Path based on your script's logic (Update date as needed)
NC_FILE = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/bmd_wrf/wrf_out_2026032700.nc"

def inspect():
    if not os.path.exists(NC_FILE):
        print(f"❌ File not found: {NC_FILE}")
        return

    ds = xr.open_dataset(NC_FILE)
    print(f"🔍 Inspecting BMD-WRF File: {os.path.basename(NC_FILE)}")
    print("-" * 60)

    # 1. Coordinate Check
    print("📍 Dimensions/Coordinates:")
    for dim in ds.dims:
        print(f"   - {dim}: {ds.dims[dim]}")

    # 2. Precipitation Variable Check
    # BMD WRF usually uses rainc (convective) and rainnc (non-convective)
    rain_vars = [v for v in ['rainc', 'rainnc', 'tp', 'precip'] if v in ds.data_vars]
    print(f"\n🧪 Found Rain Variables: {rain_vars}")
    
    for v in rain_vars:
        data = ds[v]
        print(f"   - {v}: Units={data.attrs.get('units', 'N/A')}, Shape={data.shape}")
        # Check if cumulative (values should increase over time)
        first = float(data.isel(time=0).mean())
        last = float(data.isel(time=-1).mean())
        print(f"     Behavior: Start Mean={first:.2f}, End Mean={last:.2f} ({'📈 Cumulative' if last > first else '🕒 Incremental'})")

    # 3. Time Step Check (Crucial for your range(8, len, 8) logic)
    times = ds.indexes['time']
    interval = (times[1] - times[0]).total_seconds() / 3600
    print(f"\n🕒 Time Interval: {interval} hours")
    print(f"   Total steps: {len(times)}")
    print(f"   First timestamp: {times[0]}")
    print(f"   Index of 24h mark: {int(24/interval)}")

    ds.close()

if __name__ == "__main__":
    inspect()