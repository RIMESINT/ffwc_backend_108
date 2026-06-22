#!/usr/bin/env python3


import pylab as pl
import numpy as np
from cartopy import crs as ccrs
from cartopy.feature import ShapelyFeature
from cartopy.io.shapereader import FionaReader
from cartopy import feature as cfeature
from netCDF4 import Dataset as nco, num2date as n2d
from matplotlib.colors import LinearSegmentedColormap
import sys, os


def main(fcst_date):


    # read netcdf
    nf = nco(f'/RIMESNAS/WRF_OUT/wrf_out_{fcst_date}00.nc','r')

    plot_out_dir = f'/var/www/prod/all_api/splus/splus_plots/{fcst_date}'

    if not os.path.exists(plot_out_dir):
        os.makedirs(plot_out_dir)


    # read district variables
    district_shapefile = 'zip://bd_district.zip'
    district_boundary = ShapelyFeature( 
                            FionaReader(district_shapefile).geometries(),
                            ccrs.PlateCarree(),
                            facecolor='none',
                            edgecolor='k',
                            linewidth=1
                        )

    # get variables from nc
    lons = nf.variables['lon'][:]
    lats = nf.variables['lat'][:]
    rf = nf.variables['rainc'][:] + nf.variables['rainnc'][:]
    temp = nf.variables['t2'][:] - 273.15
    dates = n2d(nf.variables['time'][:], nf.variables['time'].units)




    # dat var
    rf7d_acc = rf[7*8,0,:,:]

    # average day_night temperature
    avg_day_temp = np.zeros(rf7d_acc.shape, dtype=np.float64)
    avg_ngt_temp = np.zeros(rf7d_acc.shape, dtype=np.float64)

    for day in range(7):
        
        day_start = day*8
        day_end = night_start = day_start+4
        night_end = night_start+4
        
        avg_day_temp += np.sum(temp[day_start:day_end+1,0,:,:],axis=0)
        avg_ngt_temp += np.sum(temp[night_start:night_end+1,0,:,:],axis=0)
        

    avg_day_temp = avg_day_temp / (7*4)
    avg_ngt_temp = avg_ngt_temp / (7*4)


    # plot 7 day accm
    rf7d_start_date  = dates[0].strftime('%Y-%m-%d 06:00 BST')
    rf7d_end_date  = dates[7*8].strftime('%Y-%m-%d 06:00 BST')

    rf7d_start_date_new = dates[0].strftime('%d-%m-%Y 06:00 BST')
    rf7d_end_date_new   = dates[7*8].strftime('%d-%m-%Y 06:00 BST')

    rf7d_start_date_new_2 = dates[0].strftime('%d-%m-%Y')
    rf7d_end_date_new_2   = dates[7*8].strftime('%d-%m-%Y')
    rf7d_end_date_new_3   = dates[6*8].strftime('%d-%m-%Y')

    #my_color = LinearSegmentedColormap.from_list('my_color', ['#D4EFDF', '#A9DFBF', '#7DCEA0', '#52BE80', '#27AE60', '#229954', '#1E8449', '#196F3D', '#145A32'], N=100)
    my_color = LinearSegmentedColormap.from_list('my_color', ['#f1f7e8', '#cfe5b5', '#a9d482', '#7fc24f', '#579835', '#366523', '#fcfd35', '#ffb811', '#ff6f3b', '#f6175e', '#b9007c', '#5b008a'], N=100)

    pl.figure(figsize=(10,10))
    ax = pl.axes(projection=ccrs.PlateCarree())
    ax.add_feature(district_boundary)
    #ax.add_feature(cfeature.BORDERS)
    #pl.contourf(lons,lats,rf7d_acc,cmap=my_color,levels=[5,10,30,50,75,100,150,200,300,400,450,500],extend='max')
    
    #Original
    pl.contourf(lons,lats,rf7d_acc,cmap=my_color,levels=[5, 20, 35, 50, 70, 90, 110, 130, 175, 200, 250, 300, 350,400],extend='max')
    #pl.contourf(lons,lats,rf7d_acc,cmap=my_color,levels=[.1, .5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10],extend='max')
    ax.set_ylim(20.5,26.8)
    ax.set_xlim(87.9,92.8)
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    pl.colorbar()
    pl.title(f'Accumulated Rainfall (mm) (WRF model)\nPeriod ({rf7d_start_date_new_2} to {rf7d_end_date_new_3})', fontsize=16)
    pl.savefig(os.path.join( plot_out_dir, 'accm_7d.png'), bbox_inches='tight', dpi=72)
    pl.close()




    # plot 7 day accm
    temp_start_date  = dates[0].strftime('%Y-%m-%d 06:00 BST')
    temp_end_date  = dates[7*8].strftime('%Y-%m-%d 06:00 BST')

    temp_start_date_new = dates[0].strftime('%d-%m-%Y 06:00 BST')
    temp_end_date_new   = dates[7*8].strftime('%d-%m-%Y 06:00 BST')

    temp_start_date_new_2 = dates[0].strftime('%d-%m-%Y')
    temp_end_date_new_2   = dates[7*8].strftime('%d-%m-%Y')
    temp_end_date_new_3   = dates[6*8].strftime('%d-%m-%Y')


    pl.figure(figsize=(10,10))
    ax = pl.axes(projection=ccrs.PlateCarree())
    ax.add_feature(district_boundary)
    #ax.add_feature(cfeature.BORDERS)
    #pl.contourf(lons,lats,avg_day_temp,cmap='plasma',levels=[5,10,15,17.5,20,22.5,25,27.5,30,32.5,35,37.5,40],extend='both')
    pl.contourf(lons,lats,avg_day_temp,cmap='jet',levels=[5,10,15,17.5,20,22.5,25,27.5,30,32.5,35,37.5,40],extend='both')
    ax.set_ylim(20.5,26.8)
    ax.set_xlim(87.9,92.8)
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    pl.colorbar()
    pl.title(f'Mean Day Temperature\nPeriod ({temp_start_date_new_2} to {temp_end_date_new_3})', fontsize=16)
    pl.savefig(os.path.join( plot_out_dir, 'tavg_day.png'), bbox_inches='tight', dpi=72)
    pl.close()


    pl.figure(figsize=(10,10))
    ax = pl.axes(projection=ccrs.PlateCarree())
    ax.add_feature(district_boundary)
    #ax.add_feature(cfeature.BORDERS)
    pl.contourf(lons,lats,avg_ngt_temp,cmap='jet',levels=[5,10,15,17.5,20,22.5,25,27.5,30,32.5,35,37.5,40],extend='both')
    ax.set_ylim(20.5,26.8)
    ax.set_xlim(87.9,92.8)
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    pl.colorbar()
    pl.title(f'Mean Night Temperature\nPeriod {temp_start_date_new_2} to {temp_end_date_new_3})', fontsize=16)
    pl.savefig( os.path.join( plot_out_dir, 'tavg_night.png'), bbox_inches='tight', dpi=72)
    pl.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('provide date of data in yyyymmdd fromat')
        sys.exit(100)
    
    main(sys.argv[1])
