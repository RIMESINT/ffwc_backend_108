import time
from datetime import datetime
from django.core.management.base import BaseCommand
from data_load.models import FloodSummaryReport
from data_load.flood_summary_generator_utils import generate_flood_summary_data

class Command(BaseCommand):
    help = 'Generates summary with trace prints for debugging UI values.'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str)
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        date_str = options.get('date') or datetime.now().strftime('%Y-%m-%d')
        self.stdout.write(f"--- Processing {date_str} ---")

        try:
            summary_data = generate_flood_summary_data(date_str)
            if "error" in summary_data:
                self.stderr.write(f"Error: {summary_data['error']}")
                return

            trends = summary_data.get('forecast_trends', {})
            self.stdout.write(self.style.SUCCESS(f"Worsening: {len(trends.get('worsening', []))} | Improving: {len(trends.get('improving', []))}"))

            # DB Update
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            FloodSummaryReport.objects.update_or_create(
                report_date=date_obj,
                defaults={'summary_data': summary_data, 'processing_time': 0}
            )
            self.stdout.write(self.style.SUCCESS("Success! Database record updated."))
        except Exception as e:
            self.stderr.write(f"Critical Failure: {str(e)}")