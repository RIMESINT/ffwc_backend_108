import os
import json
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mplcolors
import geojsoncontour as gj
from tqdm import tqdm
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Step 2: Generate GeoJSON maps and SVG legends for UKMET Anomaly'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str, help='Forecast date YYYYMMDD')

    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        
        BASE_PATH = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate, 'UKMET')
        NC_FILE = os.path.join(BASE_PATH, f'ukmet_rainfall_anomaly_{fdate}.nc')

        if not os.path.exists(NC_FILE):
            self.stdout.write(self.style.ERROR(f"❌ Anomaly NetCDF not found: {NC_FILE}"))
            return

        ds = xr.open_dataset(NC_FILE)
        anomaly = ds['rainfall_anomaly']
        
        # Divergent Color Scale
        anom_colors = ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffff', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4']
        anom_levels = [-100, -50, -25, -10, -2, 2, 10, 25, 50, 100]
        cmap = mplcolors.ListedColormap(anom_colors)
        norm = mplcolors.BoundaryNorm(anom_levels, cmap.N)

        finfo = {"fdate": fdate, "rf": [], "tmin": [], "tmax": [], "rh": [], "ws": [], "cldflo": [], "thi_min": [], "thi_max": []}

        for i in tqdm(range(len(anomaly.time)), desc="Rasterizing UKMET"):
            data_slice = anomaly.isel(time=i)
            t_start_utc = pd.to_datetime(data_slice.time.values)
            s_str = t_start_utc.strftime('%Y%m%d%H')
            
            # UKMET steps are usually 24h
            start_bst = (t_start_utc + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')
            end_bst = (t_start_utc + timedelta(hours=30)).strftime('%Y-%m-%d %H:%M')

            json_name = f"anom_{fdate}_{s_str}.geojson"
            svg_name = f"anom_{fdate}_{s_str}.svg"

            # A. GeoJSON Generation
            fig, ax = plt.subplots()
            cp = ax.contourf(ds.lon, ds.lat, data_slice, levels=anom_levels, cmap=cmap, norm=norm, extend='both')
            with open(os.path.join(BASE_PATH, json_name), 'w') as jf:
                jf.write(gj.contourf_to_geojson(cp))
            plt.close(fig)

            # B. SVG Legend Generation
            fig_cbar = plt.figure(figsize=(8, 1.2))
            ax_cbar = fig_cbar.add_axes([0.05, 0.5, 0.9, 0.15]) 
            cb = plt.colorbar(cp, cax=ax_cbar, orientation='horizontal', ticks=anom_levels)
            cb.set_label('UKMET Rainfall Anomaly (mm/day)', fontsize=9, fontweight='bold')
            
            plt.savefig(os.path.join(BASE_PATH, svg_name), format='svg', bbox_inches='tight', transparent=True)
            plt.close(fig_cbar)

            finfo["rf"].append({
                "file": json_name,
                "cmap": svg_name,
                "start": start_bst,
                "end": end_bst
            })

        info_path = os.path.join(BASE_PATH, f'info.{fdate}.json')
        with open(info_path, 'w') as f:
            json.dump(finfo, f, indent=2)
            
        self.stdout.write(self.style.SUCCESS(f"✅ UKMET Raster Assets Generated in: {BASE_PATH}"))