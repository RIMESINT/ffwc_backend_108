import fiona
from shapely.geometry import shape

import os









class Boundary:
    
    def get_lat_lon(destination_dir:str):
        """
            Function for longitude and latitude as array
            Input:
                file: path of a geojson file
            Output:
                return: longitude and latitude as a DICTIONARY
        """

        c = fiona.open(destination_dir, 'r')  
        area_boundary = c.next()
        longitude = [shape(area_boundary['geometry']).bounds[0], shape(area_boundary['geometry']).bounds[2]]
        latitude = [shape(area_boundary['geometry']).bounds[1], shape(area_boundary['geometry']).bounds[3]]
        return dict(longitude=longitude, latitude=latitude) 