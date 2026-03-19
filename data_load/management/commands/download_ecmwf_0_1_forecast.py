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
        source_dir = "/home/nazmul/ffwc/hres_diana/"
        local_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ecmwf_0_1/"

        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # 2. Define dates to check (Today, then Yesterday)
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
            ssh.connect(hostname=source_host, username=source_user, password=source_pass)
            sftp = ssh.open_sftp()
            
            downloaded = False

            for date_str in dates_to_check:
                filename = f"{date_str}.nc"
                remote_path = os.path.join(source_dir, filename)
                local_path = os.path.join(local_dir, filename)

                self.stdout.write(f"Checking for {filename}...")

                try:
                    sftp.stat(remote_path)
                    # If stat doesn't error, the file exists
                    self.stdout.write(self.style.SUCCESS(f"File {filename} found. Starting download..."))
                    sftp.get(remote_path, local_path)
                    self.stdout.write(self.style.SUCCESS(f"Successfully downloaded {filename}"))
                    downloaded = True
                    break  # Exit the loop once a file is found and downloaded
                
                except IOError:
                    self.stdout.write(self.style.WARNING(f"File {filename} not found."))

            if not downloaded:
                self.stdout.write(self.style.ERROR("No data found for today or yesterday."))

            sftp.close()
            ssh.close()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {str(e)}"))