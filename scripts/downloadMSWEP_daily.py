import os
import glob
from datetime import datetime, timedelta
import re
from Google import Create_Service
from googleapiclient.http import MediaIoBaseDownload
import io

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

# Ensure the 'observed' directory exists.
os.makedirs(OBSERVED_DIR, exist_ok=True)

# Create the service
service = Create_Service(CLIENT_SECRET_FILE_PATH, API_NAME, API_VERSION, SCOPES, credentials_dir_path=credentials_dir)

# The ID of the Google Drive folder containing the files.
folder_id = '1aehP6YDNOO73ab3tvTZet2Sh5uPdG9I_'

# ------------------------------------------------------------------------------------------------------
def get_last_downloaded_date(directory):
    """
    Scans the directory for filenames matching the 'YYYYDDD.nc' pattern
    and returns the latest date found.
    """
    # A regular expression to match 'YYYYDDD.nc' filenames
    filename_pattern = re.compile(r'^\d{7}\.nc$')
    
    # Get all filenames in the directory
    list_of_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    
    latest_date = None
    
    for filename in list_of_files:
        if filename_pattern.match(filename):
            try:
                # Extract year and day of the year from the filename
                year = int(filename[:4])
                day_of_year = int(filename[4:7])
                
                # Convert day of year to a datetime object
                file_date = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
                
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
            except (ValueError, IndexError):
                # Skip files that don't conform to the expected filename format
                continue
    
    # If no valid files were found, default to the start of the current year
    if latest_date is None:
        return datetime(datetime.now().year, 1, 1)
        
    return latest_date

# ------------------------------------------------------------------------------------------------------

# Find the last downloaded date from the local directory.
last_downloaded_date = get_last_downloaded_date(OBSERVED_DIR)
print(f"Resuming download from the day after: {last_downloaded_date.strftime('%Y-%m-%d')}")

# Set the start date to the day after the last downloaded file.
start_date = last_downloaded_date + timedelta(days=1)
end_date = datetime.now()

current_date = start_date

# Loop through each day from the start date until the current day.
while current_date <= end_date:
    day_of_year = current_date.timetuple().tm_yday
    year_str = str(current_date.year)
    day_of_year_str = f"{day_of_year:03}"

    file_name_to_download = f"{year_str}{day_of_year_str}.nc"
    print(f"Checking for file: {file_name_to_download}")

    query = f"'{folder_id}' in parents and name='{file_name_to_download}'"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get('files', [])

    if not files:
        print(f'File {file_name_to_download} not found in the specified folder. Skipping.')
    else:
        file_id = files[0].get('id')
        print(f'Downloading {file_name_to_download} with ID: {file_id}')

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fd=fh, request=request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f'Download progress: {status.progress() * 100:.2f}% for file {file_name_to_download}')

        fh.seek(0)
        
        file_path = os.path.join(OBSERVED_DIR, file_name_to_download)

        with open(file_path, 'wb') as f:
            f.write(fh.read())

        print(f'Downloaded {file_name_to_download} successfully to {file_path}.')

    current_date += timedelta(days=1)