# Generate reports for past 3 days
# python manage.py generate_flood_report --days=3

# management/commands/generate_flood_report.py
import json
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from data_load.models import FloodReport
from data_load import flood_report_generator_utils

class Command(BaseCommand):
    help = 'Generates and stores flood monitoring reports'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format (default: today)')
        parser.add_argument('--days', type=int, default=0, help='Generate reports for past N days')

    def handle(self, *args, **options):
        target_date = options.get('date') or timezone.now().strftime('%Y-%m-%d')
        days = options['days']
        
        # Create date range if needed
        dates = [target_date]
        if days > 0:
            base_date = datetime.strptime(target_date, '%Y-%m-%d')
            dates = [(base_date - timedelta(days=i)).strftime('%Y-%m-%d') 
                     for i in range(days + 1)]
        
        for date in dates:
            if FloodReport.objects.filter(report_date=date).exists():
                self.stdout.write(f"Report for {date} already exists. Skipping.")
                continue
                
            self.stdout.write(f"Generating report for {date}...")
            start_time = time.time()
            
            try:
                # Fetch and process data
                datasets = flood_report_generator_utils.fetch_core_datasets()
                if not datasets.get("stations"):
                    self.stderr.write(f"Error: Failed to fetch station data for {date}")
                    continue
                    
                processed_data = flood_report_generator_utils.process_datasets(datasets)
                
                # Build report structure
                report = {
                    "metadata": {
                        "title": "Flood Monitoring Report",
                        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "data_period": f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}",
                        "data_source": "FFWC API",
                        "report_date": date
                    },
                    "national_overview": {
                        "monitoring_stations": len(processed_data["station_details"]),
                        "rainfall_gauges": len(processed_data["rainfall_details"]),
                        "critical_stations": len(processed_data["critical_stations"]),
                        "rainfall_summary": processed_data["rainfall_summary"]
                    },
                    "critical_stations": [
                        {**station, "location": f"{station['upazilla']} Upazila, {station['division']}"}
                        for station in processed_data["critical_stations"][:5]
                    ],
                    "high_water_levels": [
                        {**station, "location": f"{station['upazilla']} Upazila, {station['division']}"}
                        for station in processed_data["top_observed"][:5]
                    ]
                }
                
                # Save to database
                FloodReport.objects.create(
                    report_date=date,
                    report_data=report,
                    api_data=datasets,
                    processing_time=time.time() - start_time
                )
                
                self.stdout.write(self.style.SUCCESS(f"Successfully created report for {date}"))
                
            except Exception as e:
                self.stderr.write(f"Error generating report for {date}: {str(e)}")