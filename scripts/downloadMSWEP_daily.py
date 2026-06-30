import os
import glob
import sys
import argparse
from datetime import datetime, timedelta
import re
from Google import Create_Service
from googleapiclient.http import MediaIoBaseDownload
import io

# --- Argument Parsing for Django Date Selector ---
parser = argparse.ArgumentParser(description="MSWEP Dynamic Ingestion Pipeline")
parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format manually passed from UI")
args = parser.parse_args()

# --- Configuration Section ---
current_script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_script_dir)
credentials_dir = os.path.join(parent_dir, 'credentials')

CLIENT_SECRET_FILE = 'hasanCredentials.json'
CLIENT_SECRET_FILE_PATH = os.path.join(credentials_dir, CLIENT_SECRET_FILE)

API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']

MYBASE_DIR = '/home/rimes/ffwc-rebase/backend/ffwc_django_project'
OBSERVED_DIR = os.path.join(MYBASE_DIR, 'observed')

os.makedirs(OBSERVED_DIR, exist_ok=True)

# Create Google Drive Service Instance
service = Create_Service(CLIENT_SECRET_FILE_PATH, API_NAME, API_VERSION, SCOPES, credentials_dir_path=credentials_dir)
folder_id = '1aehP6YDNOO73ab3tvTZet2Sh5uPdG9I_'

def get_filename_for_date(target_date):
    day_of_year = target_date.timetuple().tm_yday
    return f"{target_date.year}{day_of_year:03}.nc"

# --- Determine Target Execution Window ---
if args.date:
    try:
        start_date = datetime.strptime(args.date, "%Y-%m-%d")
        print(f"Manual override initiated from UI. Target Date: {args.date}")
    except ValueError:
        print(f"CRITICAL: Invalid date format received ({args.date}). Defaulting to automated check.")
        sys.exit(1)
else:
    # Scan local directory to resume seamlessly
    filename_pattern = re.compile(r'^\d{7}\.nc$')
    list_of_files = [f for f in os.listdir(OBSERVED_DIR) if os.path.isfile(os.path.join(OBSERVED_DIR, f))]
    latest_date = None
    
    for filename in list_of_files:
        if filename_pattern.match(filename):
            try:
                year = int(filename[:4])
                day_of_year = int(filename[4:7])
                file_date = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
            except ValueError:
                continue
                
    if latest_date is None:
        latest_date = datetime(datetime.now().year, 1, 1) - timedelta(days=1)
    
    start_date = latest_date + timedelta(days=1)

end_date = datetime.now()
current_date = start_date

# --- Core Download & Automatic Lookback Fallback Loop ---
while current_date <= end_date:
    file_name_to_download = get_filename_for_date(current_date)
    print(f"Targeting download run for: {current_date.strftime('%Y-%m-%d')} -> Filename: {file_name_to_download}")

    query = f"'{folder_id}' in parents and name='{file_name_to_download}'"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get('files', [])

    if files:
        # File is on Drive! Check if we already have it locally
        file_path = os.path.join(OBSERVED_DIR, file_name_to_download)
        if os.path.exists(file_path):
            print(f"File {file_name_to_download} already exists locally. Skipping download.")
        else:
            file_id = files[0].get('id')
            print(f'Downloading {file_name_to_download} with ID: {file_id}')
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fd=fh, request=request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)
            with open(file_path, 'wb') as f:
                f.write(fh.read())
            print(f'Downloaded {file_name_to_download} successfully.')
        current_date += timedelta(days=1)
    else:
        # AUTOMATIC FALLBACK TRACE ACTIVE
        if args.date:
            print(f"Target date file {file_name_to_download} not found on Drive. Activating backward fallback sweep...")
            fallback_date = current_date - timedelta(days=1)
            found_fallback = False
            
            # Look back up to 30 days maximum to find the most recent available dataset
            for _ in range(30):
                fallback_filename = get_filename_for_date(fallback_date)
                fallback_path = os.path.join(OBSERVED_DIR, fallback_filename)
                
                # Check if we already have this fallback file locally
                if os.path.exists(fallback_path):
                    print(f"Fallback file {fallback_filename} already downloaded locally. Ending fallback hunt.")
                    break
                    
                print(f"Checking backward availability for fallback date: {fallback_date.strftime('%Y-%m-%d')} ({fallback_filename})")
                fb_query = f"'{folder_id}' in parents and name='{fallback_filename}'"
                fb_response = service.files().list(q=fb_query, fields="files(id, name)").execute()
                fb_files = fb_response.get('files', [])
                
                if fb_files:
                    print(f"Success! Found missing chronological gap file: {fallback_filename}")
                    fb_id = fb_files[0].get('id')
                    fb_request = service.files().get_media(fileId=fb_id)
                    fb_fh = io.BytesIO()
                    fb_downloader = MediaIoBaseDownload(fd=fb_fh, request=fb_request)
                    fb_done = False
                    while not fb_done:
                        fb_status, fb_done = fb_downloader.next_chunk()
                    fb_fh.seek(0)
                    with open(fallback_path, 'wb') as f:
                        f.write(fb_fh.read())
                    print(f"Downloaded fallback file {fallback_filename} successfully.")
                    found_fallback = True
                    break # Break out since we captured the nearest missing record
                
                fallback_date -= timedelta(days=1)
                
            if not found_fallback:
                print("Fallback scan complete. No missing chronological historical gaps discovered on Drive.")
            break
        else:
            print(f"File {file_name_to_download} not found on Drive. Ending execution block loop.")
            break