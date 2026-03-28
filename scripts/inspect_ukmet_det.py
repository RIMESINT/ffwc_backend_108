import netCDF4 as nco
import os
import numpy as np
from datetime import datetime

# Adjust this path to the specific file you want to check
NC_PATH = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/precip_20260328.nc"

def inspect():
    if not os.path.exists(NC_PATH):
        print(f"❌ File not found at: {NC_PATH}")
        return

    # Open the dataset in read-only mode
    ncf = nco.Dataset(NC_PATH, 'r')
    
    print(f"✅ Successfully opened: {os.path.basename(NC_PATH)}")
    print("="*60)

    # 1. Variables and Dimensions
    print(f"📊 Variables found: {list(ncf.variables.keys())}")
    print(f"📐 Dimensions:")
    for dim in ncf.dimensions:
        print(f"   - {dim}: {len(ncf.dimensions[dim])}")

    # 2. Time Analysis
    if 'time' in ncf.variables:
        t_var = ncf.variables['time']
        print(f"\n🕒 Time Units: {t_var.units}")
        
        # Convert all timestamps
        dates = nco.num2date(t_var[:], t_var.units, t_var.calendar)
        print(f"📅 First 5 Timestamps in File:")
        for i in range(min(5, len(dates))):
            print(f"   Index {i}: {dates[i]}")
    else:
        print("\n⚠️ 'time' variable not found!")

    # 3. Precipitation (tp) Variable Analysis
    if 'tp' in ncf.variables:
        tp = ncf.variables['tp']
        print(f"\n🌧️  Precipitation (tp) Details:")
        print(f"   - Shape: {tp.shape}")
        
        # Safe Attribute Access (Avoids the AttributeError from earlier)
        available_attrs = tp.ncattrs()
        print(f"   - Available Attributes: {available_attrs}")
        
        if 'units' in available_attrs:
            print(f"   - Units: {tp.units}")
        else:
            print("   - Units: NOT SPECIFIED")

        # Data Check: Looking for cumulative vs incremental behavior
        print(f"\n📈 Value Check (Mean across grid):")
        for i in range(min(5, len(dates))):
            mean_val = np.mean(tp[i, :, :])
            print(f"   Index {i} ({dates[i].strftime('%Y-%m-%d')}): {mean_val:.6f}")
            
    else:
        print("\n⚠️ 'tp' variable not found!")

    # 4. Global Metadata
    print(f"\n🌍 Global Attributes:")
    for attr in ncf.ncattrs():
        print(f"   - {attr}: {getattr(ncf, attr)}")

    ncf.close()
    print("="*60)

if __name__ == "__main__":
    inspect()