import os
import sys

# --- Configuration Section ---
# We add the parent directory to sys.path so we can import 'Google'
current_script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_script_dir)
sys.path.append(parent_dir)

from scripts.Google import Create_Service # Adjust if Google.py is elsewhere
import io

# Paths to your credentials
credentials_dir = os.path.join(parent_dir, 'credentials')
CLIENT_SECRET_FILE = 'hasanCredentials.json'
CLIENT_SECRET_FILE_PATH = os.path.join(credentials_dir, CLIENT_SECRET_FILE)

API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']

# 1. Initialize the Service
service = Create_Service(
    CLIENT_SECRET_FILE_PATH, 
    API_NAME, 
    API_VERSION, 
    SCOPES, 
    credentials_dir_path=credentials_dir
)

# 2. The ID of the folder you want to inspect
folder_id = '1gWoZ2bK2u5osJ8Iw-dvguZ56Kmz2QWrL'

# 3. List the first 5 files
try:
    print(f"Connecting to Drive to inspect folder: {folder_id}...")
    query = f"'{folder_id}' in parents"
    results = service.files().list(
        q=query, 
        pageSize=5, 
        fields="nextPageToken, files(id, name, size, mimeType, createdTime)"
    ).execute()

    items = results.get('files', [])

    if not items:
        print('No files found. Check if the folder ID is correct and shared with your service account.')
    else:
        print('\n--- Files found in folder ---')
        for item in items:
            size_mb = int(item.get('size', 0)) / 1024**2
            print(f"Name: {item['name']}")
            print(f"  ID: {item['id']}")
            print(f"  Size: {size_mb:.2f} MB")
            print(f"  Created: {item['createdTime']}")
            print("-" * 30)

except Exception as e:
    print(f"An error occurred: {e}")