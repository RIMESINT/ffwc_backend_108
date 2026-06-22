import os
import paramiko
import re
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Downloads ECMWF Ensemble folder (tries today, then yesterday)'

    def handle(self, *args, **options):
        # 1. Setup Configuration
        source_host = "203.156.108.110"
        source_user = "nazmul"
        source_pass = "rootbeer77"
        
        # Remote path: /home/nazmul/ifs_6h/ifs_processed/YYYYMMDD
        remote_root = "/home/nazmul/ifs_6h/ifs_processed/"
        local_root = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_ens_data/"

        # 2. Define dates to check (Today, then Yesterday)
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # Format folders as YYYYMMDD based on your path example /20260401
        folders_to_check = [
            today.strftime("%Y%m%d"), 
            yesterday.strftime("%Y%m%d")
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
                        self.stdout.write(self.style.WARNING(f"Folder {date_folder} is empty on remote."))
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
                            self.stdout.write(f"  - {filename} already exists. Skipping.")
                            continue

                        self.stdout.write(f"  - Downloading {filename}...")
                        sftp.get(remote_file_path, local_file_path)

                    self.stdout.write(self.style.SUCCESS(f"Successfully synced folder {date_folder}"))
                    success = True
                    break # Stop if we found and processed a folder

                except (FileNotFoundError, IOError):
                    self.stdout.write(self.style.WARNING(f"Folder {date_folder} not found on remote server."))

            if not success:
                self.stdout.write(self.style.ERROR("No ensemble data found for the checked dates."))

            sftp.close()
            ssh.close()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Connection error: {str(e)}"))