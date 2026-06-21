# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.db import connection, transaction
# Make sure to change 'data_load' to your actual Django app name if different
from data_load.models import WaterLevelObservation 

class Command(BaseCommand):
    help = 'Replace 2020 water level data for station 72 with data from historical dump table'

    def handle(self, *args, **options):
        self.stdout.write("Initializing data replacement for Station 72 (Year 2020)...")

        # Configuration Constants
        TARGET_STATION = 72
        START_DATE = "2020-01-01 00:00:00"
        END_DATE = "2020-12-31 23:59:59"

        # Using transaction.atomic ensures that if the insert fails, the old data isn't lost permanently.
        with transaction.atomic():
            
            # --- STEP 1: PURGE OLD DATA FOR REPLACEMENT ---
            self.stdout.write("Step 1: Purging existing 2020 entries for Station 72 from active table...")
            deleted_count, _ = WaterLevelObservation.objects.filter(
                station_id=TARGET_STATION,
                observation_date__range=(START_DATE, END_DATE)
            ).delete()
            self.stdout.write(f"--> Removed {deleted_count} old records. Active table is now ready for replacement.")

            # --- STEP 2: FETCH REPLACEMENT DATA FROM HISTORICAL DUMP ---
            self.stdout.write("Step 2: Fetching new replacement records from historical table...")
            raw_select_query = """
                SELECT st_id, wl_date, waterLevel 
                FROM water_level_hist_observations 
                WHERE st_id = %s AND wl_date BETWEEN %s AND %s
            """
            
            with connection.cursor() as cursor:
                cursor.execute(raw_select_query, [TARGET_STATION, START_DATE, END_DATE])
                historical_rows = cursor.fetchall()

            if not historical_rows:
                self.stdout.write(self.style.WARNING("⚠️ No matching 2020 historical records found to insert. Aborting rollback."))
                return

            self.stdout.write(f"--> Found {len(historical_rows)} historical records to copy.")

            # --- STEP 3: STAGE NEW DATA ---
            self.stdout.write("Step 3: Staging replacement records in memory...")
            new_records = []
            for row in historical_rows:
                st_id, wl_date, water_level = row
                new_records.append(
                    WaterLevelObservation(
                        station_id_id=st_id,  # Direct assignment to underlying column
                        observation_date=wl_date,
                        water_level=water_level
                    )
                )

            # --- STEP 4: BULK INSERT NEW DATA ---
            self.stdout.write("Step 4: Inserting replacement data into active table...")
            WaterLevelObservation.objects.bulk_create(new_records, batch_size=5000)
            
            self.stdout.write(
                self.style.SUCCESS(f"🎉 SUCCESS: Old 2020 data for station {TARGET_STATION} has been completely replaced with {len(new_records)} records!")
            )