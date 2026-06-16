import pandas as pd
import numpy as np
import seaborn as sbn
import geopandas

import matplotlib.pyplot as plt
import matplotlib as mlp
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Path, PathPatch

import glob
from pyscissor import scissor
import fiona
import time
import sys,os


import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.feature import ShapelyFeature
import cartopy.io.shapereader as shpreader


from shapely.geometry import Polygon
from shapely.geometry import shape
import shapely.vectorized


from pykrige.ok import OrdinaryKriging
from pykrige.kriging_tools import write_asc_grid
import pykrige.kriging_tools as kt

import requests
from datetime import datetime


def importData(date):
    
    temperatureDF=pd.read_csv(
        f"https://api.all.bdservers.site/bmd_observed_data/get_data_by_date.php?gen_date={date}&type=1"
    )
    
    temperatureDF['meanTemperature'] = temperatureDF[['temp_max', 'temp_min']].mean(axis=1)
    d=temperatureDF['date_time'].unique()[0]
    
    d=datetime.strptime(d,'%Y-%m-%d %H:%M:%S')
    #startDate_old=d.strftime('%d-%m-%Y %H:%M:%S')
    startDate=d.strftime('%d-%m-%Y')
    
    temperatureDF.drop(columns=['date_time','temp_max','temp_min'],inplace=True)
    temperatureDF.rename(
    columns={
        'st_code':'stationID',
        'st_name':'stationName',
        'lat':'Lat','lon':'Lon'
    },inplace=True)

    
    rainfallDF=pd.read_csv(
        f"https://api.all.bdservers.site/bmd_observed_data/get_data_by_date.php?gen_date={date}&type=2"
    )
    
    rainfallDF.drop(columns=['date_time'],inplace=True)
    rainfallDF.rename(
    columns={
        'st_code':'stationID',
        'st_name':'stationName',
        'lat':'Lat','lon':'Lon',
        'rainfall':'Rainfall'
    },inplace=True)
    
    endDate=date+' 06:00:00'
    endDate=datetime.strptime(endDate,'%Y-%m-%d %H:%M:%S')
    #endDate_old=endDate.strftime('%d-%m-%Y %H:%M:%S')
    endDate=endDate.strftime('%d-%m-%Y')
    
    rainfallDF=rainfallDF.sort_values(['Lat','Lon']).reset_index().drop(columns=['index'])
    temperatureDF=temperatureDF.sort_values(['Lat','Lon']).reset_index().drop(columns=['index'])
        
    return startDate,endDate,rainfallDF,temperatureDF


def createGeoPointData(stationRainfallDF,stationTemperatureDF):
    
    
    
    stationGeoRainfall = geopandas.GeoDataFrame(
    stationRainfallDF, 
    geometry=geopandas.points_from_xy(stationRainfallDF.Lon, stationRainfallDF.Lat)
    )
    
    stationPointRainfall=stationGeoRainfall[['stationName','geometry','Rainfall']].copy(deep=True)
    
   
    
    stationGeoTemperature = geopandas.GeoDataFrame(
    stationTemperatureDF, 
    geometry=geopandas.points_from_xy(stationTemperatureDF.Lon, stationTemperatureDF.Lat)
    )

    stationPointTemperature=stationGeoTemperature[['stationName','geometry','meanTemperature']].copy(deep=True)
    
    return stationPointRainfall,stationPointTemperature


def returnMaskedArray():

    fname=r'bangladesh/bangladesh-whole.shp'

    cn_area = fiona.open(fname)
    # pol = cn_area.next()
    pol = next(iter(cn_area))

    geom = shape(pol['geometry'])

    ## four corner 
    x0,x1 = geom.bounds[0],geom.bounds[2]
    y0,y1 = geom.bounds[1],geom.bounds[3]


    x  = np.linspace(x0,x1,100)
    y  = np.linspace(y0,y1,100)
    xx,yy = np.meshgrid(x,y)
    

    mask_ = shapely.vectorized.contains(geom,  xx,yy)
    
    print('Grid Lon Range: ', (x0,x1), 'Grid Lat Range:',(y0,y1))
    
    return x,y,x0,x1,y0,y1,mask_

