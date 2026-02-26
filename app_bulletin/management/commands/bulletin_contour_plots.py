#!/usr/bin/env python3
'''
Generate JSON data for ECMWF HERS forecast

- Temporal Reduction : Daily 
- Stream Name        : R1Dxxx
- Lead Time          : 10 Day 

''' 
import json
import numpy as np
from django.db.models.expressions import F


from django.core.management.base  import BaseCommand, CommandError
from datetime import date, datetime as dt, timedelta as delt 
# from datetime import date as py_date_obj, timedelta as delt 
from  yaspin import yaspin
import datetime as dt_convert


#!/usr/bin/env python3


import os
import sys

from netCDF4 import Dataset, num2date

import numpy as np
import pylab as plt
# import matplotlib.pyplot as plt
from cartopy import crs as ccrs
from cartopy import feature as cfeature

from cartopy.feature import ShapelyFeature
from cartopy.io.shapereader import FionaReader


from app_bulletin.models import (
	AgrometBulletinSourceDestinationDetails,
    AgrometBulletin
)
from app_weather_api.models import (
    FileDynamicUniqueCodeSetup
)

#  import project constant
from ffwc_django_project.project_constant import GEO_DATA, GEO_LEVELS, APP_WEATHER_API

# import settings
from ffwc_django_project.settings_local import BASE_DIR, MEDIA_URL

# GLOBAL VARIABLE
BD_GEO_DATA = GEO_DATA["Bangladesh"]
BD_GEO_LEVEL = GEO_LEVELS["BD"]
MGT_COMMAND = APP_WEATHER_API["management_command"]
MGT_SOURCE = APP_WEATHER_API["source"]


print(" #################################################################")
print(" ########## bulletin_contour_plots ############################")
print(" #################################################################")
###################################################################
### PRINT CURRENT DATE TIME
###################################################################
curr_date_time = dt.now()
curr_date_time_str = curr_date_time.strftime("%d-%m-%Y %H:%M:%S")
print(" ########################## ", curr_date_time_str, " ##############")









