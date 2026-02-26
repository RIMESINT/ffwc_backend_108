import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, connections
from django.utils import timezone
from data_load.models import WaterLevelForecast, Station

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Copy data from water_level_forecasts in c7ffwcdb to water_level_forecasts in default database'

    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting data copy from c7ffwcdb to default database for water_level_forecasts...'))

        with connections['c7ffwcdb'].cursor() as cursor:
            cursor.execute("SELECT fc_id, st_id, fc_date, waterLevel FROM water_level_forecasts")
            old_records = cursor.fetchall()
            total_records = len(old_records)
            self.stdout.write(self.style.NOTICE(f'Found {total_records} records to copy.'))

        success_count = 0
        skipped_count = 0
        batch = []

        with transaction.atomic(using='default'):
            for fc_id, st_id, fc_date, waterlevel in old_records:
                if not fc_date:
                    logger.warning(f'Empty or NULL fc_date for st_id {st_id}, fc_id {fc_id}. Skipping record.')
                    self.stdout.write(self.style.WARNING(f'Skipping st_id {st_id}, fc_id {fc_id}: Empty or NULL fc_date.'))
                    skipped_count += 1
                    continue

                try:
                    station = Station.objects.using('default').get(station_id=st_id)
                except Station.DoesNotExist:
                    logger.warning(f'No Station found for st_id {st_id} in default database. Skipping record.')
                    self.stdout.write(self.style.WARNING(f'Skipping st_id {st_id}, fc_id {fc_id}: No matching Station.'))
                    skipped_count += 1
                    continue

                try:
                    fc_date_str = fc_date.strip() if isinstance(fc_date, str) else str(fc_date)
                    logger.debug(f'Processing fc_date for st_id {st_id}, fc_id {fc_id}: {repr(fc_date_str)}')
                    forecast_date = datetime.strptime(fc_date_str, self.DATE_FORMAT)
                    if timezone.is_naive(forecast_date):
                        forecast_date = timezone.make_aware(forecast_date, timezone.get_default_timezone())
                except (ValueError, TypeError) as e:
                    logger.error(f'Failed to parse fc_date for st_id {st_id}, fc_id {fc_id}: {repr(fc_date)} - Error: {str(e)}')
                    self.stdout.write(self.style.WARNING(f'Skipping st_id {st_id}, fc_id {fc_id}: Invalid fc_date format: {repr(fc_date)}'))
                    skipped_count += 1
                    continue

                batch.append(WaterLevelForecast(
                    station_id_id=station.pk,
                    forecast_date=forecast_date,
                    water_level=waterlevel
                ))

                if len(batch) >= 1000:
                    try:
                        WaterLevelForecast.objects.using('default').bulk_create(batch)
                        success_count += len(batch)
                        self.stdout.write(self.style.NOTICE(f'Processed batch of {len(batch)} records. Total successful: {success_count}'))
                    except Exception as e:
                        logger.error(f'Failed to bulk create batch: {str(e)}')
                        self.stdout.write(self.style.ERROR(f'Error in batch processing: {str(e)}'))
                        skipped_count += len(batch)
                    batch = []

            if batch:
                try:
                    WaterLevelForecast.objects.using('default').bulk_create(batch)
                    success_count += len(batch)
                    self.stdout.write(self.style.NOTICE(f'Processed final batch of {len(batch)} records. Total successful: {success_count}'))
                except Exception as e:
                    logger.error(f'Failed to bulk create final batch: {str(e)}')
                    self.stdout.write(self.style.ERROR(f'Error in final batch processing: {str(e)}'))
                    skipped_count += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Successfully copied {success_count} records to default database.'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped_count} records due to missing Station entries or invalid fc_date.'))