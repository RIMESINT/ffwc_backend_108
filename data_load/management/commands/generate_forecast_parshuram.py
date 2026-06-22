# -*- coding: utf-8 -*-
import os
import json
import pandas as pd
import paramiko
import re
import warnings
import tempfile
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

# Suppress pandas performance warnings
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class Command(BaseCommand):
    help = 'Fetch Parshuram ensemble forecast (5% to 95%) with nested fallback (New Path -> Old Path)'

    def handle(self, *args, **options):
        # 1. Setup
        now = datetime.now()
        run_datetime = now.strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f"[{run_datetime}] Starting Parshuram forecast update...")
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Directory Constants
        NEW_ROOT = '/home/mmb/Tank_All_Output/'
        OLD_ROOT = '/home/mmb/tank-feni-auto/outputs_corrected/csv/'
        TARGET_FILE = 'all_en_feni_corr.csv'
        
        base_assets = os.path.join(settings.BASE_DIR, 'assets', 'flood-monitor-basin-forecast')
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_parshuram_forecast.json')

        fd1, temp_csv = tempfile.mkstemp(suffix='_parshuram_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_parshuram_pb.csv')
        os.close(fd1); os.close(fd2)

        try:
            # 2. SSH Connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=30)
            self.stdout.write(self.style.SUCCESS("--> SSH Connection established."))
            sftp = ssh.open_sftp()

            remote_file_path = None
            final_date_folder = None
            current_active_root = NEW_ROOT

            # --- STEP 1: Try NEW Directory Structure (Today/Yesterday) ---
            today_str = now.strftime('%Y%m%d')
            yesterday_str = (now - timedelta(days=1)).strftime('%Y%m%d')
            
            for folder in [today_str, yesterday_str]:
                candidate = f"{NEW_ROOT}{folder}/{TARGET_FILE}"
                try:
                    sftp.stat(candidate)
                    remote_file_path = candidate
                    final_date_folder = folder
                    self.stdout.write(self.style.SUCCESS(f"--> Found in NEW directory: {folder}"))
                    break
                except IOError:
                    continue

            # --- STEP 2: Try OLD Directory Structure (Fallback Scan) ---
            if not remote_file_path:
                self.stdout.write(self.style.WARNING("--> Not found in NEW root. Checking OLD directory..."))
                try:
                    all_entries = sftp.listdir(OLD_ROOT)
                    date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)
                    
                    for folder in date_folders[:3]: # Check 3 most recent
                        candidate = f"{OLD_ROOT}{folder}/{TARGET_FILE}"
                        try:
                            sftp.stat(candidate)
                            remote_file_path = candidate
                            final_date_folder = folder
                            current_active_root = OLD_ROOT
                            self.stdout.write(self.style.SUCCESS(f"--> Found in OLD directory fallback: {folder}"))
                            break
                        except IOError:
                            continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"--> Could not access OLD directory: {e}"))

            if not remote_file_path:
                raise Exception("Data not found in either NEW or OLD Parshuram directory structures.")

            # 3. Download & Process Main Forecast
            sftp.get(remote_file_path, temp_csv)
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)

            forecast_start = pd.to_datetime(final_date_folder, format='%Y%m%d')
            df = df[df[time_col] >= forecast_start].copy()

            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            
            # Expanded Quantiles
            p05 = df[ensemble_cols].quantile(0.05, axis=1).round(3).tolist()
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()
            p95 = df[ensemble_cols].quantile(0.95, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(final_date_folder, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # 4. Probability Computation
            pb_dates, pb_values = [], []
            pb_name = f"exceedence_{final_date_folder}_feni.csv"
            remote_pb_file = f"{current_active_root}{final_date_folder}/{pb_name}"

            try:
                sftp.get(remote_pb_file, temp_pb_csv)
                df_pb = pd.read_csv(temp_pb_csv)
                if 'ex_pr' in df_pb.columns:
                    pb_values = df_pb['ex_pr'].tolist()
                    pb_dates = pd.to_datetime(df_pb['date']).dt.strftime('%Y-%m-%d').tolist() if 'date' in df_pb.columns else [d.split(' ')[0] for d in dates_list[:len(pb_values)]]
            except Exception as pb_err:
                self.stdout.write(self.style.WARNING(f"--> Probability file skipped or not found: {pb_err}"))

            sftp.close(); ssh.close()

            # 5. Save JSON Output
            output_data = {
                "code": "success",
                "message": f"Fetched from {current_active_root}",
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
                "data": {
                    "date": dates_list,
                    "5%": p05,
                    "25%": p25,
                    "50%": p50,
                    "75%": p75,
                    "95%": p95
                },
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