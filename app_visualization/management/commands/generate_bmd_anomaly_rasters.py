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
    help = 'Step 2: Generate FFWC-compliant GeoJSON (Map) and SVG (Colorbar Only) assets'

    def add_arguments(self, parser):
        # 1. Positional argument support for manual CLI cron execution tasks
        parser.add_argument('fdate', nargs='?', type=str, help='Forecast date YYYYMMDD')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')

        if ui_date:
            # Clean dashboard template dashes safely: '2026-06-30' -> '20260630'
            fdate = ui_date.replace('-', '')
            self.stdout.write(self.style.SUCCESS(f"###### Received date parameter via UI Selector: {ui_date} -> Normalized to: {fdate}"))
        elif positional_date:
            fdate = positional_date
            self.stdout.write(self.style.SUCCESS(f"###### Received date parameter via Positional CLI: {fdate}"))
        else:
            fdate = dt.now().strftime('%Y%m%d')
            self.stdout.write(self.style.NOTICE(f"###### No runtime date parameter detected. Defaulting to system time: {fdate}"))
        
        # Setup Paths
        BASE_PATH = os.path.join(settings.BASE_DIR, 'assets', 'rainfall-anomaly', fdate, 'BMD-WRF')
        NC_FILE = os.path.join(BASE_PATH, f'bmd_rainfall_anomaly_{fdate}.nc')

        self.stdout.write(f"🚀 Starting Raster Generation for: {fdate}")

        if not os.path.exists(NC_FILE):
            self.stdout.write(self.style.ERROR(f"❌ Error: NetCDF file not found at {NC_FILE}"))
            return

        # Load the Anomaly NetCDF
        ds = xr.open_dataset(NC_FILE)
        anomaly = ds['rainfall_anomaly']
        
        # Define the Anomaly Color Scale (Divergent)
        anom_colors = ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffff', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4']
        anom_levels = [-100, -50, -25, -10, -2, 2, 10, 25, 50, 100]
        cmap = mplcolors.ListedColormap(anom_colors)
        norm = mplcolors.BoundaryNorm(anom_levels, cmap.N)

        # Initialize FFWC Metadata Template
        finfo = {
            "fdate": fdate,
            "rf": [], 
            "tmin": [], "tmax": [], "rh": [], "ws": [], 
            "cldflo": [], "thi_min": [], "thi_max": []
        }

        # Loop through each time step
        for i in tqdm(range(len(anomaly.time)), desc="Rasterizing"):
            data_slice = anomaly.isel(time=i)
            
            # UTC Time extraction
            t_start_utc = pd.to_datetime(data_slice.time.values)
            t_end_utc = t_start_utc + timedelta(days=1)
            
            # Formats for physical filename (YYYYMMDDHH)
            s_str = t_start_utc.strftime('%Y%m%d%H')
            
            # BST Time for JSON display strings (+6 hours)
            start_bst = (t_start_utc + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')
            end_bst = (t_end_utc + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')

            # Filenames
            json_name = f"anom_{fdate}_{s_str}.geojson"
            svg_name = f"anom_{fdate}_{s_str}.svg"

            # --- Create Visuals ---

            # A. Generate GeoJSON (using a temporary figure)
            fig_data, ax_data = plt.subplots()
            cp = ax_data.contourf(
                ds.lon, ds.lat, data_slice, 
                levels=anom_levels, 
                cmap=cmap, 
                norm=norm, 
                extend='both'
            )
            
            geojson_path = os.path.join(BASE_PATH, json_name)
            with open(geojson_path, 'w') as jf:
                jf.write(gj.contourf_to_geojson(cp))
            plt.close(fig_data) 

            # B. Generate SVG Legend (Colorbar ONLY)
            fig_cbar = plt.figure(figsize=(8, 1.2))
            ax_cbar = fig_cbar.add_axes([0.05, 0.5, 0.9, 0.15]) 
            
            cb = plt.colorbar(
                cp, 
                cax=ax_cbar, 
                orientation='horizontal', 
                ticks=anom_levels
            )
            cb.set_label('Rainfall Anomaly (mm/day)', fontsize=9, fontweight='bold')
            cb.ax.tick_params(labelsize=8)
            
            svg_path = os.path.join(BASE_PATH, svg_name)
            plt.savefig(svg_path, format='svg', bbox_inches='tight', transparent=True)
            plt.close(fig_cbar)

            # Append to Metadata list
            finfo["rf"].append({
                "file": json_name,
                "cmap": svg_name,
                "start": start_bst,
                "end": end_bst
            })

        # Save the final info.json
        info_path = os.path.join(BASE_PATH, f'info.{fdate}.json')
        with open(info_path, 'w') as f:
            json.dump(finfo, f, indent=2)
            
        self.stdout.write(self.style.SUCCESS(f"✅ SUCCESSFULLY GENERATED:"))
        self.stdout.write(f"   - {len(anomaly.time)} GeoJSON/SVG pairs")
        self.stdout.write(f"   - Metadata: {info_path}")