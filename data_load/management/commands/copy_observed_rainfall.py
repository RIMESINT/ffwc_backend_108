import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, connections
from django.utils import timezone
from data_load.models import RainfallObservation, RainfallStation

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Copy data from rainfall_observations in c7ffwcdb to rainfall_observations in default database'

    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting data copy from c7ffwcdb to default database for rainfall_observations...'))

        with connections['c7ffwcdb'].cursor() as cursor:
            cursor.execute("SELECT rf_id, st_id, rf_date, rainFall FROM rainfall_observations")
            old_records = cursor.fetchall()
            total_records = len(old_records)
            self.stdout.write(self.style.NOTICE(f'Found {total_records} records to copy.'))

        success_count = 0
        skipped_count = 0
        batch = []

        with transaction.atomic(using='default'):
            for rf_id, st_id, rf_date, rainfall in old_records:
                if rf_date is None:
                    logger.warning(f'NULL rf_date for st_id {st_id}, rf_id {rf_id}. Skipping record.')
                    self.stdout.write(self.style.WARNING(f'Skipping st_id {st_id}, rf_id {rf_id}: NULL rf_date.'))
                    skipped_count += 1
                    continue

                try:
                    station = RainfallStation.objects.using('default').get(station_id=st_id)
                except RainfallStation.DoesNotExist:
                    logger.warning(f'No RainfallStation found for st_id {st_id} in default database. Skipping record.')
                    self.stdout.write(self.style.WARNING(f'Skipping st_id {st_id}, rf_id {rf_id}: No matching RainfallStation.'))
                    skipped_count += 1
                    continue

                try:
                    if isinstance(rf_date, str):
                        rf_date_str = rf_date.strip()
                        logger.debug(f'Processing string rf_date for st_id {st_id}, rf_id {rf_id}: {repr(rf_date_str)}')
                        observation_date = datetime.strptime(rf_date_str, self.DATE_FORMAT)
                        if timezone.is_naive(observation_date):
                            observation_date = timezone.make_aware(observation_date, timezone.get_default_timezone())
                    else:
                        logger.debug(f'Processing datetime rf_date for st_id {st_id}, rf_id {rf_id}: {rf_date}')
                        observation_date = rf_date
                        if timezone.is_naive(observation_date):
                            observation_date = timezone.make_aware(observation_date, timezone.get_default_timezone())
                except (ValueError, TypeError) as e:
                    logger.error(f'Failed to process rf_date for st_id {st_id}, rf_id {rf_id}: {repr(rf_date)} - Error: {str(e)}')
                    self.stdout.write(self.style.WARNING(f'Skipping st_id {st_id}, rf_id {rf_id}: Invalid rf_date: {repr(rf_date)}'))
                    skipped_count += 1
                    continue

                batch.append(RainfallObservation(
                    station_id_id=station.pk,
                    observation_date=observation_date,
                    rainfall=rainfall
                ))

                if len(batch) >= 1000:
                    try:
                        RainfallObservation.objects.using('default').bulk_create(batch)
                        success_count += len(batch)
                        self.stdout.write(self.style.NOTICE(f'Processed batch of {len(batch)} records. Total successful: {success_count}'))
                    except Exception as e:
                        logger.error(f'Failed to bulk create batch: {str(e)}')
                        self.stdout.write(self.style.ERROR(f'Error in batch processing: {str(e)}'))
                        skipped_count += len(batch)
                    batch = []

            if batch:
                try:
                    RainfallObservation.objects.using('default').bulk_create(batch)
                    success_count += len(batch)
                    self.stdout.write(self.style.NOTICE(f'Processed final batch of {len(batch)} records. Total successful: {success_count}'))
                except Exception as e:
                    logger.error(f'Failed to bulk create final batch: {str(e)}')
                    self.stdout.write(self.style.ERROR(f'Error in final batch processing: {str(e)}'))
                    skipped_count += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Successfully copied {success_count} records to default database.'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped_count} records due to missing RainfallStation entries or invalid rf_date.'))