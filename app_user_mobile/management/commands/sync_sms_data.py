import requests
import re
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from django.conf import settings
from data_load.models import Station, RainfallStation, WaterLevelObservation, RainfallObservation
from datetime import datetime

class Command(BaseCommand):
    help = 'Syncs SMS data: RF type matches RainfallStation (CL), WL type matches Station (SW)'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, required=True)
        parser.add_argument('--datefrom', type=str, required=True)
        parser.add_argument('--dateto', type=str, required=True)

    def handle(self, *args, **options):
        # 1. Setup External Request to Gateway
        url = f"{settings.SMS_BASE_URL}/sms/list"
        payload = {
            "userid": settings.SMS_USERID,
            "apikey": settings.SMS_APIKEY,
            "source": options['source'],
            "datefrom": options['datefrom'],
            "dateto": options['dateto']
        }

        self.stdout.write("--- [START] Connecting to SMS Gateway ---")

        try:
            response = requests.post(url, json=payload, timeout=20)
            response.raise_for_status()
            data_list = response.json().get('data', [])

            if not data_list:
                self.stdout.write(self.style.WARNING("No data found for this range."))
                return

            self.stdout.write(self.style.SUCCESS(f"Found {len(data_list)} messages. Processing..."))

            for entry in data_list:
                sms_id = entry.get('id')
                raw_text = entry.get('message', '')
                
                self.stdout.write(f"\n[Processing SMS ID: {sms_id}]")

                # Clean: Handle parentheses and double backslashes
                clean_msg = raw_text.replace('(', '').replace(')', '').replace('\\n', '\n')
                records = [r.strip() for r in re.split(r'\n|;', clean_msg) if r.strip()]

                for rec in records:
                    rec = rec.strip().strip(',')
                    parts = [p.strip() for p in rec.split(',')]
                    
                    if len(parts) < 5:
                        self.stdout.write(self.style.ERROR(f"    [SKIP] Format Error: '{rec}'"))
                        continue

                    m_type, st_code, d_str, t_str, val = parts[0:5]

                    try:
                        # Time formatting logic
                        t_str_u = t_str.upper()
                        t_fmt = "%I:%M%p" if ('AM' in t_str_u or 'PM' in t_str_u) else "%H:%M"
                        aware_dt = make_aware(datetime.strptime(f"{d_str} {t_str}", f"%Y-%m-%d {t_fmt}"))

                        # --- RAINFALL LOGIC (Strict RainfallStation / CL Codes) ---
                        if m_type.lower() == 'rf':
                            # Query RainfallStation model using station_code field
                            station = RainfallStation.objects.filter(station_code=st_code).first()
                            
                            if station:
                                obj, created = RainfallObservation.objects.update_or_create(
                                    station_id=station, 
                                    observation_date=aware_dt,
                                    defaults={'rainfall': val}
                                )
                                status = "INSERTED" if created else "UPDATED"
                                self.stdout.write(self.style.SUCCESS(
                                    f"    [RF MATCHED] Station: {station.name} | Code: {st_code} | Value: {val}mm | {status}"
                                ))
                            else:
                                self.stdout.write(self.style.ERROR(
                                    f"    [FAILED] Code '{st_code}' NOT found in Rainfall Monitoring Stations table."
                                ))

                        # --- WATER LEVEL LOGIC (Strict Station / SW Codes) ---
                        elif m_type.lower() == 'wl':
                            # Query Station model using station_code field
                            station = Station.objects.filter(station_code=st_code).first()
                            
                            if station:
                                obj, created = WaterLevelObservation.objects.update_or_create(
                                    station_id=station, 
                                    observation_date=aware_dt,
                                    defaults={'water_level': val}
                                )
                                status = "INSERTED" if created else "UPDATED"
                                self.stdout.write(self.style.SUCCESS(
                                    f"    [WL MATCHED] Station: {station.name} | Code: {st_code} | Value: {val}m | {status}"
                                ))
                            else:
                                self.stdout.write(self.style.ERROR(
                                    f"    [FAILED] Code '{st_code}' NOT found in Waterlevel Stations table."
                                ))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"    [PARSE ERROR] Record '{rec}': {e}"))

            self.stdout.write(self.style.SUCCESS("\n--- [COMPLETE] SMS Sync sequence finished ---"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Critical Error: {str(e)}"))