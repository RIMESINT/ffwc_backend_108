import xarray as xr

# Define the path to your NetCDF file
# file_path = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/forecast/25092025.nc'
# file_path = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/UkMET_deterministic/ukmet_det_20250927/precip_20250927.nc'

# file_path = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/20250926/R1E.20250926.en_01.nc'

file_path = '/home/rimes/ffwc-rebase/backend/ffwc_django_project/UkMET_ensemble/ukmet_ens_20250926/precip_EN01.nc'


# Open the file as an xarray Dataset
try:
    ds = xr.open_dataset(file_path)

    # Simply printing the dataset object provides a full inspection
    print(ds)

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.")