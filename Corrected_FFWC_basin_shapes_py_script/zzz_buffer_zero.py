import json
from shapely.geometry import shape, mapping

# Load the GeoJSON file
with open('/var/www/prod/ffwc_108_deployed_backup/ffwc_django_project/Corrected_FFWC_basin_shapes_py_script/new_added/Nakuagaon_not_working.geojson', 'r') as f:
    geojson_data = json.load(f)

# Process each feature: load geometry, apply buffer(0), and update it
for feature in geojson_data['features']:
    geom = shape(feature['geometry'])
    # Apply a zero-width buffer to fix geometry issues
    fixed_geom = geom.buffer(0)
    # Update the feature's geometry with the fixed geometry in GeoJSON format
    feature['geometry'] = mapping(fixed_geom)

# Save the updated GeoJSON to a new file
with open('/var/www/prod/ffwc_108_deployed_backup/ffwc_django_project/Corrected_FFWC_basin_shapes_py_script/new_added/Nakuagaon.geojson', 'w') as f:
    json.dump(geojson_data, f)
