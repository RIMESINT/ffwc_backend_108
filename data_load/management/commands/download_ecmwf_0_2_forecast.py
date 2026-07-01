import os
import paramiko
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Checks and downloads ecmwf 0.2 .nc file with argument overrides and fallback logic'

    def add_arguments(self, parser):
        # 1. Positional argument support for manual CLI/cron executions
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD or YYYY-MM-DD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        # 1. Setup Configuration
        source_host = "203.156.108.110"
        source_user = "nazmul"
        source_pass = "rootbeer77"
        source_dir = "/home/nazmul/ffwc/hres_diana/backup/"
        local_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/"

        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # 2. Intercept and Normalize Incoming Target Date
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if raw_date:
            clean_date_str = raw_date.replace('-', '')
            try:
                target_date = datetime.strptime(clean_date_str, "%Y%m%d")
                self.stdout.write(self.style.SUCCESS(f"Target date initialized: {target_date.strftime('%Y-%m-%d')}"))
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format received ({raw_date}). Defaulting to current system time."))
                target_date = datetime.now()
        else:
            target_date = datetime.now()
            self.stdout.write(self.style.NOTICE(f"No date provided. Defaulting to system time: {target_date.strftime('%Y-%m-%d')}"))

        # 3. Define Fallback Chronological Search Sequence (Target Date, then Day Before)
        yesterday_fallback = target_date - timedelta(days=1)
        dates_to_check = [
            target_date.strftime("%d%m%Y"), 
            yesterday_fallback.strftime("%d%m%Y")
        ]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.stdout.write(f"Connecting to {source_host}...")
            ssh.connect(hostname=source_host, username=source_user, password=source_pass, timeout=10)
            sftp = ssh.open_sftp()
            
            downloaded = False

            for date_str in dates_to_check:
                filename = f"{date_str}.nc"
                remote_path = os.path.join(source_dir, filename)
                local_path = os.path.join(local_dir, filename)

                # Check if file already exists locally to save bandwidth
                if os.path.exists(local_path):
                    self.stdout.write(f"File {filename} already exists locally. Skipping.")
                    downloaded = True
                    break

                self.stdout.write(f"Checking remote for {filename}...")

                try:
                    sftp.stat(remote_path)
                    self.stdout.write(self.style.SUCCESS(f"File found on remote. Downloading to {local_path}..."))
                    sftp.get(remote_path, local_path)
                    self.stdout.write(self.style.SUCCESS(f"Successfully downloaded {filename}"))
                    downloaded = True
                    break 
                
                except FileNotFoundError:
                    self.stdout.write(self.style.WARNING(f"File {filename} not found on remote server."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to download {filename}: {str(e)}"))

            if not downloaded:
                self.stdout.write(self.style.ERROR("No data found for the checked dates."))

            sftp.close()
            ssh.close()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Connection error: {str(e)}"))