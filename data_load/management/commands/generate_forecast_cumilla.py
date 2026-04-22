import os
import json
import pandas as pd
import paramiko
import re
import tempfile
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Fetch latest Cumilla forecast and exceedence probability'

    def handle(self, *args, **options):
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'
        
        # Verify if this is 'outputs_corrected' or 'output_corrected' on server
        remote_base_dir = '/home/mmb/tank-cumilla-auto/outputs_corrected/csv/'
        
        base_assets = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/assets/flood-monitor-basin-forecast'
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_cumilla_forecast.json')

        fd1, temp_csv_path = tempfile.mkstemp(suffix='_main.csv')
        fd2, temp_pb_csv_path = tempfile.mkstemp(suffix='_pb.csv')
        os.close(fd1)
        os.close(fd2)

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=30)
            sftp = ssh.open_sftp()

            # 1. Detect the Latest Folder
            self.stdout.write(f"--> Scanning: {remote_base_dir}")
            all_entries = sftp.listdir(remote_base_dir)
            date_folders = sorted([f for f in all_entries if re.match(r'^\d{8}$', f)], reverse=True)
            
            if not date_folders:
                raise Exception(f"No valid date folders found in {remote_base_dir}")
            
            latest_date = date_folders[0]
            remote_folder_path = f'{remote_base_dir}{latest_date}/'
            self.stdout.write(f"--> Target Folder: {remote_folder_path}")

            # 2. Process Main Forecast Data
            remote_forecast_file = f'{remote_folder_path}all_en_cumilla_corr.csv'
            self.stdout.write(f"--> Attempting Main CSV: {remote_forecast_file}")
            
            # This is often where Errno 2 happens if the file name is slightly different
            sftp.get(remote_forecast_file, temp_csv_path)
            
            df = pd.read_csv(temp_csv_path)
            df['Time'] = pd.to_datetime(df['Time']).dt.tz_localize(None)
            forecast_start_threshold = pd.to_datetime(latest_date, format='%Y%m%d')
            df = df[df['Time'] >= forecast_start_threshold].copy()
            
            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()
            time_list = df['Time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()

            # 3. Process Probability Data
            pb_dates = []
            pb_values = []
            remote_pb_filename = f'exceedence_{latest_date}_cumilla.csv'
            remote_pb_file = f'{remote_folder_path}{remote_pb_filename}'
            self.stdout.write(f"--> Attempting Probability CSV: {remote_pb_file}")

            try:
                sftp.get(remote_pb_file, temp_pb_csv_path)
                df_pb = pd.read_csv(temp_pb_csv_path)
                if 'ex_pr' in df_pb.columns:
                    pb_values = df_pb['ex_pr'].tolist()
                    if 'date' in df_pb.columns:
                        pb_dates = pd.to_datetime(df_pb['date']).dt.strftime('%Y-%m-%d').tolist()
                    else:
                        pb_dates = [d.split(' ')[0] for d in time_list[:len(pb_values)]]
            except Exception as pb_error:
                self.stdout.write(self.style.WARNING(f"--> PB File skipped: {pb_error}"))

            sftp.close()
            ssh.close()

            # 4. Save JSON
            formatted_date = datetime.strptime(latest_date, "%Y%m%d").strftime("%Y-%m-%d")
            output_data = {
                "code": "success", "message": "Data fetched!",
                "metadata": {
                    "station_id": 'SW110', "basin_name": "Gumti River (Cumilla)",
                    "forecast_date": formatted_date, "run_datetime": run_datetime,
                    "dc_unit": "m³/s", "dl": "290", "pb_unit": "%", "forecast_type": "experimental"
                },
                "data": {"date": time_list, "25%": p25, "50%": p50, "75%": p75},
                "data_pb": {"date": pb_dates, "pb": pb_values}
            }

            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated {local_json_path}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Critical Error: {str(e)}'))

        finally:
            for path in [temp_csv_path, temp_pb_csv_path]:
                if os.path.exists(path):
                    os.remove(path)