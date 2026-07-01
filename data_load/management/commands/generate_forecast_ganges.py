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
# Suppress paramiko cryptography deprecation warning logs from STDERR
warnings.filterwarnings("ignore", message=".*TripleDES.*")

class Command(BaseCommand):
    help = 'Fetch Ganges ensemble forecast and probability data supporting UI inputs with rolling fallback'

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Forecast target initialization date in YYYYMMDD format')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Target date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **options):
        # Determine the primary input parameter dynamically across channels
        ui_date = options.get('date')
        positional_date = options.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if not raw_date:
            base_datetime = datetime.now()
        else:
            clean_date_str = raw_date.replace('-', '')
            try:
                base_datetime = datetime.strptime(clean_date_str, "%Y%m%d")
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format received: {raw_date}"))
                return

        # Explicitly configure fallback paths: Selected Target, then Day-1 Yesterday
        target_fdate = base_datetime.strftime('%Y%m%d')
        fallback_fdate = (base_datetime - timedelta(days=1)).strftime('%Y%m%d')

        self.stdout.write(self.style.NOTICE(f"Initializing Ganges Forecast Update Core | Target Window: {target_fdate} | Fallback Day-1: {fallback_fdate}"))

        # Trigger ingestion loop; fall back to yesterday if target folders fail to resolve
        success = self.execute_ingestion_pipeline(target_fdate)
        if not success:
            self.stdout.write(self.style.WARNING(f"⚠️ Data arrays unavailable for target {target_fdate}. Executing historical rolling fallback to: {fallback_fdate}..."))
            success_fallback = self.execute_ingestion_pipeline(fallback_fdate)
            if not success_fallback:
                self.stderr.write(self.style.ERROR(f"❌ Critical Failure: Ganges ensemble data completely missing across both windows."))

    def execute_ingestion_pipeline(self, date_str):
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Paths configurations for Ganges
        ACTIVE_ROOT = '/home/bdflood/GBM_MODEL/output_ifs/csv/ganges/'
        PB_ROOT = '/home/bdflood/GBM_MODEL/output_ifs/webdat/ganges/'
        
        base_assets = os.path.join(settings.BASE_DIR, 'assets', 'flood-monitor-basin-forecast')
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_ganges_forecast.json')

        fd1, temp_csv = tempfile.mkstemp(suffix='_ganges_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_ganges_pb.csv')
        os.close(fd1); os.close(fd2)

        sftp_session_active = False
        ssh_client_active = False

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=30)
            ssh_client_active = True
            
            sftp = ssh.open_sftp()
            sftp_session_active = True

            # Verify target directory presence before initiating merge routines
            target_folder = f"c.{date_str}"
            remote_dir_path = f"{ACTIVE_ROOT}{target_folder}/"
            
            try:
                sftp.stat(remote_dir_path)
                self.stdout.write(self.style.SUCCESS(f"--> Found active data folder matching parameters: {target_folder}"))
            except IOError:
                sftp.close(); ssh.close()
                for p in [temp_csv, temp_pb_csv]:
                    if os.path.exists(p): os.remove(p)
                return False

            # Download & Merge Multiple Ensemble CSV Files
            all_files = sftp.listdir(remote_dir_path)
            ensemble_pattern = re.compile(rf'^{date_str}\.corr\.en-\d+\.csv$')
            ensemble_files = [f for f in all_files if ensemble_pattern.match(f)]
            
            if not ensemble_files:
                self.stdout.write(self.style.WARNING(f"Directory {target_folder} exists but contains no files matching format requirements."))
                sftp.close(); ssh.close()
                for p in [temp_csv, temp_pb_csv]:
                    if os.path.exists(p): os.remove(p)
                return False
            
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

            # Slicing forward from forecast run point
            f_start = pd.to_datetime(date_str, format='%Y%m%d')
            master_df = master_df[master_df['Time'] >= f_start].copy()

            # Compute Quantiles across parsed columns
            ensemble_cols = [col for col in master_df.columns if col.startswith('EN#')]
            p05 = master_df[ensemble_cols].quantile(0.05, axis=1).round(3).tolist()
            p25 = master_df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = master_df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = master_df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()
            p95 = master_df[ensemble_cols].quantile(0.95, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = master_df['Time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # Process Probability File from webdat (e.g., 20260621_b.pb.csv)
            pb_dates, pb_values = [], []
            pb_filename = f"{date_str}_b.pb.csv"
            remote_pb_file = f"{PB_ROOT}{pb_filename}"

            try:
                sftp.stat(remote_pb_file)
                sftp.get(remote_pb_file, temp_pb_csv)
                df_pb = pd.read_csv(temp_pb_csv)
                
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

            # Save Formatted Output JSON (station_id: "101")
            output_data = {
                "code": "success", "message": f"Fetched and combined from {remote_dir_path} and {PB_ROOT}",
                "metadata": {
                    "station_id": "101", "basin_name": "Ganges River (Hardinge Bridge)",
                    "forecast_date": formatted_date, "run_datetime": run_datetime,
                    "dc_unit": "m³/s", "dl": "73240", "pb_unit": "%", "forecast_type": "experimental"
                },
                "data": {
                    "date": dates_list, "5%": p05, "25%": p25, "50%": p50, "75%": p75, "95%": p95
                },
                "data_pb": {"date": pb_dates, "pb": pb_values}
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f"DONE: Ganges updated successfully for run parameter date: {formatted_date}."))
            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Pipeline processing execution error for folder date {date_str}: {str(e)}"))
            return False
        finally:
            if sftp_session_active:
                try: sftp.close()
                except: pass
            if ssh_client_active:
                try: ssh.close()
                except: pass
            for p in [temp_csv, temp_pb_csv]:
                if os.path.exists(p): os.remove(p)