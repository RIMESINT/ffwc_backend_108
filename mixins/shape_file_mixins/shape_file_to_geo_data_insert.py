
from user_authentication.models import (GeoData, GeoLevel)









class ShapeFileTOGeoDataInsert:
    def shape_file_to_geodata_conversion(geo_details):
        for rec in geo_details["data_list"]:
            geo_obj = GeoData(
                name = rec[0],
                unique_value = rec[1],
                unique_key = geo_details["unique_key"],
                parent = geo_details["parent_details"],
                level_name = geo_details["shape_file_obj"][0]["level"],
                level_id = geo_details["level"],
            )
            geo_obj.save()
 
        # geo_obj = GeoData(
        #     name = rec[0],
        #     unique_value = rec[1],
        #     unique_key = geo_details["unique_key"],
        #     parent = geo_details["parent_details"],
        #     level_name = geo_details["shape_file_obj"][0]["level"],
        #     level_id = geo_details["level"],
        # )
        # geo_obj.save()