class Command(BaseCommand):

    help="generate bulletin map plotting"

    # SOURCE_PATH = f + AgrometBulletinSourceDestinationDetails.objects.all()[0].source_path 

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Date for forecast data in format YYYYMMDD')
		# pass
        # parser.add_argument('date', type=str, help="forecast date in yyyymmdd format")


    def handle(self,*args,**kwargs):
        fcst_date = kwargs['fdate']

        if fcst_date is None:
            today_date = dt.now()
            # formatted_date = today_date.strftime('%Y%m%d')  # Date format = YYYYMMDD
            formatted_date = today_date.strftime("%d%m%Y")  # Date format = DDMMYYYY
            print("formatted_date: ", formatted_date)
            fcst_date = formatted_date

        # try:        
        with yaspin() as ysp:
            ysp.text = "Processing Bulletin Maps. "
            # fcst_date = '20230516'
            self.gen_contourf_plot(fcst_date)
        # except Exception as e:
        #     print(e)        
        

    def gen_contourf_plot(self, fcst_date:dt): 

        # print("########### fcst_date: ", fcst_date)
        ambsd_qs = AgrometBulletinSourceDestinationDetails.objects.all()
        # print("ambsd_qs: ", ambsd_qs)
        # print("ambsd_qs len: ", len(ambsd_qs))
        
        
        for ambsd in ambsd_qs:
            contour_plot_path = {}

            # SOURCE_PATH = AgrometBulletinSourceDestinationDetails.objects.all()[0].source_path+'/'+fcst_date+'.nc'
            SOURCE_PATH = ambsd.source_path+fcst_date+'.nc'
            # print("########### SOURCE_PATH: ", SOURCE_PATH)
            
            # DEST_PATH = AgrometBulletinSourceDestinationDetails.objects.all()[0].destination_path+'/'+fcst_date
            DEST_PATH = str(BASE_DIR)+str(MEDIA_URL)+ambsd.destination_path+fcst_date+'/'+str(ambsd.country.unique_value)
            # print("########### DEST_PATH: ", DEST_PATH)

            # read netcdf
            # nf = Dataset(f'/RIMESNAS/ECMWF_HRES/{fcst_date}.nc','r')
            # nf = nco(f'/RIMESNAS/WRF_OUT/wrf_out_{fcst_date}00.nc','r')
            # nf = Dataset(f'/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/data/nas/ecmwf/{fcst_date}.nc','r')
            nf = Dataset(SOURCE_PATH,'r')

            # plot_out_dir = f'/var/www/prod/all_api/splus/splus_plots/{fcst_date}'
            # plot_out_dir = f'/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/media/assets/bulletin/agromet_bulletin/{fcst_date}'
            # plot_out_dir = f'/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/media/assets/bulletin/agromet_bulletin/{fcst_date}'
            plot_out_dir = DEST_PATH

            # create path if path doesnot exist
            if not os.path.exists(plot_out_dir):
                os.makedirs(plot_out_dir)

            
            # read district variables
            # district_shapefile = '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/data/pak_shape/geojson/pak_adm3.json'
            shapefile_path = FileDynamicUniqueCodeSetup.objects.filter(
                country=ambsd.country.id
            ).order_by('level')[0]
            district_shapefile = str(BASE_DIR)+str(MEDIA_URL)+str(shapefile_path.shape_file)
            # print("############# district_shapefile : ", district_shapefile)
            district_boundary = ShapelyFeature( 
                FionaReader(district_shapefile).geometries(),
                ccrs.PlateCarree(),
                facecolor='none',
                edgecolor='k',
                linewidth=0.4
            )

            lat = nf.variables['latitude'][:]
            lon = nf.variables['longitude'][:]
            time = num2date(nf.variables['time'][:], nf.variables['time'].units)

            pr =  (nf.variables['cp'][:] +  nf.variables['lsp'][:] ) * 1000
            t2 =  nf.variables['t2m'][:] - 273.15


            pr_1_7_day = pr[28, :, :]
            # pr_1_5_day = pr[20, :, :]
            # pr_6_10_day = pr[-1, :, :] - pr_1_5_day


            tmax_1_7_day = np.amax( t2[:29], axis=0 )
            # tmax_1_5_day = np.amax( t2[:21], axis=0 )
            # tmax_6_10_day = np.amax( t2[21:], axis=0 )

            tmin_1_7_day = np.amin( t2[:29], axis=0 )
            # tmin_1_5_day = np.amin( t2[:21], axis=0 )
            # tmin_6_10_day = np.amin( t2[21:], axis=0 )


            # SET MAX and MIN of LAT and LON Value
            # lat_m = (lat >= 22) & (lat <= 38)
            # lon_m = (lon>=60) & (lon<=79) 
            lat_m = (lat >= ambsd.country.lat_json['min']) & (lat <= ambsd.country.lat_json['max'])
            lon_m = (lon>=ambsd.country.lon_json['min']) & (lon<=ambsd.country.lon_json['max'])
            # print("lat_m: ", lat[lat_m])
            # print("lon_m: ", lon[lon_m])
            m2d= np.ix_(lat_m, lon_m)
            # print("m2d: ", m2d)
            # print("shape: ", m2d.shape())


            #########################################################################
            ### Day 1 to 5 accumulated rainfall
            #########################################################################
            fig = plt.figure(dpi=300)
            ax = plt.axes(projection=ccrs.PlateCarree())
            # ax = plt.axes(projection=ccrs.Mercator())
            ax.add_feature(district_boundary)
            plt.contourf(
                lon[lon_m],lat[lat_m], pr_1_7_day[m2d], 
                levels=[5,10,20,40,60,80,100,150,200,250,300,400,500],
                extend='max', cmap='Spectral_r')
            # plt.contourf(lon[lon_m],lat[lat_m], pr_1_5_day[m2d])
            plt.colorbar()
            gl = ax.gridlines(draw_labels=True)
            gl.top_labels=False
            gl.right_labels=False
            plt.title(f'Extended Outlook for Accumulated Rainfall (mm)\nPeriod (day 1 to day 7)', fontsize=16) 
            plt.savefig(os.path.join(plot_out_dir, 'accum_rf_1st_7d.png'), bbox_inches='tight', dpi=300)
            # contour_plot_path['accum_rf_1st_5d'] = os.path.join(plot_out_dir, 'accum_rf_1st_5d.png')
            contour_plot_path['accum_rf_1st_7d'] = os.path.join(str(MEDIA_URL)+ambsd.destination_path+fcst_date+'/'+str(ambsd.country.unique_value), 'accum_rf_1st_7d.png')
            plt.close()


            # #########################################################################
            # ### Day 6 to 10 accumulated rainfall
            # #########################################################################
            # fig = plt.figure(dpi=300)
            # ax = plt.axes(projection=ccrs.PlateCarree())
            # # ax = plt.axes(projection=ccrs.Mercator())
            # ax.add_feature(district_boundary)
            # plt.contourf(lon[lon_m],lat[lat_m], pr_6_10_day[m2d])
            # plt.colorbar()
            # gl = ax.gridlines(draw_labels=True)
            # gl.top_labels=False
            # gl.right_labels=False
            # plt.title(f'Extended Outlook for Accumulated Rainfall (mm)\nPeriod (day 1 to day 5)', fontsize=16) 
            # plt.savefig(os.path.join(plot_out_dir, 'accum_rf_2nd_5d.png'), bbox_inches='tight', dpi=300)
            # # contour_plot_path['accum_rf_2nd_5d'] = os.path.join(plot_out_dir, 'accum_rf_2nd_5d.png')
            # contour_plot_path['accum_rf_2nd_5d'] = os.path.join(str(MEDIA_URL)+ambsd.destination_path+fcst_date+'/'+str(ambsd.country.unique_value), 'accum_rf_2nd_5d.png')
            # plt.close()


            
            
        print(" ********** Processing Bulletin Map Completed ********** ")

