import os
import json
import pandas as pd
import paramiko
import re
import tempfile
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Scan available folders for Amalshid, fetch the most recent valid forecast, and filter out historical data'

    def handle(self, *args, **options):
        # 1. Setup
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Base directory and filename for Amalshid
        remote_base_dir = '/home/mmb/Tank/outputs_corrected/amalshid_s/csv/'
        # target_filename = 'all_en_amalshid_corr.csv'
        target_filename = 'all_en_amalshid_s_corr.csv'
        
        
        # Local paths
        base_assets = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/assets/flood-monitor-basin-forecast'
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_amalshid_forecast.json')
        # local_json_path = os.path.join(base_assets, 'latest_amalshid_forecast.json')

        # all_en_amalshid_s_corr.csv

        # Use a tempfile name that is unique to this execution
        fd, temp_csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd) # Close the file descriptor so sftp can write to it

        try:
            # 2. SSH Connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS)
            sftp = ssh.open_sftp()

            # 3. Detect the Latest Valid Folder
            self.stdout.write(f"Scanning {remote_base_dir} for date folders...")
            all_entries = sftp.listdir(remote_base_dir)
            
            # Sort folders descending (newest YYYYMMDD first)
            date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)
            
            if not date_folders:
                raise Exception(f"No valid date folders found in {remote_base_dir}")

            remote_file_path = None
            final_date_folder = None

            # 4. Find the first folder that actually contains the CSV file
            for folder in date_folders:
                candidate_path = f"{remote_base_dir}{folder}/{target_filename}"
                try:
                    sftp.stat(candidate_path)
                    remote_file_path = candidate_path
                    final_date_folder = folder
                    self.stdout.write(self.style.SUCCESS(f"Found valid data in: {folder}"))
                    break
                except IOError:
                    continue

            if not remote_file_path:
                raise Exception(f"Could not find {target_filename} in recent folders.")

            # 5. Download the file to the unique temp path
            sftp.get(remote_file_path, temp_csv_path)
            sftp.close()
            ssh.close()

            # 6. Data Processing & Filtering
            df = pd.read_csv(temp_csv_path)
            
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            
            # Fix timezone mismatch
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)
            
            # Filtering logic
            forecast_start_threshold = pd.to_datetime(final_date_folder, format='%Y%m%d')
            df = df[df[time_col] >= forecast_start_threshold].copy()

            # Prepare for JSON
            df[time_col] = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S')
            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(final_date_folder, "%Y%m%d").strftime("%Y-%m-%d")

            # 7. Construct JSON Structure
            output_data = {
                "code": "success",
                "message": "Data has been fetched!",
                "metadata": {
                    "station_id": 'SW1', # Adjust ID if necessary
                    "basin_name": "Kushiyara River (Amalshid)",
                    "forecast_date": formatted_date,
                    "run_datetime": run_datetime,
                    "dc_unit": "m³/s",
                    "dl": "15.40", # Adjust Danger Level if necessary
                    "pb_unit": "%",
                    "forecast_type": "experimental"
                },
                "data": {
                    "date": df[time_col].tolist(),
                    "25%": p25,
                    "50%": p50,
                    "75%": p75
                }
            }

            # 8. Overwrite existing file
            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated latest_amalshid_forecast.json'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Critical Error for Amalshid: {str(e)}'))
        
        finally:
            # Clean up the temp file
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)