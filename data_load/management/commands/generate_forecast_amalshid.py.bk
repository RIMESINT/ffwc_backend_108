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

# Suppress pandas performance warnings if necessary
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class Command(BaseCommand):
    help = 'Fetch Amalshid ensemble forecast + probability with terminal progress tracing'

    def handle(self, *args, **options):
        # 1. Setup
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f"[{run_datetime}] Starting Amalshid forecast update...")
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Base directory and filename for Amalshid
        remote_base_dir = '/home/mmb/Tank/outputs_corrected/amalshid_s/csv/'
        target_filename = 'all_en_amalshid_s_corr.csv'
        
        # Local paths
        base_assets = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/assets/flood-monitor-basin-forecast'
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_amalshid_forecast.json')

        # Use tempfile to avoid permission/cleanup issues
        fd1, temp_csv = tempfile.mkstemp(suffix='_amalshid_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_amalshid_pb.csv')
        os.close(fd1)
        os.close(fd2)

        try:
            # 2. SSH Connection with banner timeout
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.stdout.write(f"--> Connecting to {REMOTE_HOST}...")
            ssh.connect(
                REMOTE_HOST, 
                username=REMOTE_USER, 
                password=REMOTE_PASS, 
                timeout=30, 
                banner_timeout=30 
            )
            self.stdout.write(self.style.SUCCESS("--> SSH Connection established."))
            sftp = ssh.open_sftp()

            # 3. Scan for date folders
            self.stdout.write(f"--> Scanning remote directory: {remote_base_dir}")
            all_entries = sftp.listdir(remote_base_dir)
            date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)
            
            if not date_folders:
                raise Exception(f"No valid date folders found in {remote_base_dir}")

            remote_file_path = None
            final_date_folder = None

            # 4. Find the first folder that actually contains the CSV file
            self.stdout.write("--> Searching for the most recent valid data folder...")
            for folder in date_folders:
                candidate_path = f"{remote_base_dir}{folder}/{target_filename}"
                try:
                    sftp.stat(candidate_path)
                    remote_file_path = candidate_path
                    final_date_folder = folder
                    self.stdout.write(self.style.SUCCESS(f"--> Found target file in folder: {folder}"))
                    break
                except IOError:
                    continue

            if not remote_file_path:
                raise Exception(f"Could not find {target_filename} in recent folders.")

            # 5. Download the main forecast file
            self.stdout.write(f"--> Downloading main forecast: {target_filename}")
            sftp.get(remote_file_path, temp_csv)
            self.stdout.write("--> Main forecast download complete.")

            # 6. Data Processing & Filtering
            self.stdout.write("--> Processing forecast data...")
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            
            # Fix timezone mismatch
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)
            
            # Filtering logic
            forecast_start_threshold = pd.to_datetime(final_date_folder, format='%Y%m%d')
            df = df[df[time_col] >= forecast_start_threshold].copy()

            # Prepare for JSON
            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(final_date_folder, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
            self.stdout.write(f"--> Processed {len(dates_list)} forecast time steps.")

            # 7. Probability Computation (data_pb)
            # UPDATED: File naming convention and parsing logic
            pb_dates = []
            pb_values = []
            # Updated pattern: exceedence_YYYYMMDD_amalshid_s.csv
            remote_pb_filename = f"exceedence_{final_date_folder}_amalshid_s.csv"
            remote_pb_file = f"{remote_base_dir}{final_date_folder}/{remote_pb_filename}"

            self.stdout.write(f"--> Checking for exceedence file: {remote_pb_filename}")
            try:
                sftp.get(remote_pb_file, temp_pb_csv)
                self.stdout.write("--> Exceedence file downloaded. Parsing...")
                df_pb = pd.read_csv(temp_pb_csv)
                
                # Check for required columns: 'ex_pr' and 'date'
                if 'ex_pr' in df_pb.columns:
                    pb_values = df_pb['ex_pr'].tolist()
                    
                    if 'date' in df_pb.columns:
                        # Extract dates directly from the exceedence CSV
                        pb_dates = pd.to_datetime(df_pb['date']).dt.strftime('%Y-%m-%d').tolist()
                    else:
                        # Fallback if 'date' column is missing: align with main dates list
                        pb_dates = dates_list[:len(pb_values)]
                        self.stdout.write(self.style.WARNING("--> Column 'date' missing in exceedence file. Falling back to main date sequence."))
                    
                    self.stdout.write(self.style.SUCCESS(f"--> Probability data loaded ({len(pb_values)} entries)."))
                else:
                    self.stdout.write(self.style.WARNING("--> Column 'ex_pr' missing in exceedence file. Skipping pb data."))
            except Exception as pb_err:
                self.stdout.write(self.style.WARNING(f"--> Exceedence file not found or error: {pb_err}"))

            sftp.close()
            ssh.close()

            # 8. Construct JSON Structure
            self.stdout.write(f"--> Saving final JSON to: {local_json_path}")
            output_data = {
                "code": "success",
                "message": "Data has been fetched!",
                "metadata": {
                    "station_id": 'SW1',
                    "basin_name": "Kushiyara River (Amalshid)",
                    "forecast_date": formatted_date,
                    "run_datetime": run_datetime,
                    "dc_unit": "m³/s",
                    "dl": "15.40",
                    "pb_unit": "%",
                    "forecast_type": "experimental"
                },
                "data": {
                    "date": dates_list,
                    "25%": p25,
                    "50%": p50,
                    "75%": p75
                },
                "data_pb": {
                    "date": pb_dates,
                    "pb": pb_values
                }
            }

            # Overwrite existing file
            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f"DONE: Amalshid forecast successfully updated for {formatted_date}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FATAL ERROR for Amalshid: {str(e)}"))
        
        finally:
            self.stdout.write("--> Cleaning up temporary files...")
            for f_path in [temp_csv, temp_pb_csv]:
                if os.path.exists(f_path):
                    os.remove(f_path)
            self.stdout.write("--> Cleanup complete.")