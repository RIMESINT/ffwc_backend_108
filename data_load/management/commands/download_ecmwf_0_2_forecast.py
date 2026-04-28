import os
import paramiko
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Checks and downloads ecmwf .nc file (tries today, then yesterday)'

    def handle(self, *args, **options):
        # 1. Setup Configuration
        source_host = "203.156.108.110"
        source_user = "nazmul"
        source_pass = "rootbeer77"
        # source_dir = "/home/nazmul/ffwc/hres_diana/backup/"
        source_dir = "/home/nazmul/ffwc/hres_diana/backup/
        # ec_atmos_20260428_00.nc
        local_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_2/"

        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # 2. Define dates to check (Today, then Yesterday)
        # Note: Today is 26-03-2026
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        dates_to_check = [
            today.strftime("%d%m%Y"), 
            yesterday.strftime("%d%m%Y")
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
                    # Check if file exists on remote
                    sftp.stat(remote_path)
                    self.stdout.write(self.style.SUCCESS(f"File found on remote. Downloading to {local_path}..."))
                    
                    # Perform the actual download
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