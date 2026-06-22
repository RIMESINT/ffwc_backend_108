import os
import paramiko
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Downloads UKMET deterministic forecast .nc files from remote server'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD or YYYYMMDD)')

    def handle(self, *args, **options):
        # 1. Determine Date
        date_input = options['date']
        if not date_input:
            # dt_obj = datetime.today()- timedelta(days=1)
            dt_obj = datetime.today()- timedelta(days=0)
        else:
            try:
                if "-" in date_input:
                    dt_obj = datetime.strptime(date_input, "%Y-%m-%d")
                else:
                    dt_obj = datetime.strptime(date_input, "%Y%m%d")
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {date_input}"))
                return

        # 2. Configuration
        source_host = "203.156.108.110"
        source_user = "nazmul"
        source_pass = "rootbeer77"  
        
        # Local destination
        local_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_det_data/"
        
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # Fallback list: Try target date, then yesterday
        dates_to_check = [dt_obj, dt_obj - timedelta(days=1)]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.stdout.write(f"Connecting to {source_host} for UKMET data...")
            ssh.connect(hostname=source_host, username=source_user, password=source_pass)
            sftp = ssh.open_sftp()
            
            downloaded = False
            for check_date in dates_to_check:
                date_str = check_date.strftime('%Y%m%d')
                
                # Remote Path: /home/nazmul/ukmet_det_data/ukmet_det_YYYYMMDD/precip_YYYYMMDD.nc
                remote_path = f"/home/nazmul/ukmet_det_data/ukmet_det_{date_str}/precip_{date_str}.nc"
                local_path = os.path.join(local_dir, f"precip_{date_str}.nc")

                self.stdout.write(f"Checking for: {remote_path}")

                try:
                    sftp.stat(remote_path)
                    self.stdout.write(self.style.SUCCESS(f"File found! Downloading to {local_path}..."))
                    sftp.get(remote_path, local_path)
                    self.stdout.write(self.style.SUCCESS(f"Successfully downloaded UKMET forecast for {date_str}"))
                    downloaded = True
                    break 
                except IOError:
                    self.stdout.write(self.style.WARNING(f"File not found for date {date_str}"))

            if not downloaded:
                self.stdout.write(self.style.ERROR("UKMET download failed: No files found for target or previous date."))

            sftp.close()
            ssh.close()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred during UKMET download: {str(e)}"))