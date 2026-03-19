import os, json
import xarray as xr
import rioxarray
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import shape
from shapely.ops import unary_union
from datetime import datetime, timedelta
from tqdm import tqdm
from django.core.management.base import BaseCommand

PROJECT_ROOT = "/home/rimes/ffwc-rebase/backend/ffwc_django_project"


class Command(BaseCommand):
    help = "Generate basin-wise UKMET deterministic rainfall forecast"

    def add_arguments(self, parser):
        parser.add_argument("fdate", type=str)

    def handle(self, *args, **kwargs):
        from app_visualization.models import BasinDetails, ForecastDaily, Source, Parameter
        self.BasinDetails = BasinDetails
        self.ForecastDaily = ForecastDaily
        self.Source = Source
        self.Parameter = Parameter
        self.main(kwargs["fdate"])

    def normalize_path(self, p):
        if p.startswith("/assets/"):
            return os.path.join(PROJECT_ROOT, p.lstrip("/"))
        return p

    def main(self, fdate):

        print("###################################################")
        print("###### Signal file loaded successfully!")
        print("###################################################")
        print(f">>> Generating UKMET basin forecast for {fdate}")

        out_dir = os.path.join(
            PROJECT_ROOT,
            "assets/assets/ukmet_deterministic/forecast_map",
            fdate
        )
        os.makedirs(out_dir, exist_ok=True)

        nc_path = f"{PROJECT_ROOT}/UkMET_deterministic/ukmet_det_{fdate}/precip_{fdate}.nc"
        print(f"Using NC: {nc_path}")

        ds = xr.open_dataset(nc_path)
        rain = ds["tp"].rio.write_crs("EPSG:4326")

        basins = self.BasinDetails.objects.exclude(shape_file_path__isnull=True)
        print(f"Basins found: {basins.count()}")

        param = self.Parameter.objects.get(name="rainfall")
        source = self.Source.objects.get(name="UKMET Deterministic")
        forecast_date = datetime.strptime(fdate, "%Y%m%d").date()

        rows = []
        info_entries = []  # ← NEW

        # loop per day
        for day in range(rain.time.size):

            step_start = datetime.strptime(fdate, "%Y%m%d") + timedelta(days=day+1)
            step_end = step_start + timedelta(days=1)

            layer = rain.isel(time=day)

            features = []

            for basin in basins:
                try:
                    shape_path = self.normalize_path(basin.shape_file_path)
                    if not os.path.exists(shape_path):
                        continue

                    with open(shape_path) as f:
                        gj = json.load(f)

                    geoms = []
                    if gj["type"] == "FeatureCollection":
                        geoms = [shape(f["geometry"]) for f in gj["features"]]
                    elif gj["type"] == "Feature":
                        geoms                 = [shape(gj["geometry"])]
                    else:
                        geoms = [shape(gj)]

                    geom = unary_union(geoms)
                    if not geom.is_valid:
                        geom = geom.buffer(0)
                    if geom.is_empty:
                        continue

                    clipped = layer.rio.clip([geom], rain.rio.crs, drop=True)
                    if clipped.count() == 0:
                        continue

                    mean_val = float(clipped.mean().values)

                    rows.append(self.ForecastDaily(
                        parameter=param,
                        source=source,
                        basin_details=basin,
                        forecast_date=forecast_date,
                        step_start=step_start,
                        step_end=step_end,
                        val_avg=mean_val,
                        val_min=float(clipped.min().values),
                        val_max=float(clipped.max().values),
                    ))

                    features.append({
                        "type": "Feature",
                        "geometry": geom.__geo_interface__,
                        "properties": {
                            "basin": basin.name,
                            "rf": round(mean_val, 2)
                        }
                    })

                except Exception as e:
                    print(f"❌ Error for basin {basin.name}: {e}")

            geojson_name = f"rf.F_{fdate}.S_{step_start.strftime('%Y%m%d')}.E_{step_end.strftime('%Y%m%d')}.geojson"
            geojson_path = os.path.join(out_dir, geojson_name)
            with open(geojson_path, "w") as f:
                json.dump({"type": "FeatureCollection", "features": features}, f)

            plt.figure(figsize=(6, 5))
            layer.plot()
            plt.title(f"Rainfall {step_start.strftime('%Y-%m-%d')}")
            svg_name = geojson_name.replace(".geojson", ".svg")
            plt.savefig(os.path.join(out_dir, svg_name), format="svg")
            plt.close()

            # ← NEW: collect info entry
            info_entries.append({
                "file": geojson_name,
                "cmap": svg_name,
                "start": step_start.strftime("%Y-%m-%d"),
                "end": step_end.strftime("%Y-%m-%d"),
            })

        # replace old records
        self.ForecastDaily.objects.filter(
            source=source,
            parameter=param,
            forecast_date=forecast_date
        ).delete()

        self.ForecastDaily.objects.bulk_create(rows)
        print(f"✔ Inserted {len(rows)} records into ForecastDaily")

        # ← NEW: write info file
        info_path = os.path.join(out_dir, f"info.{fdate}.json")
        with open(info_path, "w") as f:
            json.dump({"fdate": fdate, "rf": info_entries}, f, indent=2)

        print(f"✔ Info file written: {info_path}")
