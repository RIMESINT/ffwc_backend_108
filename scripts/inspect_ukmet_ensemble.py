import xarray as xr
import os
import numpy as np
import pandas as pd

# Path based on your last run
ENS_DIR = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_ens_data/ukmet_ens_20260327/"

def inspect_ensemble(directory):
    if not os.path.exists(directory):
        print(f"❌ Directory not found: {directory}")
        return

    print(f"🔍 Inspecting Ensemble Run: {os.path.basename(directory.strip('/'))}")
    print("=" * 70)

    all_max_values = []
    unit_detected = "Unknown"

    for i in range(18):
        filename = f"precip_EN{i:02d}.nc"
        filepath = os.path.join(directory, filename)

        if not os.path.exists(filepath):
            print(f"⚠️ Member {i:02d}: File missing.")
            continue

        try:
            ds = xr.open_dataset(filepath)
            
            # 1. Identify Variable
            var_name = next((v for v in ['tp', 'thickness_of_rainfall_amount', 'precipitation'] if v in ds.data_vars), None)
            
            if not var_name:
                print(f"❌ Member {i:02d}: No precipitation variable found.")
                continue

            data = ds[var_name]
            unit_detected = data.attrs.get('units', 'No Units Found')
            
            # 2. Get Raw Stats
            raw_max = float(data.max())
            
            # 3. Check for Scale Factor (Common in UKMET)
            # Sometimes 'tp' is in meters, so a value of 0.05 is actually 50mm
            converted_max = raw_max if unit_detected == 'mm' else raw_max * 1000
            all_max_values.append(converted_max)

            if i % 6 == 0: # Print every 6th member to keep output clean
                 print(f"✅ Member {i:02d} | Var: {var_name:10} | Units: {unit_detected:8} | Raw Max: {raw_max:.6f} | Converted: {converted_max:.2f}mm")

            ds.close()
        except Exception as e:
            print(f"💥 Member {i:02d}: Error reading file - {e}")

    # --- Summary Statistics ---
    if all_max_values:
        print("-" * 70)
        print(f"📊 ENSEMBLE SUMMARY (18 Members):")
        print(f"   * Highest Rainfall Found: {max(all_max_values):.2f} mm")
        print(f"   * Lowest Rainfall Found:  {min(all_max_values):.2f} mm")
        print(f"   * Ensemble Mean Max:      {np.mean(all_max_values):.2f} mm")
        print("-" * 70)
        
        # Check against your lowest threshold (usually 51.45mm)
        threshold = 51.45
        if max(all_max_values) < threshold:
            print(f"💡 VERDICT: The result of 0.0% is CORRECT.")
            print(f"   Reason: Even the wettest member ({max(all_max_values):.2f}mm) is below your 24h threshold ({threshold}mm).")
        else:
            print(f"🚨 VERDICT: Logic Error Suspected.")
            print(f"   Reason: Some members exceed {threshold}mm, but probability is 0.0%.")

if __name__ == "__main__":
    inspect_ensemble(ENS_DIR)