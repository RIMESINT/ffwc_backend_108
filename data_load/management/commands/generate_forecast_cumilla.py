import os
import json
import pandas as pd
import paramiko
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Fetch latest forecast and overwrite the single latest JSON file'

    def add_arguments(self, parser):
        # Optional: You can still pass a date to fetch a specific past folder, 
        # but it will still overwrite the "latest" file.
        parser.add_argument('--date', type=str, help='Target date folder (YYYYMMDD)')

    def handle(self, *args, **options):
        # 1. Setup
        target_date = options['date'] if options['date'] else datetime.now().strftime('%Y%m%d')
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        REMOTE_HOST = '203.156.108.111'
        REMOTE_USER = 'mmb'
        REMOTE_PASS = 'mmb!@#$'


        remote_path = f'/home/mmb/tank-cumilla-auto/output_corrected/csv/{target_date}/all_en_corr_cumilla.csv'
        
        # Single file path (Static name)
        base_assets = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/assets/flood-monitor-basin-forecast'
        os.makedirs(base_assets, exist_ok=True)
        local_json_path = os.path.join(base_assets, 'latest_cumilla_forecast.json')

        try:
            # 2. SFTP Transfer
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS)
            
            sftp = ssh.open_sftp()
            temp_csv = f'/tmp/latest_cumilla_temp.csv'
            self.stdout.write(f"Fetching data from folder {target_date}...")
            sftp.get(remote_path, temp_csv)
            sftp.close()
            ssh.close()

            # 3. Processing
            df = pd.read_csv(temp_csv)
            df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            ensemble_cols = [col for col in df.columns if col.startswith('EN#')]
            
            p25 = df[ensemble_cols].quantile(0.25, axis=1).round(3).tolist()
            p50 = df[ensemble_cols].quantile(0.50, axis=1).round(3).tolist()
            p75 = df[ensemble_cols].quantile(0.75, axis=1).round(3).tolist()

            output_data = {

                "metadata": {
                    "station_id": 'SW110',
                    "basin_name": "Gumti River (Cumilla)",
                    "forecast_date": target_date,
                    "run_datetime": run_datetime,
                    "dc_unit": "m",
                    "pb_unit": "%"
                },
                "data": {
                    "date": df['Time'].tolist(),
                    "min": p25,
                    "mean": p50,
                    "max": p75
                }
            }

            # 4. Overwrite existing file
            with open(local_json_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            self.stdout.write(self.style.SUCCESS('Successfully updated latest_cumilla_forecast.json'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
