import netCDF4 as nco
import os
from datetime import datetime

NC_PATH = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwrf_hres/20260327/tp.nc"

def inspect():
    if not os.path.exists(NC_PATH):
        print(f"File not found at {NC_PATH}")
        return

    ncf = nco.Dataset(NC_PATH, 'r')
    print(f"--- Variables in File ---")
    print(ncf.variables.keys())

    times = ncf.variables['time']
    dates = nco.num2date(times[:], times.units, times.calendar)
    
    print(f"\n--- Time Details ---")
    print(f"Units: {times.units}")
    print(f"First 3 Timestamps in file:")
    for i in range(min(3, len(dates))):
        print(f"  Index {i}: {dates[i]}")

    tp = ncf.variables['tp']
    print(f"\n--- Precipitation (tp) Details ---")
    print(f"Shape: {tp.shape}") # Looking for (time, lat, lon)
    print(f"First index values (mean): {tp[0,:,:].mean()}")
    
    ncf.close()

if __name__ == "__main__":
    inspect()