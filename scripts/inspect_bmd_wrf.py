import xarray as xr
import os
import sys

def inspect_wrf_file(file_path):
    print(f"--- Inspecting BMD WRF File: {os.path.basename(file_path)} ---\n")
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        return

    try:
        # Open dataset
        ds = xr.open_dataset(file_path)
        
        # 1. Show Data Variables
        # Look specifically for 'RAINC' (Cumulus) and 'RAINNC' (Non-Convective)
        print("1. DATA VARIABLES:")
        rainfall_vars = ['RAINC', 'RAINNC', 'precip', 'tp', 'precip_total']
        for var in ds.data_vars:
            if var in rainfall_vars or "RAIN" in var:
                print(f"   [!] Rainfall Candidate -> {var}")
                print(f"       Units: {ds[var].attrs.get('units', 'N/A')}")
                print(f"       Description: {ds[var].attrs.get('long_name', 'N/A')}")
            else:
                # Just list other variables briefly
                pass
        
        print(f"\n   (Total variables found: {len(ds.data_vars)})")

        # 2. Show Coordinates
        print("\n2. COORDINATES / DIMENSIONS:")
        for coord in ds.coords:
            vals = ds[coord].values
            print(f"   - {coord}: {len(vals)} values from {vals.min()} to {vals.max()}")

        # 3. Check for XLAT / XLONG (Common in WRF)
        if 'XLAT' in ds.variables or 'XLONG' in ds.variables:
            print("\n3. WRF GRID CHECK:")
            # WRF often uses 2D lat/lon arrays (Time, South_North, West_East)
            lat_var = 'XLAT' if 'XLAT' in ds.variables else 'XLAT_M'
            lon_var = 'XLONG' if 'XLONG' in ds.variables else 'XLONG_M'
            
            if lat_var in ds.variables:
                lats = ds[lat_var].values
                print(f"   - {lat_var} range: {lats.min()} to {lats.max()}")
            if lon_var in ds.variables:
                lons = ds[lon_var].values
                print(f"   - {lon_var} range: {lons.min()} to {lons.max()}")

        # 4. Check Time
        if 'time' in ds.coords or 'XTIME' in ds.variables:
            print("\n4. TIME RANGE:")
            # Some WRF files use 'XTIME', others 'time'
            time_key = 'time' if 'time' in ds.coords else 'XTIME'
            times = ds.indexes.get(time_key, ds[time_key].values)
            print(f"   - Start: {times[0]}")
            print(f"   - End:   {times[-1]}")
            print(f"   - Total Steps: {len(times)}")

        ds.close()

    except Exception as e:
        print(f"An error occurred during inspection: {str(e)}")

if __name__ == "__main__":
    path = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/bmd_wrf/wrf_out_2026031700.nc"
    inspect_wrf_file(path)