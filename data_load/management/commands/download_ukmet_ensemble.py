import os
import paramiko
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Downloads UKMET ensemble forecast files (EN00-EN17) from remote server'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD or YYYYMMDD)')

    def handle(self, *args, **options):
        # 1. Determine Date
        date_input = options['date']
        if not date_input:
            dt_obj = datetime.today() - timedelta(days=0)
        else:
            try:
                if "-" in date_input:
                    dt_obj = datetime.strptime(date_input, "%Y-%m-%d")
                else:
                    dt_obj = datetime.strptime(date_input, "%Y%m%d")
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {date_input}"))
                return

        # 
        source_host = "203.156.108.110"
        source_user = "nazmul"
        source_pass = "rootbeer77"  
        
        # Local destination
        local_base_dir = "/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/ukmet_ens_data/"
        
        # Try target date, then fallback to yesterday
        dates_to_check = [dt_obj, dt_obj - timedelta(days=1)]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.stdout.write(f"Connecting to {source_host} for UKMET Ensemble data...")
            ssh.connect(hostname=source_host, username=source_user, password=source_pass)
            sftp = ssh.open_sftp()
            
            download_triggered = False
            
            for check_date in dates_to_check:
                date_str = check_date.strftime('%Y%m%d')
                remote_folder = f"/home/nazmul/ukmet_ens_data/ukmet_ens_{date_str}/"
                
                # Check if the directory exists on the remote server
                try:
                    sftp.chdir(remote_folder)
                    self.stdout.write(self.style.SUCCESS(f"Found remote folder: {remote_folder}"))
                except IOError:
                    self.stdout.write(self.style.WARNING(f"Remote folder not found: {remote_folder}"))
                    continue

                # Prepare local directory for this specific date
                local_date_dir = os.path.join(local_base_dir, f"ukmet_ens_{date_str}")
                if not os.path.exists(local_date_dir):
                    os.makedirs(local_date_dir)

                # Download files EN00 to EN17 (18 files total)
                files_downloaded_count = 0
                for i in range(18):
                    ens_member = f"EN{str(i).zfill(2)}" # EN00, EN01, etc.
                    filename = f"precip_{ens_member}.nc"
                    remote_path = os.path.join(remote_folder, filename)
                    local_path = os.path.join(local_date_dir, filename)

                    try:
                        sftp.stat(remote_path)
                        sftp.get(remote_path, local_path)
                        files_downloaded_count += 1
                    except IOError:
                        self.stdout.write(self.style.WARNING(f"  File {filename} missing in {remote_folder}"))

                if files_downloaded_count > 0:
                    self.stdout.write(self.style.SUCCESS(f"Successfully downloaded {files_downloaded_count} files for {date_str}"))
                    download_triggered = True
                    break # Stop looking for yesterday's data if today's was found

            if not download_triggered:
                self.stdout.write(self.style.ERROR("Ensemble download failed: No folders found for target or previous date."))

            sftp.close()
            ssh.close()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {str(e)}"))