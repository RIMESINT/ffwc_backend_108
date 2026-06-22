"""
    ######################################################################################
    ### REGION AND COUNTRY WISE --- ECMWF OPEN DATA DOWNLOAD SCRIPT
    ######################################################################################
    ### SOURCE REGION: https://open-data.rimes.int/Regional/rimes/ECMWF/ifs15/
    ### SOURCE COUNTRY: https://open-data.rimes.int/Regional/rimes/ECMWF/ifs15/
    ### DATA FORMAT: netCDF
    ### FREQUENCY: DAILY
    ### VARIABLES: "10v.nc", "10u.nc", "2t.nc", "2d.nc", "tp.nc", "w.nc", "ssr.nc", "v.nc", "u.nc",
    ### LEAD TIME: 14 days
    ### RESOLUTION: 0.1 degree
    ######################################################################################

"""



import os
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime as dt, timedelta as delt
from tqdm import tqdm  # Import tqdm for progress bars

ECMWF_BASE_URL = settings.BASE_DIR
from ffwc_django_project.project_constant import (app_visualization)

from app_visualization.models import (
    Source, SystemState
)
# from user_authentication.models import (
#     GeoData, GeoLevel
# )


# COUNTRY_OBJ = GeoData.objects.filter(
#     id=19,
# )[0]
COUNTRY_OBJ_country_short_name = app_visualization["bd_details"]["SHORT_NAME"]
print(" *********** COUNTRY:", COUNTRY_OBJ_country_short_name)
# print(" *********** COUNTRY Short name:", COUNTRY_OBJ.country_short_name)
# print(" *********** COUNTRY LAT max:", COUNTRY_OBJ.lat_json["max"])
# print(" *********** COUNTRY LAT min:", COUNTRY_OBJ.lat_json["min"])
# print(" *********** COUNTRY LON max:", COUNTRY_OBJ.lon_json["max"])
# print(" *********** COUNTRY LON min:", COUNTRY_OBJ.lon_json["min"])






class Command(BaseCommand):
    help = "Downloads ECMWF weather data files for the current date"

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')


    def handle(self, *args, **options): 
        current_date = options['fdate']
        if current_date is None:
            today_date = dt.now() 
            formatted_date = today_date.strftime('%Y%m%d')
            print("formatted_date: ", formatted_date)
            current_date = formatted_date
        
        source_obj = Source.objects.filter(
			name="ECMWF_HRES_VIS",
			source_type="vis"
		)[0]
        
        download_output_dir = str(ECMWF_BASE_URL) + f"{source_obj.source_path}" + f"{current_date}/"
        is_successful = self.download_data_from_rimes_open_data(
            output_dir = download_output_dir, 
            current_date = current_date,
        )
        print(" $$$$$$$$$$$$$$$$$$ Download completed successfully Flag:", is_successful)
    
    
    def download_data_from_rimes_open_data(self, output_dir, current_date):
        is_successful = True
        
        base_url = f"https://open-data.rimes.int/Regional/rimes/ECMWF/ifs15/{current_date}/"
        # if COUNTRY_OBJ_country_short_name is not None:
        #     base_url = f"https://open-data.rimes.int/Countries/{COUNTRY_OBJ_country_short_name}/ECMWF/ifs15/{current_date}/"
        print(" $$$$$$$$$$$$$$ BASE URL:", base_url)
        os.makedirs(output_dir, exist_ok=True)
        
        files = [
            # "10v.nc", "10u.nc", "2t.nc", "2d.nc", 
            "tp.nc",
            # "w.nc", 
            # "ssr.nc", "v.nc", "u.nc",
        ]
        
        self.stdout.write(f"Downloading files to: {output_dir}")

        for file in files:
            url = base_url + file
            file_path = os.path.join(output_dir, file)
            
            try:
                # Initialize download with streaming
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # Get file size for progress tracking
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192  # 8KB chunks
                
                # Initialize progress bar
                progress_bar = tqdm(
                    desc=f"Downloading {file}",
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    leave=False  # Clears progress bar after completion
                )
                
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(block_size):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            progress_bar.update(len(chunk))
                
                # Finalize progress bar and show success
                progress_bar.close()
                self.stdout.write(self.style.SUCCESS(f"✓ Downloaded {file}"))
                
            except requests.exceptions.HTTPError as e:
                is_successful = False
                self.stderr.write(self.style.ERROR(f"HTTP error for {file}: {e}"))
            except requests.exceptions.RequestException as e:
                is_successful = False
                self.stderr.write(self.style.ERROR(f"Failed to download {file}: {e}"))
            finally:
                # Ensure progress bar is closed if exception occurs
                if 'progress_bar' in locals():
                    progress_bar.close()
                    
        return is_successful