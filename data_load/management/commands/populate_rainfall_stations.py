import logging
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from data_load.models import RainfallStation, Basin

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates RainfallStation model using data from ffwc_rainfall_stations and ffwc_rainfall_stations_2025 tables.'

    def handle(self, *args, **options):
        self.stdout.write("Starting population of RainfallStation model...")
        try:
            with transaction.atomic():
                # Fetch data from ffwc_rainfall_stations_2025
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            id, st_id, station, basin, latitude, longitude, 
                            division, district, upazilla, header, dtation_bn,
                            basin_bn, division_bn, district_bn, upazilla_bn
                        FROM ffwc_rainfall_stations_2025
                    """)
                    stations_2025 = cursor.fetchall()

                # Fetch unit data from ffwc_rainfall_stations
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id, unit FROM ffwc_rainfall_stations")
                    unit_data = {row[0]: row[1] for row in cursor.fetchall()}

                # Process each record from ffwc_rainfall_stations_2025
                created_count = 0
                updated_count = 0
                for row in stations_2025:
                    (
                        station_id, st_id, station, basin_name, latitude, longitude,
                        division, district, upazilla, header, dtation_bn,
                        basin_bn, division_bn, district_bn, upazilla_bn
                    ) = row

                    # Get or create Basin instance
                    basin = None
                    if basin_name:
                        basin, _ = Basin.objects.get_or_create(
                            name=basin_name,
                            defaults={'name': basin_name}
                        )

                    # Prepare RainfallStation data
                    station_data = {
                        'station_id': station_id,
                        'station_code': st_id,
                        'name': station,
                        'name_bn': dtation_bn,
                        'basin': basin,
                        'basin_bn': basin_bn,
                        'latitude': latitude,
                        'longitude': longitude,
                        'division': division,
                        'division_bn': division_bn,
                        'district': district,
                        'district_bn': district_bn,
                        'upazilla': upazilla,
                        'upazilla_bn': upazilla_bn,
                        'header': header,
                        'unit': unit_data.get(station_id),
                        'status': True
                    }

                    # Create or update RainfallStation
                    obj, created = RainfallStation.objects.update_or_create(
                        station_id=station_id,
                        defaults=station_data
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(f"Created RainfallStation: {station}")
                    else:
                        updated_count += 1
                        self.stdout.write(f"Updated RainfallStation: {station}")

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Completed! Created {created_count} and updated {updated_count} RainfallStation records."
                    )
                )

        except Exception as e:
            logger.error(f"Error populating RainfallStation: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            raise