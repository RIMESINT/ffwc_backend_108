import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from data_load.models import WaterLevelObservations, WaterLevelObservation, Station

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Copy data from water_level_observations in c7ffwcdb to water_level_observations in default database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting data copy from c7ffwcdb to default database...'))

        # Fetch all records from the old table in c7ffwcdb
        old_records = WaterLevelObservations.objects.using('c7ffwcdb').all()
        total_records = old_records.count()
        self.stdout.write(self.style.NOTICE(f'Found {total_records} records to copy.'))

        success_count = 0
        skipped_count = 0

        # Use a transaction for writes to default database
        with transaction.atomic(using='default'):
            for old_record in old_records:
                # Find the corresponding Station instance in default database
                try:
                    station = Station.objects.using('default').get(station_id=old_record.st_id)
                except Station.DoesNotExist:
                    logger.warning(f'No Station found for st_id {old_record.st_id} in default database. Skipping record.')
                    self.stdout.write(self.style.WARNING(f'Skipping st_id {old_record.st_id}: No matching Station.'))
                    skipped_count += 1
                    continue

                # Create a new record in the new table
                WaterLevelObservation.objects.using('default').create(
                    station_id_id=station.pk,  # Use the primary key of the Station instance
                    observation_date=old_record.wl_date,
                    water_level=old_record.waterlevel
                )
                success_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully copied {success_count} records to default database.'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped_count} records due to missing Station entries.'))