import os
import json
import pandas as pd
import paramiko
import re
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Automatically fetch the latest Cumilla forecast by detecting the most recent date folder'

    def handle(self, *args, **options):
        # 1. Setup
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Base directory where YYYYMMDD folders are stored
        remote_base_dir = '/home/mmb/tank-cumilla-auto/output_corrected/csv/'
        
        # Local paths
        base_assets = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/assets/flood-monitor-basin-forecast'
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_cumilla_forecast.json')

        try:
            # 2. SSH Connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS)
            sftp = ssh.open_sftp()

            # 3. Detect the Latest Folder
            self.stdout.write("Scanning remote directories for the latest date...")
            all_entries = sftp.listdir(remote_base_dir)
            
            # Filter for folders that are exactly 8 digits (YYYYMMDD)
            date_folders = [f for f in all_entries if re.match(r'^\d{8}$', f)]
            
            if not date_folders:
                raise Exception(f"No valid date folders (YYYYMMDD) found in {remote_base_dir}")

            # Sort alphabetically (works perfectly for YYYYMMDD) and pick the last one
            latest_date = sorted(date_folders)[-1]
            self.stdout.write(self.style.SUCCESS(f"Latest folder detected: {latest_date}"))

            # 4. Define full remote path and download
            remote_file_path = f'{remote_base_dir}{latest_date}/all_en_corr_cumilla.csv'
            temp_csv = f'/tmp/latest_cumilla_temp.csv'
            
            sftp.get(remote_file_path, temp_csv)
            sftp.close()
            ssh.close()

            # 5. Data Processing
            df = pd.read_csv(temp_csv)
            
            # Use 'Time' column as per your original file structure
            df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            
            # Calculate Quantiles as seen in your extracted data
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(latest_date, "%Y%m%d").strftime("%Y-%m-%d")
            # 6. Construct JSON Structure
            output_data = {
                "code": "success",
                "message": "Data has been fetched!",
                "metadata": {
                    "station_id": 'SW110',
                    "basin_name": "Gumti River (Cumilla)",
                    "forecast_date": formatted_date,
                    "run_datetime": run_datetime,
                    "dc_unit": "m³/s",
                    "dl":"290",
                    "pb_unit": "%"
                },
                "data": {
                    "date": df['Time'].tolist(),
                    "25%": p25,
                    "50%": p50,
                    "75%": p75
                }
            }

            # 7. Overwrite existing file
            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated latest_cumilla_forecast.json using data from folder {latest_date}'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error processing Cumilla: {str(e)}'))