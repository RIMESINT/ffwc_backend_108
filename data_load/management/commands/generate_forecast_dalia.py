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
    help = 'Fetch Dalia ensemble forecast from the corrected Teesta auto path'

    def handle(self, *args, **options):
        # 1. Setup
        now = datetime.now()
        run_datetime = now.strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f"[{run_datetime}] Starting Dalia forecast update...")
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Verified active path configuration
        ACTIVE_ROOT = '/home/mmb/tank-teesta-new-auto/outputs_corrected/csv/'
        TARGET_FILE = 'all_en_corr_DALIA.csv'
        
        base_assets = os.path.join(settings.BASE_DIR, 'assets', 'flood-monitor-basin-forecast')
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_dalia_forecast.json')

        fd1, temp_csv = tempfile.mkstemp(suffix='_dalia_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_dalia_pb.csv')
        os.close(fd1); os.close(fd2)

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=30)
            sftp = ssh.open_sftp()

            remote_file_path = None
            final_date_folder = None

            # --- Try Directory Lookups (Today -> Yesterday -> Fallback Scan) ---
            today_str = now.strftime('%Y%m%d')
            yesterday_str = (now - timedelta(days=1)).strftime('%Y%m%d')
            
            for folder in [today_str, yesterday_str]:
                candidate = f"{ACTIVE_ROOT}{folder}/{TARGET_FILE}"
                try:
                    sftp.stat(candidate)
                    remote_file_path = candidate
                    final_date_folder = folder
                    self.stdout.write(self.style.SUCCESS(f"--> Found active data folder: {folder}"))
                    break
                except IOError:
                    continue

            # Dynamic Fallback: if today/yesterday aren't generated yet, find the most recent folder dynamically
            if not remote_file_path:
                self.stdout.write(self.style.WARNING("--> File not found for today/yesterday. Scanning directory history..."))
                try:
                    all_entries = sftp.listdir(ACTIVE_ROOT)
                    date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)
                    
                    for folder in date_folders[:3]:
                        candidate = f"{ACTIVE_ROOT}{folder}/{TARGET_FILE}"
                        try:
                            sftp.stat(candidate)
                            remote_file_path = candidate
                            final_date_folder = folder
                            self.stdout.write(self.style.SUCCESS(f"--> Fallback found historical folder: {folder}"))
                            break
                        except IOError:
                            continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"--> Could not browse directory root: {e}"))

            if not remote_file_path:
                raise Exception(f"Target file '{TARGET_FILE}' completely missing from paths under: {ACTIVE_ROOT}")

            # 4. Download & Process Main CSV
            sftp.get(remote_file_path, temp_csv)
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)

            # Slicing from forecast date onward
            f_start = pd.to_datetime(final_date_folder, format='%Y%m%d')
            df = df[df[time_col] >= f_start].copy()

            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            p05 = df[ensemble_cols].quantile(0.05, axis=1).round(3).tolist()
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()
            p95 = df[ensemble_cols].quantile(0.95, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(final_date_folder, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # 5. Download & Process Probability File (data_pb)
            pb_dates, pb_values = [], []
            pb_name = f"exceedence{final_date_folder}.csv"
            remote_pb_file = f"{ACTIVE_ROOT}{final_date_folder}/{pb_name}"

            try:
                sftp.get(remote_pb_file, temp_pb_csv)
                df_pb = pd.read_csv(temp_pb_csv)
                if 'ex_pr' in df_pb.columns:
                    pb_values = df_pb['ex_pr'].tolist()
                    pb_dates = pd.to_datetime(df_pb['date']).dt.strftime('%Y-%m-%d').tolist() if 'date' in df_pb.columns else [d.split(' ')[0] for d in dates_list[:len(pb_values)]]
                self.stdout.write(self.style.SUCCESS("--> Probability file successfully loaded."))
            except Exception as pb_err:
                self.stdout.write(self.style.WARNING(f"--> Probability file processing skipped or not found: {pb_err}"))

            sftp.close(); ssh.close()

            # 6. Save Formatted JSON Output
            output_data = {
                "code": "success", "message": f"Fetched from {ACTIVE_ROOT}",
                "metadata": {
                    "station_id": 'SW291.5R', "basin_name": "Teesta River (Dalia)",
                    "forecast_date": formatted_date, "run_datetime": run_datetime,
                    "dc_unit": "m³/s", "dl": "1850", "pb_unit": "%", "forecast_type": "experimental"
                },
                "data": {
                    "date": dates_list, "5%": p05, "25%": p25, "50%": p50, "75%": p75, "95%": p95
                },
                "data_pb": {"date": pb_dates, "pb": pb_values}
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f"DONE: Dalia updated for {formatted_date}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FATAL ERROR: {str(e)}"))
        finally:
            for p in [temp_csv, temp_pb_csv]:
                if os.path.exists(p): os.remove(p)