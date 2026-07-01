import os
import paramiko
import re
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Downloads ECMWF Ensemble folder with argument processing and step-down fallbacks'

    def add_arguments(self, parser):
        # 1. Positional argument support for manual CLI/cron executions
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast folder in format YYYYMMDD or YYYY-MM-DD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        # 1. Setup Configuration
        source_host = "203.156.108.110"
        source_user = "nazmul"
        source_pass = "rootbeer77"
        
        remote_root = "/home/nazmul/ifs_6h/ifs_processed/"
        local_root = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_ens_data/"

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

        # 3. Define Fallback Chronological Folders Search Sequence (Target Date, then Day Before)
        yesterday_fallback = target_date - timedelta(days=1)
        folders_to_check = [
            target_date.strftime("%Y%m%d"), 
            yesterday_fallback.strftime("%Y%m%d")
        ]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.stdout.write(f"Connecting to {source_host}...")
            ssh.connect(hostname=source_host, username=source_user, password=source_pass, timeout=15)
            sftp = ssh.open_sftp()
            
            success = False

            for date_folder in folders_to_check:
                remote_dir = os.path.join(remote_root, date_folder)
                local_dir = os.path.join(local_root, date_folder)

                self.stdout.write(f"Checking remote folder: {remote_dir}")

                try:
                    # Verify if folder exists on remote
                    remote_files = sftp.listdir(remote_dir)
                    
                    if not remote_files:
                        self.stdout.write(self.style.WARNING(f"Folder {date_folder} is empty on remote server."))
                        continue

                    # Create local folder if it doesn't exist
                    if not os.path.exists(local_dir):
                        os.makedirs(local_dir)
                        self.stdout.write(f"Created local directory: {local_dir}")

                    self.stdout.write(self.style.SUCCESS(f"Found {len(remote_files)} files. Starting download..."))

                    # Download each file
                    for filename in remote_files:
                        remote_file_path = os.path.join(remote_dir, filename)
                        local_file_path = os.path.join(local_dir, filename)

                        if os.path.exists(local_file_path):
                            self.stdout.write(f"  - {filename} already exists locally. Skipping.")
                            continue

                        self.stdout.write(f"  - Downloading {filename}...")
                        sftp.get(remote_file_path, local_file_path)

                    self.stdout.write(self.style.SUCCESS(f"Successfully synced folder {date_folder}"))
                    success = True
                    break # Stop looping if we successfully found and downloaded data files

                except (FileNotFoundError, IOError):
                    self.stdout.write(self.style.WARNING(f"Folder {date_folder} not found on remote server. Stepping down to fallback candidate..."))

            if not success:
                self.stdout.write(self.style.ERROR("No ensemble data found for the checked dates."))

            sftp.close()
            ssh.close()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Connection error during secure directory synchronization: {str(e)}"))