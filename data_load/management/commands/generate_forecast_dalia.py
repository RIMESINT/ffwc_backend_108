# -*- coding: utf-8 -*-
import os
import json
import pandas as pd
import paramiko
import re
import warnings
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

# Suppress pandas performance warnings
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class Command(BaseCommand):
    help = 'Scan the new automated folders for Dalia and fetch the most recent ensemble forecast'

    def handle(self, *args, **options):
        # 1. Setup
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # New automated paths for Dalia
        remote_base_dir = '/home/mmb/tank-teesta-new-auto/corrected_output/csv/'
        target_filename = 'all_en_corr_DALIA.csv'
        
        base_assets = os.path.join(settings.BASE_DIR, 'assets', 'flood-monitor-basin-forecast')
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_dalia_forecast.json')

        try:
            # 2. SSH Connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS)
            sftp = ssh.open_sftp()

            # 3. Scan for date folders
            self.stdout.write(f"Scanning {remote_base_dir} for date folders...")
            all_entries = sftp.listdir(remote_base_dir)
            date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)

            if not date_folders:
                raise Exception("No YYYYMMDD folders found on the remote server.")

            remote_file_path = None
            final_date_folder = None

            # 4. Locate the most recent valid file
            for folder in date_folders:
                candidate_path = f"{remote_base_dir}{folder}/{target_filename}"
                try:
                    sftp.stat(candidate_path)
                    remote_file_path = candidate_path
                    final_date_folder = folder
                    self.stdout.write(self.style.SUCCESS(f"Found valid Dalia data in: {folder}"))
                    break
                except IOError:
                    continue

            if not remote_file_path:
                raise Exception(f"Could not find {target_filename} in any recent folders.")

            # 5. Download
            temp_csv = f'/tmp/latest_dalia_temp.csv'
            sftp.get(remote_file_path, temp_csv)
            sftp.close()
            ssh.close()

            # 6. Data Processing
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            
            # Timezone Fix: Strip timezone info to allow comparison with folder date
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)

            # Filter starting from the run date folder name
            forecast_start = pd.to_datetime(final_date_folder, format='%Y%m%d')
            df = df[df[time_col] >= forecast_start].copy()

            # Calculate Percentiles
            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(final_date_folder, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # 7. JSON Output
            output_data = {
                "code": "success",
                "message": "Data has been fetched!",
                "metadata": {
                    "station_id": 'SW291.5R',
                    "basin_name": "Teesta River (Dalia)",
                    "forecast_date": formatted_date,
                    "run_datetime": run_datetime,
                    "dc_unit": "m³/s",
                    "dl": "1850",
                    "pb_unit": "%",
                    "forecast_type": "experimental"
                },
                "data": {
                    "date": dates_list,
                    "25%": p25,
                    "50%": p50,
                    "75%": p75
                }
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated Dalia JSON from folder {final_date_folder}'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Critical Error for Dalia: {str(e)}'))