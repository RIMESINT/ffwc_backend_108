import os
import json
import pandas as pd
import paramiko
import re
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Scan available YYYYMMDD folders for Amalshid and fetch the most recent valid forecast'

    def handle(self, *args, **options):
        # 1. Setup
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        remote_base_dir = '/home/mmb/Tank/outputs_corrected/amalshid_s/csv/'
        target_filename = 'all_en_amalshid_s_corr.csv'
        
        base_assets = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/assets/flood-monitor-basin-forecast'
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_amalshid_forecast.json')

        try:
            # 2. SSH Connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS)
            sftp = ssh.open_sftp()

            # 3. Check existing YYYYMMDD list
            self.stdout.write(f"Scanning {remote_base_dir} for date folders...")
            all_entries = sftp.listdir(remote_base_dir)
            
            # Filter and sort folders descending (newest first)
            date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)

            if not date_folders:
                raise Exception("No YYYYMMDD folders found on the remote server.")

            remote_file_path = None
            final_date_folder = None

            # 4. Find the first folder that actually contains the CSV
            for folder in date_folders:
                candidate_path = f"{remote_base_dir}{folder}/{target_filename}"
                try:
                    sftp.stat(candidate_path)  # Check if file exists
                    remote_file_path = candidate_path
                    final_date_folder = folder
                    self.stdout.write(self.style.SUCCESS(f"Found valid data in: {folder}"))
                    break
                except IOError:
                    # File doesn't exist in this folder, try the next one
                    self.stdout.write(f"Folder {folder} exists, but {target_filename} is missing. Checking previous day...")

            if not remote_file_path:
                raise Exception(f"Searched {len(date_folders)} folders but could not find {target_filename}.")

            # 5. Download the file
            temp_csv = f'/tmp/latest_amalshid_temp.csv'
            sftp.get(remote_file_path, temp_csv)
            sftp.close()
            ssh.close()

            # 6. Data Processing & Filtering
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            df[time_col] = pd.to_datetime(df[time_col])

            # Filter: Start forecast from the day the data was found
            forecast_start = pd.to_datetime(final_date_folder, format='%Y%m%d')
            df = df[df[time_col] >= forecast_start].copy()

            # Format for JSON
            df[time_col] = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S')
            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]

            # Calculate Percentiles
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(final_date_folder, "%Y%m%d").strftime("%Y-%m-%d")

            # 7. Final JSON Construction
            output_data = {
                "code": "success",
                "message": "Data has been fetched!",
                "metadata": {
                    "station_id": 'SW172',
                    "basin_name": "Kushiyara River (Amalshid)",
                    "forecast_date": formatted_date,
                    "run_datetime": run_datetime,
                    "dc_unit": "m³/s",
                    "dl":"1800",
                    "pb_unit": "%"
                },
                "data": {
                    "date": df[time_col].tolist(),
                    "25%": p25,
                    "50%": p50,
                    "75%": p75
                }
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated latest_amalshid_forecast.json from folder {final_date_folder}'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Critical Error for Amalshid: {str(e)}'))