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
    help = 'Fetch Dalia ensemble forecast supporting manual UI date parameters with historical rollback'

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Forecast target initialization date in YYYYMMDD format')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Target date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **options):
        # Capture parameter inputs across standard option channels
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

        # Explicitly configure recursive step windows: Selected Target, then Day-1 Yesterday
        target_fdate = base_datetime.strftime('%Y%m%d')
        fallback_fdate = (base_datetime - timedelta(days=1)).strftime('%Y%m%d')

        self.stdout.write(self.style.NOTICE(f"Initializing Dalia Forecast Update Core | Target Window: {target_fdate} | Fallback Day-1: {fallback_fdate}"))

        # Trigger ingestion sequence; fall back automatically if the target folder is empty
        success = self.execute_ingestion_pipeline(target_fdate)
        if not success:
            self.stdout.write(self.style.WARNING(f"⚠️ Data arrays unavailable for target {target_fdate}. Executing historical rolling fallback to: {fallback_fdate}..."))
            success_fallback = self.execute_ingestion_pipeline(fallback_fdate)
            if not success_fallback:
                self.stderr.write(self.style.ERROR(f"❌ Critical Failure: Dalia ensemble data missing across both primary and fallback options."))

    def execute_ingestion_pipeline(self, date_folder_str):
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'

        # Verified active path configuration
        ACTIVE_ROOT = '/home/mmb/tank-teesta-new-auto/outputs_corrected/csv/'
        TARGET_FILE = 'all_en_corr_DALIA.csv'
        
        base_assets = os.path.join(settings.BASE_DIR, 'assets', 'flood-monitor-basin-forecast')
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_dalia_forecast.json')

        # Use safe temporary files for background download pipelines
        fd1, temp_csv = tempfile.mkstemp(suffix='_dalia_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_dalia_pb.csv')
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

            remote_file_path = f"{ACTIVE_ROOT}{date_folder_str}/{TARGET_FILE}"
            
            # Verify file exists on remote server path for the designated folder parameter
            try:
                sftp.stat(remote_file_path)
                self.stdout.write(self.style.SUCCESS(f"--> Found active data folder matching parameters: {date_folder_str}"))
            except IOError:
                # If path doesn't exist, terminate session safely and report back to handle() fallback loop
                sftp.close(); ssh.close()
                for p in [temp_csv, temp_pb_csv]:
                    if os.path.exists(p): os.remove(p)
                return False

            # Download & Process Main CSV
            sftp.get(remote_file_path, temp_csv)
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)

            # Slicing from forecast date onward
            f_start = pd.to_datetime(date_folder_str, format='%Y%m%d')
            df = df[df[time_col] >= f_start].copy()

            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            p05 = df[ensemble_cols].quantile(0.05, axis=1).round(3).tolist()
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()
            p95 = df[ensemble_cols].quantile(0.95, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(date_folder_str, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # Download & Process Probability File (data_pb)
            pb_dates, pb_values = [], []
            pb_name = f"exceedence{date_folder_str}.csv"
            remote_pb_file = f"{ACTIVE_ROOT}{date_folder_str}/{pb_name}"

            try:
                sftp.stat(remote_pb_file)
                sftp.get(remote_pb_file, temp_pb_csv)
                df_pb = pd.read_csv(temp_pb_csv)
                if 'ex_pr' in df_pb.columns:
                    pb_values = df_pb['ex_pr'].tolist()
                    pb_dates = pd.to_datetime(df_pb['date']).dt.strftime('%Y-%m-%d').tolist() if 'date' in df_pb.columns else [d.split(' ')[0] for d in dates_list[:len(pb_values)]]
                self.stdout.write(self.style.SUCCESS("--> Probability file successfully loaded."))
            except Exception as pb_err:
                self.stdout.write(self.style.WARNING(f"--> Probability file processing skipped or not found: {pb_err}"))

            sftp.close(); ssh.close()

            # Save Formatted JSON Output
            output_data = {
                "code": "success", "message": f"Fetched from {ACTIVE_ROOT}",
                "metadata": {
                    "station_id": 'SW291.5R', "basin_name": "Teesta River (Dalia)",
                    "forecast_date": formatted_date, "run_datetime": run_datetime,
                    "dc_unit": "m³/s", "dl": "2600", "pb_unit": "%", "forecast_type": "experimental"
                },
                "data": {
                    "date": dates_list, "5%": p05, "25%": p25, "50%": p50, "75%": p75, "95%": p95
                },
                "data_pb": {"date": pb_dates, "pb": pb_values}
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f"DONE: Dalia updated successfully for run parameter date: {formatted_date}."))
            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Pipeline processing execution error for folder date {date_folder_str}: {str(e)}"))
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