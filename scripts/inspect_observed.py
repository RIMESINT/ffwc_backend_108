import xarray as xr
ds = xr.open_dataset("/home/rimes/ffwc-rebase/backend/ffwc_django_project/observed/2026086.nc")
print(ds.data_vars)
print(ds.coords)