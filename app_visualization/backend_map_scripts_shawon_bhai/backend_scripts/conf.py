import os
# from django.conf import settings
# from ffwc_django_project.settings import BASE_DIR
# from django.conf.settings import BASE_DIR

#########################
# [paths for BMDWRF]
#########################
# BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# BASE_DIR     = settings.BASE_DIR
# JSON_OUT_LOC = os.path.join(BASE_DIR,'media/assets/forecast_map')
JSON_OUT_LOC = "/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/"+'media/assets/bmd_wrf/forecast_map/'
# WRF_NC_LOC   = '/RIMESNAS/WRF_OUT/'
WRF_NC_LOC   = "/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/bmd_wrf/"

#########################
# [paths for BMDWRF]
######################### 
JSON_OUT_LOC_ECMWF_HRES = "/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/"+'media/assets/ecmwrf_hres/forecast_map/'
# WRF_NC_LOC   = '/RIMESNAS/WRF_OUT/'
WRF_NC_LOC_ECMWF_HRES   = "/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/ecmwrf_hres/"
# WRF_NC_LOC_ECMWF_HRES   = "/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/ecmwrf_hres/%d%m%Y.nc"
# "/media/shaif/RIMES/SHAIF/Official_Project/FFWC/FFWC_Flash_Flood_Guidance/ffwc_flash_flood_guidence/forecast/ecmwf_hres/"

# [database]
db_host = '127.0.0.1'
db_name = 'undp'
db_user = 'rimes'
db_pass = 'rimesr230@#$%'

