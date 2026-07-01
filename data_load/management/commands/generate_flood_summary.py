# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime, timedelta
import pandas as pd
import json
import os
from data_load.models import WaterLevelObservation, RainfallObservation, RainfallStation

class Command(BaseCommand):
    help = 'Generate Flood Summary Report with dynamic parameter routing and Day-1 Fallback'

    def add_arguments(self, parser):
        # 1. Positional argument support for direct console execution and crontab macros
        parser.add_argument('fdate', nargs='?', type=str, help='Target date in YYYYMMDD format')
        # 2. Keyed option flag mapping to support date-picker from Django Dashboard UI
        parser.add_argument('--date', type=str, help='Target date from Django UI picker in format YYYY-MM-DD')

    def handle(self, *args, **kwargs):
        ui_date = kwargs.get('date')
        positional_date = kwargs.get('fdate')
        raw_date = ui_date if ui_date else positional_date

        if not raw_date:
            # Fallback to checking the latest database entry if no explicit date parameter is provided
            latest_obs = WaterLevelObservation.objects.filter(
                water_level__gte=0
            ).order_by('-observation_date').first()
            
            if latest_obs:
                date_input = latest_obs.observation_date.strftime('%Y-%m-%d')
                self.stdout.write(f"Latest Date pulled from Database logs: {latest_obs.observation_date}")
            else:
                date_input = datetime.today().strftime('%Y-%m-%d')
                self.stdout.write(f"No valid telemetry data discovered, using current system date: {date_input}")
        else:
            date_input = raw_date
            if "-" not in date_input:
                try:
                    date_input = datetime.strptime(date_input, '%Y%m%d').strftime('%Y-%m-%d')
                except:
                    pass

        # Execute processing pipeline with automatic previous day recursive fallback checks
        if not self.run_summary_pipeline(date_input):
            try:
                current_dt = datetime.strptime(date_input, '%Y-%m-%d')
                yesterday_str = (current_dt - timedelta(days=1)).strftime('%Y-%m-%d')
                self.stdout.write(self.style.WARNING(f"⚠️ Telemetry data missing for date: {date_input}. Attempting historical fallback to: {yesterday_str}..."))
                if not self.run_summary_pipeline(yesterday_str):
                    self.stderr.write(self.style.ERROR(f"❌ Failed to extract data logs for both {date_input} and historical fallback window."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Critical failure executing summary date fallback sequence: {str(e)}"))

    def run_summary_pipeline(self, date_input):
        self.stdout.write(self.style.NOTICE(f"--- Compiling Flood Summary Report Matrix for: {date_input} ---"))
        
        try:
            target_date = datetime.strptime(date_input, '%Y-%m-%d').date()
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid date sequence parsed: {date_input}"))
            return False

        # 1. Extract Water Level Telemetry Indices
        wl_qs = WaterLevelObservation.objects.filter(observation_date=target_date)
        if not wl_qs.exists():
            print(f"No Water Level Observations discovered in tables for date: {date_input}")
            return False

        # Compute Gauge Threshold Highlights
        danger_count = 0
        flowing_above_danger_stations = []

        for obs in wl_qs:
            wl = obs.water_level
            dl = obs.station_id.danger_level if obs.station_id else None
            
            if wl is not None and dl is not None and wl > dl:
                danger_count += 1
                flowing_above_danger_stations.append({
                    "station_name": obs.station_id.name,
                    "river": obs.station_id.river,
                    "water_level": float(wl),
                    "danger_level": float(dl),
                    "above_danger_mm": round(float(wl - dl) * 1000, 2)
                })

        # 2. Extract Heavy Rainfall Telemetry Indices
        rf_qs = RainfallObservation.objects.filter(observation_date=target_date, rainfall__gte=50.0)
        heavy_rainfall_stations = []

        for obs in rf_qs:
            heavy_rainfall_stations.append({
                "station_name": obs.station_id.name if obs.station_id else "Unknown",
                "station_code": obs.station_id.station_code if obs.station_id else None,
                "rainfall_mm": float(obs.rainfall)
            })

        # 3. Compile Core Summary Dictionary Metadata JSON Payload
        summary_payload = {
            "report_date": date_input,
            "generation_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_stations_above_danger": danger_count,
            "stations_above_danger_list": flowing_above_danger_stations,
            "heavy_rainfall_stations_list": heavy_rainfall_stations
        }

        # 4. Save to target output directory context relative to settings.BASE_DIR
        output_directory = os.path.join(settings.BASE_DIR, 'assets', 'jsonOutput')
        os.makedirs(output_directory, exist_ok=True)
        
        output_filepath = os.path.join(output_directory, f"flood_summary_report_{date_input.replace('-', '')}.json")
        
        with open(output_filepath, 'w', encoding='utf-8') as jf:
            json.dump(summary_payload, jf, indent=4, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f"✅ Flood Summary structural matrix exported to asset path: {output_filepath}"))
        return True