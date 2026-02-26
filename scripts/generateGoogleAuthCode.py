import os
import json
import requests

# Get the directory of the current script
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the parent directory (your_project_root)
parent_dir = os.path.dirname(current_script_dir)
# Construct the path to the credentials directory
credentials_dir = os.path.join(parent_dir, 'credentials')

# Define the full path to your credentials file
CLIENT_SECRET_FILE = 'hasanCredentials.json'
CLIENT_SECRET_FILE_PATH = os.path.join(credentials_dir, CLIENT_SECRET_FILE)

# Load your credentials
# Use the constructed full path
with open(CLIENT_SECRET_FILE_PATH) as f:
    creds = json.load(f)

# Generate the authorization URL
auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={creds['client_id']}&redirect_uri={creds['redirect_uris'][0]}&scope=https://www.googleapis.com/auth/drive&access_type=offline"
print("Please visit this URL to authorize this application:", auth_url)

# After visiting the URL and getting the code
code = input("Enter the authorization code: ")

# Exchange the authorization code for an access token
token_url = "https://oauth2.googleapis.com/token"
data = {
    'code': code,
    'client_id': creds['client_id'],
    'client_secret': creds['client_secret'],
    'redirect_uri': creds['redirect_uris'][0],
    'grant_type': 'authorization_code'
}

response = requests.post(token_url, data=data)
tokens = response.json()

if 'access_token' in tokens:
    print("Access Token:", tokens['access_token'])
    if 'refresh_token' in tokens:
        print("Refresh Token:", tokens['refresh_token'])
    else:
        print("No refresh token received. Ensure 'access_type=offline' is in auth URL.")
else:
    print("Error getting tokens:", tokens)