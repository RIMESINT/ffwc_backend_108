import fiona
from shapely.geometry import shape

import os

from ffwc_django_project import settings



"""
    ###############################################
    ### START SHAPEFILE UNIQUE FIELS FINDOUT
    ###############################################
"""
class ShapeFile:
    
    def get_asset_info(file:str)->tuple:
        """
            Function for get unique fields
        """
        info = dict()
        all_keys = []

        try:
            sf = fiona.open(file,'r')
        except Exception as e:
            return (False, dict(type="file open", error=str(e)), info)

        sf_schema_prop = sf.schema['properties']

        # only allow string and int header
        allowed_header_types = ['int','str']
        allowed_headers = []
        header_values = dict()
        
        for header in sf_schema_prop:
            if sf_schema_prop[header].split(':')[0] in allowed_header_types:
                allowed_headers.append(header)
                header_values[header] = set()

        rec_count = 0

        for i, rec in enumerate(sf):
            
            try:
                if rec['geometry']['type'] not in ['MultiPolygon',  'Polygon']:
                    # raise ValueError('File contains non polygon record')
                    return (False, dict(type="geometry reading", error="File contains non polygon record"), info)
                
                shp = shape(rec['geometry'])
                # print(" ########### under shp: ", shp)
                all_keys = list(rec["properties"].keys())
                # print(" ########### under all_keys: ", all_keys)
                # print(" ########### is_valid: ", shp.is_valid)

                if not shp.is_valid:
                    # raise ValueError(f'File contains invalid geometry at record no {i}')
                    return (False, dict(type="geometry reading", error=f'File contains invalid geometry at record no {i}'), info)

            except Exception as e:
                return (False, dict(type="geometry reading", error=str(e)), info)            


            for _header in allowed_headers:
                header_values[_header].add( rec['properties'][_header] )

            rec_count = i+1

        unique_headers = []

        for _header in allowed_headers:

            if len(header_values[_header]) == rec_count:
                unique_headers.append(_header)
        
        info['rec_count'] = rec_count
        info['unique_fields'] = unique_headers
        info['all_keys'] = all_keys

        """
            Also count the number of polygon in shape file
        """
        # polygon_info = dict()
        for layername in fiona.listlayers(file): 
            with fiona.open(file, layer=layername) as src: 
                # print(layername, len(src)) 
                info['number_of_polygon'] = len(src)

        return (True, None, info)   



# file = os.path.join(settings.BASE_DIR,settings.BD_SHAPE_FILE,'bd_adm0_level_geojson.geojson')
# output = ShapeFile.get_asset_info(file)
# print("output: ", output) 
