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


def main(fcst_date):
    # print("########### fcst_date: ", fcst_date)

    # read netcdf
    # nf = Dataset(f'/RIMESNAS/ECMWF_HRES/{fcst_date}.nc','r')
    # nf = nco(f'/RIMESNAS/WRF_OUT/wrf_out_{fcst_date}00.nc','r')
    nf = Dataset(f'/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/data/nas/ecmwf/{fcst_date}.nc','r')

    # plot_out_dir = f'/var/www/prod/all_api/splus/splus_plots/{fcst_date}'
    # plot_out_dir = f'/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/media/assets/bulletin/agromet_bulletin/{fcst_date}'
    plot_out_dir = f'/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/media/assets/bulletin/agromet_bulletin/{fcst_date}'


    # create path if path doesnot exist
    if not os.path.exists(plot_out_dir):
        os.makedirs(plot_out_dir)


    lat = nf.variables['latitude'][:]
    lon = nf.variables['longitude'][:]
    time = num2date(nf.variables['time'][:], nf.variables['time'].units)

    pr =  (nf.variables['cp'][:] +  nf.variables['lsp'][:] ) * 1000
    t2 =  nf.variables['t2m'][:] - 273.15


    pr_1_5_day = pr[20, :, :]
    pr_6_10_day = pr[-1, :, :] - pr_1_5_day


    tmax_1_5_day = np.amax( t2[:21], axis=0 )
    tmax_6_10_day = np.amax( t2[21:], axis=0 )

    tmin_1_5_day = np.amin( t2[:21], axis=0 )
    tmin_6_10_day = np.amin( t2[21:], axis=0 )


    lat_m = (lat >= 22) & (lat <= 38)
    lon_m = (lon>=60) & (lon<=79)
    # print("lat_m: ", lat[lat_m])
    # print("lon_m: ", lon[lon_m])
    m2d= np.ix_(lat_m, lon_m)
    # print("m2d: ", m2d)
    # print("shape: ", m2d.shape())


    # read district variables
    district_shapefile = '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/data/pak_shape/geojson/pak_adm3.json'
    district_boundary = ShapelyFeature( 
        FionaReader(district_shapefile).geometries(),
        ccrs.PlateCarree(),
        facecolor='none',
        edgecolor='k',
        linewidth=0.4
    )


    #########################################################################
    ### Day 1 to 5 accumulated rainfall
    #########################################################################
    fig = plt.figure(dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())
    # ax = plt.axes(projection=ccrs.Mercator())
    ax.add_feature(district_boundary)
    plt.contourf(lon[lon_m],lat[lat_m], pr_1_5_day[m2d])
    plt.colorbar()
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    plt.title(f'Extended Outlook for Accumulated Rainfall (mm)\nPeriod (day 1 to day 5)', fontsize=16) 
    plt.savefig(os.path.join(plot_out_dir, 'accum_rf_1st_5d.png'), bbox_inches='tight', dpi=300)
    plt.close()


    #########################################################################
    ### Day 6 to 10 accumulated rainfall
    #########################################################################
    fig = plt.figure(dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())
    # ax = plt.axes(projection=ccrs.Mercator())
    ax.add_feature(district_boundary)
    plt.contourf(lon[lon_m],lat[lat_m], pr_6_10_day[m2d])
    plt.colorbar()
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    plt.title(f'Extended Outlook for Accumulated Rainfall (mm)\nPeriod (day 1 to day 5)', fontsize=16) 
    plt.savefig(os.path.join(plot_out_dir, 'accum_rf_2nd_5d.png'), bbox_inches='tight', dpi=300)
    plt.close()


    #########################################################################
    ### Day 1 to 5 max temperature
    #########################################################################
    fig = plt.figure(dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())
    # ax = plt.axes(projection=ccrs.Mercator())
    ax.add_feature(district_boundary)
    plt.contourf(lon[lon_m],lat[lat_m], tmax_1_5_day[m2d])
    plt.colorbar()
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    plt.title(f'Extended Outlook for Maximum Temperature (°C)\nPeriod (day 1 to day 5)', fontsize=16) 
    plt.savefig(os.path.join(plot_out_dir, 'max_temp_1st_5d.png'), bbox_inches='tight', dpi=300)
    plt.close()


    #########################################################################
    ### Day 6 to 10 max temperature
    #########################################################################
    fig = plt.figure(dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())
    # ax = plt.axes(projection=ccrs.Mercator())
    ax.add_feature(district_boundary)
    plt.contourf(lon[lon_m],lat[lat_m], tmax_6_10_day[m2d])
    plt.colorbar()
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    plt.title(f'Extended Outlook for Maximum Temperature (°C)\nPeriod (day 6 to day 10)', fontsize=16) 
    plt.savefig(os.path.join(plot_out_dir, 'max_temp_2nd_5d.png'), bbox_inches='tight', dpi=300)
    plt.close()


    #########################################################################
    ### Day 1 to 5 min temperature
    #########################################################################
    fig = plt.figure(dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())
    # ax = plt.axes(projection=ccrs.Mercator())
    ax.add_feature(district_boundary)
    plt.contourf(lon[lon_m],lat[lat_m], tmin_1_5_day[m2d])
    plt.colorbar()
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    plt.title(f'Extended Outlook for Minimum Temperature (°C)\nPeriod (day 1 to day 5)', fontsize=16) 
    plt.savefig(os.path.join(plot_out_dir, 'min_temp_1st_5d.png'), bbox_inches='tight', dpi=300)
    plt.close()


    #########################################################################
    ### Day 6 to 10 min temperature
    #########################################################################
    fig = plt.figure(dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())
    # ax = plt.axes(projection=ccrs.Mercator())
    ax.add_feature(district_boundary)
    plt.contourf(lon[lon_m],lat[lat_m], tmin_6_10_day[m2d])
    plt.colorbar()
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    plt.title(f'Extended Outlook for Minimum Temperature (°C)\nPeriod (day 6 to day 10)', fontsize=16) 
    plt.savefig(os.path.join(plot_out_dir, 'min_temp_2nd_5d.png'), bbox_inches='tight', dpi=300)
    plt.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('provide date of data in ddmmyyyy fromat')
        sys.exit(100)
    
    main(sys.argv[1])
