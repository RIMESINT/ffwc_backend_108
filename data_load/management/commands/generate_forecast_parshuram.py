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
    help = 'Fetch Parshuram ensemble forecast supporting manual UI date parameters with historical rollback'

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

        self.stdout.write(self.style.NOTICE(f"Initializing Parshuram Forecast Update Core | Target Window: {target_fdate} | Fallback Day-1: {fallback_fdate}"))

        # Trigger ingestion sequence; fall back automatically if the target folder is empty
        success = self.execute_ingestion_pipeline(target_fdate)
        if not success:
            self.stdout.write(self.style.WARNING(f"⚠️ Data arrays unavailable for target {target_fdate}. Executing historical rolling fallback to: {fallback_fdate}..."))
            success_fallback = self.execute_ingestion_pipeline(fallback_fdate)
            if not success_fallback:
                self.stderr.write(self.style.ERROR(f"❌ Critical Failure: Parshuram ensemble data missing across both primary and fallback options."))

    def execute_ingestion_pipeline(self, date_folder_str):
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
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

        # Use safe temporary files for background download pipelines
        fd1, temp_csv = tempfile.mkstemp(suffix='_parshuram_main.csv')
        fd2, temp_pb_csv = tempfile.mkstemp(suffix='_parshuram_pb.csv')
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

            remote_file_path = None
            current_active_root = NEW_ROOT

            # --- STEP 1: Attempt Ingestion from NEW Directory structure using the parameter date folder ---
            candidate_new = f"{NEW_ROOT}{date_folder_str}/{TARGET_FILE}"
            try:
                sftp.stat(candidate_new)
                remote_file_path = candidate_new
                self.stdout.write(self.style.SUCCESS(f"--> Found ensemble stream inside NEW server folder: {date_folder_str}"))
            except IOError:
                pass

            # --- STEP 2: Attempt Ingestion from OLD Directory Fallback if missing from NEW ---
            if not remote_file_path:
                candidate_old = f"{OLD_ROOT}{date_folder_str}/{TARGET_FILE}"
                try:
                    sftp.stat(candidate_old)
                    remote_file_path = candidate_old
                    current_active_root = OLD_ROOT
                    self.stdout.write(self.style.SUCCESS(f"--> Found ensemble stream inside OLD server folder fallback: {date_folder_str}"))
                except IOError:
                    pass

            # If both paths return blank results for this specific directory, abort to trigger fallback loop
            if not remote_file_path:
                sftp.close(); ssh.close()
                for f_path in [temp_csv, temp_pb_csv]:
                    if os.path.exists(f_path): os.remove(f_path)
                return False

            # Download & Process Main Forecast
            sftp.get(remote_file_path, temp_csv)
            df = pd.read_csv(temp_csv)
            time_col = 'Time' if 'Time' in df.columns else 'Date'
            df[time_col] = pd.to_datetime(df[time_col]).dt.tz_localize(None)

            forecast_start = pd.to_datetime(date_folder_str, format='%Y%m%d')
            df = df[df[time_col] >= forecast_start].copy()

            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            
            p05 = df[ensemble_cols].quantile(0.05, axis=1).round(3).tolist()
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()
            p95 = df[ensemble_cols].quantile(0.95, axis=1).round(3).tolist()

            formatted_date = datetime.strptime(date_folder_str, "%Y%m%d").strftime("%Y-%m-%d")
            dates_list = df[time_col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # Process probability exceedence arrays
            pb_dates, pb_values = [], []
            pb_name = f"exceedence_{date_folder_str}_feni.csv"
            remote_pb_file = f"{current_active_root}{date_folder_str}/{pb_name}"

            try:
                sftp.stat(remote_pb_file)
                sftp.get(remote_pb_file, temp_pb_csv)
                df_pb = pd.read_csv(temp_pb_csv)
                if 'ex_pr' in df_pb.columns:
                    pb_values = df_pb['ex_pr'].tolist()
                    pb_dates = pd.to_datetime(df_pb['date']).dt.strftime('%Y-%m-%d').tolist() if 'date' in df_pb.columns else [d.split(' ')[0] for d in dates_list[:len(pb_values)]]
            except Exception as pb_err:
                self.stdout.write(self.style.WARNING(f"--> Probability exceedence file skipped or not found: {pb_err}"))

            sftp.close(); ssh.close()

            # Construct structured output JSON manifest payload
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

            self.stdout.write(self.style.SUCCESS(f"DONE: Parshuram updated successfully for run parameter date: {formatted_date}."))
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
            for f_path in [temp_csv, temp_pb_csv]:
                if os.path.exists(f_path):
                    os.remove(f_path)