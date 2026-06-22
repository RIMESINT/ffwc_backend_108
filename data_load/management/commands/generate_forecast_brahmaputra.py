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
    help = 'Fetch Brahmaputra ensemble forecast and probability data'

    def handle(self, *args, **options):
        now = datetime.now()
        run_datetime = now.strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f"[{run_datetime}] Starting Brahmaputra forecast update...")
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Paths configurations
        ACTIVE_ROOT = '/home/bdflood/GBM_MODEL/output_ifs/csv/brahmaputra_new/blending/'
        PB_ROOT = '/home/bdflood/GBM_MODEL/output_ifs/webdat/brahmaputra_new/'
        
        base_assets = os.path.join(settings.BASE_DIR, 'assets', 'flood-monitor-basin-forecast')
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_brahmaputra_forecast.json')

        fd1, temp_csv = tempfile.mkstemp(suffix='_brahmaputra_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_brahmaputra_pb.csv')
        os.close(fd1); os.close(fd2)

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=30)
            sftp = ssh.open_sftp()

            final_folder = None
            date_str = None

            # Lookups: Today -> Yesterday -> Fallback Directory Scan
            today_str = now.strftime('%Y%m%d')
            yesterday_str = (now - timedelta(days=1)).strftime('%Y%m%d')
            
            for folder_date in [today_str, yesterday_str]:
                candidate_folder = f"c.{folder_date}"
                candidate_path = f"{ACTIVE_ROOT}{candidate_folder}/"
                try:
                    sftp.stat(candidate_path)
                    final_folder = candidate_folder
                    date_str = folder_date
                    self.stdout.write(self.style.SUCCESS(f"--> Found active data folder: {candidate_folder}"))
                    break
                except IOError:
                    continue

            if not final_folder:
                self.stdout.write(self.style.WARNING("--> Folder not found for today/yesterday. Scanning directory history..."))
                try:
                    all_entries = sftp.listdir(ACTIVE_ROOT)
                    date_folders = sorted([f for f in all_entries if re.match(r'^c\.\d{8}$', f)], reverse=True)
                    
                    for folder in date_folders[:3]:
                        candidate_path = f"{ACTIVE_ROOT}{folder}/"
                        try:
                            sftp.stat(candidate_path)
                            final_folder = folder
                            date_str = folder.split('.')[-1]
                            self.stdout.write(self.style.SUCCESS(f"--> Fallback found historical folder: {folder}"))
                            break
                        except IOError:
                            continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"--> Could not browse directory root: {e}"))

            if not final_folder:
                raise Exception(f"No valid c.YYYYMMDD forecast folders found under: {ACTIVE_ROOT}")

            # 4. Download & Merge Multiple Ensemble CSV Files
            remote_dir_path = f"{ACTIVE_ROOT}{final_folder}/"
            all_files = sftp.listdir(remote_dir_path)
            
            ensemble_pattern = re.compile(rf'^{date_str}\.corr\.en-\d+\.csv$')
            ensemble_files = [f for f in all_files if ensemble_pattern.match(f)]
            
            if not ensemble_files:
                raise Exception(f"No ensemble CSV files found matching {date_str}.corr.en-*.csv in {remote_dir_path}")
            
            self.stdout.write(f"--> Found {len(ensemble_files)} ensemble files. Processing and merging...")

            master_df = None
            for filename in ensemble_files:
                member_id = filename.split('en-')[-1].replace('.csv', '')
                remote_file_path = f"{remote_dir_path}{filename}"
                
                sftp.get(remote_file_path, temp_csv)
                df_member = pd.read_csv(temp_csv, header=None, names=['Time', f'EN#{member_id}'])
                df_member['Time'] = pd.to_datetime(df_member['Time']).dt.tz_localize(None)
                
                if master_df is None:
                    master_df = df_member
                else:
                    master_df = pd.merge(master_df, df_member, on='Time', how='outer')

            master_df = master_df.sort_values(by='Time').reset_index(drop=True)

            # Slicing from forecast date forward
            f_start = pd.to_datetime(date_str, format='%Y%m%d')
            master_df = master_df[master_df['Time'] >= f_start].copy()

            # Compute Quantiles across the parsed columns
            ensemble_cols = [col for col in master_df.columns if col.startswith('EN#')]
            p05 = master_df[ensemble_cols].quantile(0.05, axis=1).round(3).tolist()
            p25 = master_df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = master_df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = master_df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()
            p95 = master_df[ensemble_cols].quantile(0.95, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = master_df['Time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # 5. Process Probability File from webdat root path (e.g., 20260621.pb.csv)
            pb_dates, pb_values = [], []
            pb_filename = f"{date_str}.pb.csv"
            remote_pb_file = f"{PB_ROOT}{pb_filename}"

            try:
                sftp.get(remote_pb_file, temp_pb_csv)
                df_pb = pd.read_csv(temp_pb_csv)
                
                # Dynamic matching for column names (checking for standard 'ex_pr' or variations)
                pb_col = 'ex_pr' if 'ex_pr' in df_pb.columns else (df_pb.columns[1] if len(df_pb.columns) > 1 else None)
                date_col = 'date' if 'date' in df_pb.columns else (df_pb.columns[0] if len(df_pb.columns) > 0 else None)
                
                if pb_col:
                    pb_values = df_pb[pb_col].tolist()
                    if date_col:
                        pb_dates = pd.to_datetime(df_pb[date_col]).dt.strftime('%Y-%m-%d').tolist()
                    else:
                        pb_dates = [d.split(' ')[0] for d in dates_list[:len(pb_values)]]
                    self.stdout.write(self.style.SUCCESS(f"--> Probability file {pb_filename} successfully processed."))
                else:
                    self.stdout.write(self.style.WARNING("--> Probability file format unrecognized or missing valid columns."))
            except Exception as pb_err:
                self.stdout.write(self.style.WARNING(f"--> Probability file processing skipped or not found ({pb_filename}): {pb_err}"))

            sftp.close(); ssh.close()

            # 6. Save Output JSON
            output_data = {
                "code": "success", "message": f"Fetched and combined from {remote_dir_path} and {PB_ROOT}",
                "metadata": {
                    "station_id": "66", "basin_name": "Brahmaputra River (Bahadurabad)",
                    "forecast_date": formatted_date, "run_datetime": run_datetime,
                    "dc_unit": "m³/s", "dl": "40000", "pb_unit": "%", "forecast_type": "experimental"
                },
                "data": {
                    "date": dates_list, "5%": p05, "25%": p25, "50%": p50, "75%": p75, "95%": p95
                },
                "data_pb": {"date": pb_dates, "pb": pb_values}
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f"DONE: Brahmaputra updated for {formatted_date}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FATAL ERROR: {str(e)}"))
        finally:
            for p in [temp_csv, temp_pb_csv]:
                if os.path.exists(p): os.remove(p)