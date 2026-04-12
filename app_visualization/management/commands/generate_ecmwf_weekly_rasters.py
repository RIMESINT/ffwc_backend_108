import os
import json
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mplcolors
import geojsoncontour as gj
from datetime import datetime as dt, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Generate Weekly GeoJSON and SVG assets for ECMWF'

    def add_arguments(self, parser):
        parser.add_argument('fdate', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        fdate = kwargs['fdate'] or dt.now().strftime('%Y%m%d')
        BASE_PATH = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate, 'ECMWF')
        NC_FILE = os.path.join(BASE_PATH, f"ecmwf_weekly_anomaly_{fdate}.nc")

        if not os.path.exists(NC_FILE):
            self.stdout.write(self.style.ERROR(f"❌ NC not found: {NC_FILE}"))
            return

        ds = xr.open_dataset(NC_FILE)
        anomaly = ds['weekly_anomaly'].squeeze()
        
        anom_colors = ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffff', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4']
        anom_levels = [-50, -30, -20, -10, -2, 2, 10, 20, 30, 50]
        cmap = mplcolors.ListedColormap(anom_colors)
        norm = mplcolors.BoundaryNorm(anom_levels, cmap.N)

        t_start_utc = pd.to_datetime(dt.strptime(fdate, '%Y%m%d'))
        start_bst = (t_start_utc + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')
        end_bst = (t_start_utc + timedelta(days=7, hours=6)).strftime('%Y-%m-%d %H:%M')

        fig, ax = plt.subplots()
        cp = ax.contourf(ds.lon, ds.lat, anomaly, levels=anom_levels, cmap=cmap, norm=norm, extend='both')
        with open(os.path.join(BASE_PATH, f"weekly_anom_{fdate}.geojson"), 'w') as jf:
            jf.write(gj.contourf_to_geojson(cp))
        plt.close(fig)

        fig_cbar = plt.figure(figsize=(8, 1.2))
        ax_cbar = fig_cbar.add_axes([0.05, 0.5, 0.9, 0.15]) 
        cb = plt.colorbar(cp, cax=ax_cbar, orientation='horizontal', ticks=anom_levels)
        cb.set_label('ECMWF 7-Day Mean Anomaly (mm/day)', fontsize=9, fontweight='bold')
        plt.savefig(os.path.join(BASE_PATH, f"weekly_anom_{fdate}.svg"), format='svg', bbox_inches='tight', transparent=True)
        plt.close(fig_cbar)

        with open(os.path.join(BASE_PATH, f'info.weekly.{fdate}.json'), 'w') as f:
            json.dump({"fdate": fdate, "rf": [{"file": f"weekly_anom_{fdate}.geojson", "cmap": f"weekly_anom_{fdate}.svg", "start": start_bst, "end": end_bst}]}, f, indent=2)
            
        self.stdout.write(self.style.SUCCESS(f"✅ ECMWF Weekly Assets Generated"))