# the map background function
# the map background function
def back_main_clean(fig,extent):
    
    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
    ax.set_extent(extents=extent, crs=ccrs.Geodetic())
    
    for i in ax.spines.values(): i.set_linewidth(0.01)
        
    fname = r'bangladesh/district-1bd.shp'
    shape_feature = ShapelyFeature(shpreader.Reader(fname).geometries(), 
                                   ccrs.PlateCarree(),facecolor='none', linestyle='dotted',
                                   edgecolor ='gray', linewidth = .3, alpha =1)
    ax.add_feature(shape_feature, zorder =3) 
    
    
    fname = r'bangladesh/DIVISION_BD.shp'
    shape_feature = ShapelyFeature(shpreader.Reader(fname).geometries(), 
                                   ccrs.PlateCarree(),facecolor='none', linestyle='solid',
                                   edgecolor ='black', linewidth = .75, alpha =1)
    ax.add_feature(shape_feature, zorder =3) 
    
    
    return ax



def rainfallInterpolation(plot_out_dir,startDate,endDate,df,x,y,x0,x1,y0,y1,mask_):

    #dates_old=f'({startDate} BST - {endDate} BST)'
    dates=f'({startDate} - {endDate})'
    lons,lats,zdata=df.geometry.x.values,df.geometry.y.values,df.Rainfall.values
    
#     minZ=min(zdata)
    minZ=0
    zdata[zdata < 0] = minZ
    
#     print('Station Lon-Min-Max: ',lons.min(),lons.max())
#     print('Station Lat-Min-Max: ',lats.min(),lats.max())
    
#     print('Shapes of Station Data: ', lons.shape,lats.shape,zdata.shape)
        
    rainOrNoRain=[v for v in zdata if v>0]
    
    if len(rainOrNoRain)>0:

        variogram_model=['linear','gaussian','spherical','power','exponential','hole-effect']
        coordinates_type=['euclidean','geographic']

        OK = OrdinaryKriging(
            lons, lats, zdata, 
            variogram_model=variogram_model[4],
            coordinates_type=coordinates_type[0],
            anisotropy_scaling=1.0,
            weight=True,
            exact_values=True,
            pseudo_inv=True

        )

        zz, ss1 = OK.execute('grid', x, y)
        
        zz_mask = np.ma.masked_array(zz.data,~mask_)


        fig = plt.figure(figsize=(10, 10))
        extent=[x0,x1,y0,y1]
        ax = back_main_clean(fig, extent)

        xx,yy = np.meshgrid(x,y)

        #Filtering for all the negative values and getting the min of them
        positiveList=zz.flatten()
        minPositive=min([p for p in positiveList if p >0])
        zz=np.where(zz<0, minPositive, zz)

