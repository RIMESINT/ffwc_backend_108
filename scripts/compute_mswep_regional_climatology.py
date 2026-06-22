import os
import io
import xarray as xr
import numpy as np
import pandas as pd
import sys
from tqdm import tqdm

# --- Path Setup ---
# Adding parent directory to sys.path to ensure Google.py can be imported
current_script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_script_dir)
sys.path.append(parent_dir)

# Import your custom Google service creator
from Google import Create_Service
from googleapiclient.http import MediaIoBaseDownload

# --- Region Configuration ---
# Your requested extent
REG_LAT_MIN, REG_LAT_MAX = -40.0, 75.0
REG_LON_MIN, REG_LON_MAX = -10.0, 170.0

# --- Drive & Local Path Configuration ---
FOLDER_ID = '1gWoZ2bK2u5osJ8Iw-dvguZ56Kmz2QWrL'
MYBASE_DIR = '/home/rimes/ffwc-rebase/backend/ffwc_django_project'
OUTPUT_DIR = os.path.join(MYBASE_DIR, 'static/data')
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'regional_mswep_climatology.nc')

# Credentials setup
credentials_dir = os.path.join(MYBASE_DIR, 'credentials')
CLIENT_SECRET_FILE = os.path.join(credentials_dir, 'hasanCredentials.json')

API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']

# --- Initialize Service ---
print("Initializing Google Drive Service...")
service = Create_Service(
    CLIENT_SECRET_FILE, 
    API_NAME, 
    API_VERSION, 
    SCOPES, 
    credentials_dir_path=credentials_dir
)

def get_all_files(folder_id):
    """Fetches all .nc files from the specific Google Drive folder."""
    query = f"'{folder_id}' in parents and name contains '.nc'"
    results = []
    next_page_token = None
    
    print(f"Fetching file list for folder: {folder_id}")
    while True:
        response = service.files().list(
            q=query, 
            pageSize=1000, 
            fields="nextPageToken, files(id, name)",
            pageToken=next_page_token
        ).execute()
        results.extend(response.get('files', []))
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
    # Sort files to ensure chronological/logical processing
    return sorted(results, key=lambda x: x['name'])

def main():
    files = get_all_files(FOLDER_ID)
    total_files = len(files)
    
    if total_files == 0:
        print("No files found in the specified Drive folder.")
        return

    print(f"Total files found: {total_files}")

    # Dictionaries to store the running sum and count per Day of Year (1-366)
    doy_sums = {}
    doy_counts = {}

    # 1. Loop through each file in Drive
    for f in tqdm(files, desc="Processing Regional Grids"):
        try:
            # Parse Day of Year from filename 'YYYYDOY.nc' (e.g., 1979001.nc)
            # Adjust indexing if your filenames vary
            doy = int(f['name'][4:7])
            
            # Download file to a memory buffer
            request = service.files().get_media(fileId=f['id'])
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            fh.seek(0)
            
            # 2. Open dataset and extract slice
            with xr.open_dataset(fh) as ds:
                # MSWEP is usually North-to-South (90 to -90). 
                # slice(max, min) selects the range correctly for this order.
                regional_slice = ds['precipitation'].sel(
                    lat=slice(REG_LAT_MAX, REG_LAT_MIN), 
                    lon=slice(REG_LON_MIN, REG_LON_MAX)
                ).squeeze().load()
                
                # Update running total for this specific calendar day
                if doy not in doy_sums:
                    doy_sums[doy] = regional_slice
                    doy_counts[doy] = 1
                else:
                    doy_sums[doy] += regional_slice
                    doy_counts[doy] += 1
                    
            fh.close() # Explicitly close buffer to free RAM

        except Exception as e:
            print(f"\n[Error] Failed to process {f['name']}: {e}")
            continue

    # 3. Finalize Averages
    print("\nCalculating final daily averages (Sum/Count)...")
    climatology_list = []
    # Sort days 1-366
    for d in sorted(doy_sums.keys()):
        daily_mean = doy_sums[d] / doy_counts[d]
        # Add 'dayofyear' as a new dimension/coordinate
        daily_mean = daily_mean.expand_dims(dayofyear=[d])
        climatology_list.append(daily_mean)

    # 4. Concatenate and Save
    print(f"Combining {len(climatology_list)} days into final file...")
    final_ds = xr.concat(climatology_list, dim='dayofyear')
    
    # Metadata
    final_ds.attrs['title'] = "MSWEP Daily Climatology (1979-2020)"
    final_ds.attrs['extent'] = f"Lat: {REG_LAT_MIN} to {REG_LAT_MAX}, Lon: {REG_LON_MIN} to {REG_LON_MAX}"
    
    final_ds.to_netcdf(OUTPUT_FILE)
    print(f"\nSUCCESS: Climatology file saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()