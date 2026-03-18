import xarray as xr
import os
import sys

def inspect_ensemble_file(date_str, member="EN00"):
    # Construct path based on the ensemble folder structure
    file_path = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_ens_data/ukmet_ens_{date_str}/precip_{member}.nc"
    
    print(f"--- Inspecting UKMET Ensemble Member: {member} ({date_str}) ---")
    print(f"Path: {file_path}\n")
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found. Check if the path or date is correct.")
        return

    try:
        ds = xr.open_dataset(file_path)
        
        # 1. Check Data Variables
        print("1. DATA VARIABLES:")
        for var in ds.data_vars:
            print(f"   - Name: {var}")
            print(f"     Units: {ds[var].attrs.get('units', 'N/A')}")
            print(f"     Description: {ds[var].attrs.get('long_name', 'N/A')}")
            print(f"     Shape: {ds[var].shape} (Time, Lat, Lon)")
        
        # 2. Check Coordinates & Spatial Extent
        print("\n2. SPATIAL COORDINATES:")
        for coord in ds.coords:
            if coord in ['latitude', 'longitude', 'lat', 'lon']:
                vals = ds[coord].values
                print(f"   - {coord}: {len(vals)} steps from {vals.min()} to {vals.max()}")

        # 3. Check Time Steps
        if 'time' in ds.coords:
            times = ds.indexes['time']
            print("\n3. TIME COVERAGE:")
            print(f"   - Start: {times[0]}")
            print(f"   - End:   {times[-1]}")
            print(f"   - Total Steps: {len(times)}")
            
            # Check if it's daily or sub-daily
            if len(times) > 1:
                diff = (times[1] - times[0]).total_seconds() / 3600
                print(f"   - Interval: {diff} hours")

        # 4. Check for Coordinate Sorting (North-South check)
        lat_name = 'latitude' if 'latitude' in ds.coords else 'lat'
        if lat_name in ds.coords:
            lats = ds[lat_name].values
            if lats[0] > lats[-1]:
                print(f"\n[!] ALERT: {lat_name} is DESCENDING. You must use .sortby(['{lat_name}']).")

        ds.close()

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Usage: python3 inspect_ukmet_ens.py 20260317 EN00
    d = sys.argv[1] if len(sys.argv) > 1 else "20260317"
    m = sys.argv[2] if len(sys.argv) > 2 else "EN00"
    inspect_ensemble_file(d, m)