#         minimal_value,maximal_value=zz.min(),zz.max()
        minimal_value,maximal_value=min(rainOrNoRain),max(rainOrNoRain)

        # print(minimal_value,maximal_value)

        if (maximal_value-minimal_value) <=2:
            levels = np.linspace(minimal_value,maximal_value+2,2)
            cs=plt.contourf(x, y, zz_mask,levels=levels,cmap='Blues') 

        else :
            levels = np.linspace(minimal_value,maximal_value,100)
            cs=plt.contourf(x, y, zz_mask,levels=levels,cmap='Blues') 

            # cs=plt.contourf(x, y, zz_mask,levels=levels,cmap='Blues') 

            bounds=np.linspace(minimal_value, maximal_value+.50,num=10,endpoint=True)
            bounds=[int(b) for b in bounds]

            cb=plt.colorbar(ticks=bounds,spacing='uniform',orientation='vertical',aspect=55)



        ax.set_ylim(20.5,26.8)
        ax.set_xlim(87.9,92.8)
        gl = ax.gridlines(draw_labels=True)
        gl.top_labels=False
        gl.right_labels=False



        #plt.title(f'7 Days Accumulated Observed Rainfall (mm) \n{dates}\n', fontsize=12)
        plt.title(f'7 Days Accumulated Observed Rainfall (mm)', fontsize=12)




        fig.savefig(os.path.join( plot_out_dir,'rainfallObserved.png'),transparent=True, bbox_inches='tight')
    
    elif len(rainOrNoRain)==0:
        
        xx,yy = np.meshgrid(x,y)
        zz = np.zeros_like(xx)
        
        fig = plt.figure(figsize=(10, 10))
        extent=[x0,x1,y0,y1]
        ax = back_main_clean(fig, extent)
        
        plt.plot(zz)
        zz_mask=zz
        ax.set_ylim(20.5,26.8)
        ax.set_xlim(87.9,92.8)
        gl = ax.gridlines(draw_labels=True)
        gl.top_labels=False
        gl.right_labels=False



        #plt.title(f'7 Days Accumulated Observed Rainfall (mm) \n{dates}\n', fontsize=12)
        plt.title(f'7 Days Accumulated Observed Rainfall (mm)', fontsize=12)
        
        fig.savefig(os.path.join( plot_out_dir,'rainfallObserved.png'),transparent=True, bbox_inches='tight')

    
    return df,zdata,zz_mask

def temperatureInterpolation(plot_out_dir,startDate,endDate,df,x,y,x0,x1,y0,y1,mask_):

    lons,lats,zdata=df.geometry.x.values,df.geometry.y.values,df.meanTemperature.values

    variogram_model=['linear','gaussian','spherical','power','exponential','hole-effect']
    coordinates_type=['euclidean','geographic']

    OK = OrdinaryKriging(
        lons, lats, zdata, 
        variogram_model=variogram_model[3],
        coordinates_type=coordinates_type[0],
        anisotropy_scaling=1.0,
        weight=True,
        exact_values=True,
        pseudo_inv=True

    )

    zz, ss1 = OK.execute('grid', x, y)

    zz_mask = np.ma.masked_array(zz.data,~mask_)



    fig = plt.figure(figsize=(10, 10))
    
    extent=[x0,x1,y0,y1]
    ax = back_main_clean(fig, extent)

    xx,yy = np.meshgrid(x,y)


#     minimal_value,maximal_value=df.meanTemperature.min(),df.meanTemperature.max()
    minimal_value,maximal_value=zz_mask.min(),zz_mask.max()


    levels = np.linspace(minimal_value-.50,maximal_value+.50,100)
    cs=plt.contourf(x, y, zz_mask,levels=levels,cmap='jet') 

    # colormap
#     bounds=[i for i in range(int(minimal_value),int(maximal_value),1)] 
    bounds=np.linspace(minimal_value, maximal_value,num=10,endpoint=True)
    bounds=[round(b,1) for b in bounds]
    
    cb=plt.colorbar(ticks=bounds,
             spacing='uniform',
             orientation='vertical',
             aspect=55)
        
#     cmap = plt.get_cmap('jet', len(bounds)+1)



#     # Normalizer
#     # bounds = mlp.colors.Normalize(vmin=0, vmax=maximal_value)

#     norm = mlp.colors.BoundaryNorm(bounds, cmap.N, extend='both')
#     # creating ScalarMappable
#     sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
#     sm.set_array([])

#     cb=plt.colorbar(sm, ticks=np.linspace(int(minimal_value), int(maximal_value), len(bounds)+2),
#                  spacing='uniform',
#                  orientation='vertical',
# #                  label='Station Average Temperature Interpolated to District Levels In Centigrade (C° )',
#                  aspect=45
#                 )
    # ax.set_facecolor("white")
    # cb.patch.set_facecolor("white")
    
    #dates_old=f'({startDate} BST - {endDate} BST)'
    dates=f'({startDate} - {endDate})'
    #plt.title(f'Mean Observed Temperature (C°) \n{dates}\n', fontsize=12)
    plt.title(f'Mean Observed Temperature (C°)', fontsize=12)
    
    
    ax.set_ylim(20.5,26.8)
    ax.set_xlim(87.9,92.8)
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    
    fig.savefig( os.path.join( plot_out_dir,'temperatureObserved.png'),transparent=True, bbox_inches='tight')
    
    
    return df,zdata,zz_mask
    

