import os
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from data_load.models import (
    FloodMetadata, 
    FloodCurrentCondition,
    FloodForecastTrend,
    FloodRecommendation,
    FloodForecastData
)
import requests
from django.conf import settings

class Command(BaseCommand):
    help = 'Imports flood alert data from FFWC API'
    
    def add_arguments(self, parser):
        parser.add_argument('date', type=str, help='Date in YYYY-MM-DD format to fetch data for')
    
    def handle(self, *args, **options):
        date = options['date']
        api_url = f"https://api.ffwc.gov.bd/data_load/district-flood-alerts-observed-forecast-by-observed-dates/{date}/"
        
        self.stdout.write(f"Fetching data from {api_url}...")
        
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"API request failed: {str(e)}"))
            return
            
        try:
            data = response.json()
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR("Invalid JSON response from API"))
            return
        
        # Save Metadata
        meta = data['metadata']
        try:
            metadata, created = FloodMetadata.objects.update_or_create(
                request_date=meta['request_date'],
                defaults={
                    'forecast_dates': meta['forecast_dates'],
                    'generated_at': datetime.strptime(meta['generated_at'], '%Y-%m-%d %H:%M:%S'),
                    'data_source': meta['data_source'],
                    'total_districts': meta['total_districts'],
                    'text_summary': data.get('text_summary', '')
                }
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error saving metadata: {str(e)}"))
            return

        # Delete old related data if updating
        if not created:
            try:
                metadata.current_conditions.all().delete()
                metadata.forecast_trends.all().delete()
                metadata.recommendations.all().delete()
                metadata.forecast_data.all().delete()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error deleting old data: {str(e)}"))
                return

        # Save Current Conditions
        try:
            for cond_type, districts in data['current_conditions'].items():
                for district in districts:
                    FloodCurrentCondition.objects.create(
                        metadata=metadata,
                        condition_type=cond_type,
                        district=district['district'],
                        alert_type=district['alert_type']
                    )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error saving current conditions: {str(e)}"))
            return

        # Save Forecast Trends
        try:
            for trend_type, trends in data['forecast_trends'].items():
                for trend in trends:
                    FloodForecastTrend.objects.create(
                        metadata=metadata,
                        trend_type=trend_type,
                        district=trend['district'],
                        current_alert=trend['current_alert'],
                        future_alert=trend['future_alert'],
                        forecast_date=trend['forecast_date'],
                        change=trend['change']
                    )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error saving forecast trends: {str(e)}"))
            return

        # Save Recommendations
        try:
            for rec in data['recommendations']:
                FloodRecommendation.objects.create(
                    metadata=metadata,
                    level=rec['level'],
                    message=rec['message'],
                    districts=rec['districts'],
                    priority=rec['priority']
                )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error saving recommendations: {str(e)}"))
            return

        # Save Forecast Data
        try:
            for date_str, districts in data['forecast_data'].items():
                for district in districts:
                    FloodForecastData.objects.create(
                        metadata=metadata,
                        forecast_date=date_str,
                        district=district['district'],
                        alert_type=district['alert_type']
                    )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error saving forecast data: {str(e)}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Successfully {'imported' if created else 'updated'} data for {meta['request_date']}"
        ))