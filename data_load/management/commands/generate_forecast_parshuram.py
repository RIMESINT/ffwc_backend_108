# -*- coding: utf-8 -*-
import os
import json
import pandas as pd
import paramiko
import re
import warnings
import tempfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

# Suppress pandas performance warnings
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class Command(BaseCommand):
    help = 'Fetch Parshuram ensemble forecast + probability with terminal progress tracing'

    def handle(self, *args, **options):
        # 1. Setup
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f"[{run_datetime}] Starting Parshuram forecast update...")
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # UPDATED: Changed 'output_corrected' to 'outputs_corrected'
        remote_base_dir = '/home/mmb/tank-feni-auto/outputs_corrected/csv/'
        # UPDATED: Matches your confirmed filename
        target_filename = 'all_en_feni_corr.csv'
        
        base_assets = os.path.join(settings.BASE_DIR, 'assets', 'flood-monitor-basin-forecast')
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_parshuram_forecast.json')

        fd1, temp_csv = tempfile.mkstemp(suffix='_parshuram_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_parshuram_pb.csv')
        os.close(fd1)
        os.close(fd2)

        try:
            # 2. SSH Connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=30)
            self.stdout.write(self.style.SUCCESS("--> SSH Connection established."))
            sftp = ssh.open_sftp()

            # 3. Scan for date folders
            all_entries = sftp.listdir(remote_base_dir)
            date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)

            if not date_folders:
                raise Exception(f"No YYYYMMDD folders found in {remote_base_dir}")

            latest_date = date_folders[0]
            remote_folder_path = f"{remote_base_dir}{latest_date}/"

            # 4. Download Main Forecast
            remote_file_path = f"{remote_folder_path}{target_filename}"
            self.stdout.write(f"--> Attempting Main CSV: {remote_file_path}")
            sftp.get(remote_file_path, temp_csv)

            # 5. Data Processing
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)

            forecast_start = pd.to_datetime(latest_date, format='%Y%m%d')
            df = df[df[time_col] >= forecast_start].copy()

            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(latest_date, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # 6. Probability Computation
            pb_dates = []
            pb_values = []
            # Generic naming: exceedence_YYYYMMDD_feni.csv
            remote_pb_filename = f"exceedence_{latest_date}_feni.csv"
            remote_pb_file = f"{remote_folder_path}{remote_pb_filename}"

            try:
                self.stdout.write(f"--> Attempting Probability CSV: {remote_pb_file}")
                sftp.stat(remote_pb_file)
                sftp.get(remote_pb_file, temp_pb_csv)
                df_pb = pd.read_csv(temp_pb_csv)
                
                if 'ex_pr' in df_pb.columns:
                    pb_values = df_pb['ex_pr'].tolist()
                    if 'date' in df_pb.columns:
                        pb_dates = pd.to_datetime(df_pb['date']).dt.strftime('%Y-%m-%d').tolist()
                    else:
                        pb_dates = [d.split(' ')[0] for d in dates_list[:len(pb_values)]]
            except Exception as pb_err:
                self.stdout.write(self.style.WARNING(f"--> PB File skipped: {pb_err}"))

            sftp.close()
            ssh.close()

            # 7. JSON Output
            output_data = {
                "code": "success",
                "message": "Data has been fetched!",
                "metadata": {
                    "station_id": 'SW212',
                    "basin_name": "Feni River (Parshuram)",
                    "forecast_date": formatted_date,
                    "run_datetime": run_datetime,
                    "dc_unit": "m³/s",
                    "dl": "240",
                    "pb_unit": "%",
                    "forecast_type": "experimental"
                },
                "data": {"date": dates_list, "25%": p25, "50%": p50, "75%": p75},
                "data_pb": {"date": pb_dates, "pb": pb_values}
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f"DONE: Parshuram updated for {formatted_date}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Critical Error: {str(e)}"))

        finally:
            for f_path in [temp_csv, temp_pb_csv]:
                if os.path.exists(f_path):
                    os.remove(f_path)