def returnDistrictRainfall(stationPointRainfall):
    
    bdDistrict = geopandas.read_file('bangladesh/district-1bd.shp')
    districtPolygon=bdDistrict[['admin2Name','geometry']]


    stationPoint=stationPointRainfall[['stationName','geometry','Rainfall']]
    districtPolygon=bdDistrict[['admin2Name','geometry']]
    

    
    
    districtPolygon.crs = stationPoint.crs
    districtRainfallWithPolygon = geopandas.sjoin(stationPoint,districtPolygon,how="right", op='within')
    
    districtRainfallWithPolygon.rename(columns={'admin2Name':'districtName'},inplace=True)
    
    districtRainfallWithPolygon=districtRainfallWithPolygon.fillna(0)
    districtRainfallWithPolygon.fillna(0)
    
    districtRainfallWithPolygon['stationName'] = districtRainfallWithPolygon[
    'stationName'].fillna(districtRainfallWithPolygon['districtName'])
    
    return districtRainfallWithPolygon


def plotInterpolatedRainfall(districtRainfallWithPolygon,stationPointRainfall,plot_out_dir,dates):
    
    minimal_value=districtRainfallWithPolygon['Rainfall'].min()
    maximal_value=districtRainfallWithPolygon['Rainfall'].max()
    
    bounds=[i for i in range(int(minimal_value)
                             ,int(maximal_value)+10,
                             10)]

    fig,ax = plt.subplots(figsize=(8,7))

    
    districtRainfallWithPolygon.plot(ax=ax,column='Rainfall',
                                     scheme='user_defined', classification_kwds={'bins':bounds},
                                     edgecolor = 'black', linewidth=0.5,
                                     legend=False,figsize=(8, 7),
                                     cmap=None)

    # colormap
#     cmap = plt.get_cmap(None, len(bounds)+1)
#     norm = mlp.colors.BoundaryNorm(bounds, cmap.N, extend='both')
#     sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
#     sm.set_array([])

   
    
    levels = np.linspace(minimal_value,maximal_value,100)
    
    
#     cb=plt.colorbar(sm, ticks=np.linspace(int(minimal_value), int(maximal_value), len(bounds)),
#                  spacing='uniform',
#                  orientation='vertical',
#                  aspect=45
#                 )
    
#     ax.grid(b=True, alpha=0.5)

    bounds=np.linspace(minimal_value, maximal_value,num=10,endpoint=True)

    cb=plt.colorbar(ticks=bounds,
                 spacing='uniform',
                 orientation='vertical',
                 aspect=45)


    ax.set_ylim(20.5,26.8)
    ax.set_xlim(87.9,92.8)
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels=False
    gl.right_labels=False
    
    #plt.title(f'District Level Accumulated Observed Rainfall (mm) \n{dates}\n', fontsize=12)    
    plt.title(f'District Level Accumulated Observed Rainfall (mm)', fontsize=12)    
    ax.figure.savefig( os.path.join( plot_out_dir,'districtObservedRainfall.png'),transparent=True, bbox_inches='tight')
    
def rainfallInterpolate(districtRainfallWithPolygon,stationPointRainfall,plot_out_dir,dates):
    
    interpolatedDF=districtRainfallWithPolygon.copy(deep=True)
    interpolatedDF['Rainfall'].interpolate(method='linear', limit_direction='both', inplace=True,axis=0)
    
    plotInterpolatedRainfall(interpolatedDF,stationPointRainfall,plot_out_dir,dates)
    
    return interpolatedDF


