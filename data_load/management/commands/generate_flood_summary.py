import json
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import logging

# Import the model where the data will be stored
from data_load.models import FloodSummaryReport
# Import the function that generates the data
from data_load.flood_summary_generator_utils import generate_flood_summary_data

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates and stores daily flood summary reports in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Optional: Specify a date (YYYY-MM-DD) for which to generate the report. Defaults to today.'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Optional: Generate reports for the past N days, including the --date specified (or today). Default is 0 (only the specified date/today).'
        )
        # Add a new optional argument to force deletion and re-creation
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the deletion of existing report entries for the specified dates before creating new ones.'
        )

    def handle(self, *args, **options):
        target_date_str = options.get('date')
        num_days = options['days']
        force_update = options['force']  # Get the new --force argument

        # Determine the starting date
        if target_date_str:
            try:
                base_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f"Invalid date format for --date: '{target_date_str}'. Please use YYYY-MM-DD.")
        else:
            base_date = timezone.now().date()  # Current date in local timezone

        # Create a list of dates for which reports should be generated
        dates_to_process = []
        for i in range(num_days + 1):
            date_to_process = base_date - timedelta(days=i)
            dates_to_process.append(date_to_process.strftime('%Y-%m-%d'))

        self.stdout.write(f"Attempting to generate flood summary reports for: {', '.join(dates_to_process)}")

        # --- Implement --force logic from Code 1 ---
        if force_update:
            self.stdout.write(self.style.WARNING(f"The --force flag is enabled. Deleting existing reports for dates: {', '.join(dates_to_process)}..."))

            dates_to_delete = [datetime.strptime(d, '%Y-%m-%d').date() for d in dates_to_process]
            deleted_count, _ = FloodSummaryReport.objects.filter(report_date__in=dates_to_delete).delete()
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} existing report(s)."))
        # -------------------------------------------

        for date_str in dates_to_process:
            report_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Check if a report for this date already exists, but only if --force is NOT used
            if not force_update and FloodSummaryReport.objects.filter(report_date=report_date_obj).exists():
                self.stdout.write(self.style.WARNING(f"Report for {date_str} already exists. Skipping generation. Use --force to overwrite."))
                continue

            self.stdout.write(f"Generating report for {date_str}...")
            start_time = time.time()

            try:
                # Call the function that generates the summary data, matching Code 1's logic
                # to get the LATEST data, not data for a specific date.
                # summary_data = generate_flood_summary_data()
                summary_data = generate_flood_summary_data(target_date_str=date_str)

                if "error" in summary_data:
                    self.stderr.write(self.style.ERROR(f"Failed to generate summary for {date_str}: {summary_data['error']}"))
                    continue

                # Save the generated data to the database
                FloodSummaryReport.objects.create(
                    report_date=report_date_obj,
                    summary_data=summary_data,
                    processing_time=(time.time() - start_time)
                )
                self.stdout.write(self.style.SUCCESS(f"Successfully generated and stored flood summary report for {date_str}."))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An unexpected error occurred while generating report for {date_str}: {e}"))
                logger.exception(f"Error generating flood summary for {date_str}")

        self.stdout.write(self.style.SUCCESS("Flood summary generation process completed."))