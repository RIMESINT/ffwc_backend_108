import xarray as xr
import os
import sys

def inspect_ukmet_file(date_str):
    # Construct the path based on your download directory
    file_path = f"/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_{date_str}.nc"
    
    print(f"--- Inspecting UKMET File: {file_path} ---\n")
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        return

    try:
        # Open dataset
        ds = xr.open_dataset(file_path)
        
        # 1. Show all Data Variables (Find the rainfall variable here)
        print("1. DATA VARIABLES:")
        for var in ds.data_vars:
            print(f"   - Name: {var}")
            print(f"     Units: {ds[var].attrs.get('units', 'N/A')}")
            print(f"     Long Name: {ds[var].attrs.get('long_name', 'N/A')}")
            print(f"     Shape: {ds[var].shape}")
        
        # 2. Show Coordinates (Check for lat/lon vs latitude/longitude)
        print("\n2. COORDINATES:")
        for coord in ds.coords:
            vals = ds[coord].values
            print(f"   - {coord}: {len(vals)} values from {vals.min()} to {vals.max()}")

        # 3. Check Time Dimension
        if 'time' in ds.coords:
            print("\n3. TIME RANGE:")
            times = ds.indexes['time']
            print(f"   - Start: {times[0]}")
            print(f"   - End:   {times[-1]}")
            print(f"   - Steps: {len(times)}")

        # 4. Check for Coordinate Sorting (Descending order check)
        # We check if latitude is North-to-South (descending)
        lat_name = 'latitude' if 'latitude' in ds.coords else 'lat'
        if lat_name in ds.coords:
            lats = ds[lat_name].values
            if lats[0] > lats[-1]:
                print(f"\n[!] WARNING: {lat_name} is in DESCENDING order (North to South).")
                print(f"    You MUST use .sortby(['{lat_name}']) before clipping.")

        ds.close()

    except Exception as e:
        print(f"An error occurred during inspection: {str(e)}")

if __name__ == "__main__":
    # Use the date from earlier as default or take from command line
    target_date = sys.argv[1] if len(sys.argv) > 1 else "20260316"
    inspect_ukmet_file(target_date)