def returnDistrictTemperature(stationPointTemperature):
    
    bdDistrict = geopandas.read_file('bangladesh/district-1bd.shp')
    districtPolygon=bdDistrict[['admin2Name','geometry']]


    stationPointTemperature=stationPointTemperature[['stationName','geometry','meanTemperature']]
    districtPolygon=bdDistrict[['admin2Name','geometry']]
    

    
    
    districtPolygon.crs = stationPointTemperature.crs
    districtTemperaturePolygon = geopandas.sjoin(stationPointTemperature,districtPolygon,how="right", op='within')
    
    districtTemperaturePolygon.rename(columns={'admin2Name':'districtName'},inplace=True)
    
    districtTemperaturePolygon['stationName'] = districtTemperaturePolygon[
    'stationName'].fillna(districtTemperaturePolygon['districtName'])
    
    return districtTemperaturePolygon


def plotTemperatureInterpolation(districtTemperaturePolygon,stationPointTemperature,plot_out_dir,dates):
    
    minimal_value=districtTemperaturePolygon['meanTemperature'].min()
    maximal_value=districtTemperaturePolygon['meanTemperature'].max()
    
    bounds=[i for i in np.arange(minimal_value,maximal_value+1,.50)]
    
#     fig= plt.figure(figsize=(10, 10))

    fig,ax = plt.subplots(figsize=(8,7))
    
    districtTemperaturePolygon.plot(ax=ax,column='meanTemperature',
                                     scheme='user_defined', classification_kwds={'bins':bounds},
                                     edgecolor = 'black', linewidth=0.5,
                                     legend=False,figsize=(8, 7),
                                     cmap='jet')

#     print(minimal_value,bounds,maximal_value)
    # colormap
    cmap = plt.get_cmap('jet')
    norm = mlp.colors.BoundaryNorm(bounds, cmap.N, extend='both')
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cb=plt.colorbar(sm, ticks=bounds,
                 spacing='uniform',
                 orientation='vertical',
                 aspect=45
                )
    #plt.title(f'District Level Mean Observed Temperature (C°) \n{dates}\n', fontsize=12)
    plt.title(f'District Level Mean Observed Temperature (C°)', fontsize=12)
    ax.grid(b=True, alpha=0.5)
    ax.figure.savefig( os.path.join( plot_out_dir,'districtObservedTemp.png'),transparent=True, bbox_inches='tight')
    

def interpolateTemperature(df,stationDF,plot_out_dir,dates):
    
    interpolatedDF=df.copy(deep=True)
#     display(interpolatedDF)
    interpolatedDF['meanTemperature'].interpolate(method='linear', limit_direction='both', inplace=True,axis=0)
    
    plotTemperatureInterpolation(interpolatedDF,stationDF,plot_out_dir,dates)
    
    return interpolatedDF


def main(date):

    date=str(date)
    dateString=f'{date[:4]}-{date[4:6]}-{date[6:]}'
    
    plot_out_dir = f'{date}'

    if not os.path.exists(plot_out_dir):
        os.makedirs(plot_out_dir)

    startDate,endDate,stationRainfallDF,stationTemperatureDF=importData(dateString)
    stationPointRainfall,stationPointTemperature=createGeoPointData(stationRainfallDF,stationTemperatureDF)

    # print(stationPointRainfall)

    x,y,x0,x1,y0,y1,mask_=returnMaskedArray()

    df,zdata,zz_mask=rainfallInterpolation(plot_out_dir,startDate,endDate,stationPointRainfall,x,y,x0,x1,y0,y1,mask_)
    df,zdata,zz_mask=temperatureInterpolation(plot_out_dir,startDate,endDate,stationPointTemperature,x,y,x0,x1,y0,y1,mask_)
    
    
#     districtRainfallWithPolygon=returnDistrictRainfall(stationPointRainfall)
#     interpolatedDF=rainfallInterpolate(districtRainfallWithPolygon,stationPointRainfall,plot_out_dir,dates)
      
#     districtTemperaturelWithPolygon=returnDistrictTemperature(stationPointTemperature)
#     interpolatedDF=interpolateTemperature(districtTemperaturelWithPolygon,stationPointTemperature,plot_out_dir,dates)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('provide date of data in yyyymmdd fromat')
        sys.exit(100)
    
    main(sys.argv[1])