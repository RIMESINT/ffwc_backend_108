# data_load/utils.py
import pytz
import requests
from datetime import datetime,timedelta
from django.conf import settings
import logging
import csv
from django.http import HttpResponse # Import HttpResponse for export mixin
from django.utils import timezone
logger = logging.getLogger(__name__)

def normalize_datetime(dt):
    """
    Normalizes a timezone-aware datetime object to UTC if USE_TZ is True,
    then converts it back to naive datetime if USE_TZ is False.
    Otherwise, returns it as is.
    """
    if settings.USE_TZ:
        if dt.tzinfo is None:
            # If datetime is naive, make it aware using the default timezone
            tz = pytz.timezone(settings.TIME_ZONE)
            dt = tz.localize(dt, is_dst=None)
            logger.warning(f"Naive datetime localized: {dt} (auto-localized)")
        return dt.astimezone(pytz.utc).replace(tzinfo=None)
    return dt

class ExportCsvMixin:
    """
    Mixin to add 'Export as CSV' action to Django admin.
    """
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export selected to CSV"





def get_alert_level(alert_type):
    """Map alert types to severity levels"""
    if "severe" in alert_type.lower():
        return 3
    elif "flood" in alert_type.lower() or "warning" in alert_type.lower():
        return 2
    return 1

def generate_flood_summary(api_data, target_date=None):
    """
    Generate flood summary from API response data
    :param api_data: API response (list of daily alerts)
    :param target_date: Target date in YYYY-MM-DD format (default: today)
    :return: Markdown formatted summary
    """
    # Set target date
    target_date = target_date or timezone.now().strftime('%Y-%m-%d')
    
    # Find today's data and forecast data
    today_data = next((d for d in api_data if d['date'] == target_date), None)
    if not today_data:
        return f"⚠️ No data available for {target_date}"
    
    # Get forecast data (next 3 days)
    forecast_days = []
    current_date = datetime.strptime(target_date, '%Y-%m-%d')
    for i in range(1, 4):
        next_date = (current_date + timedelta(days=i)).strftime('%Y-%m-%d')
        forecast_data = next((d for d in api_data if d['date'] == next_date), None)
        if forecast_data:
            forecast_days.append(forecast_data)
    
    # Process current alerts
    current_alerts = {
        3: [a['district'] for a in today_data['alerts'] if get_alert_level(a['alert_type']) == 3],
        2: [a['district'] for a in today_data['alerts'] if get_alert_level(a['alert_type']) == 2],
        1: [a['district'] for a in today_data['alerts'] if get_alert_level(a['alert_type']) == 1]
    }
    
    # Process forecast alerts
    forecast_changes = {
        'persisting': [],
        'worsening': [],
        'new': []
    }
    
    # Identify districts with persistent severe flooding
    severe_districts = current_alerts[3]
    for forecast in forecast_days:
        forecast_severe = [
            a['district'] for a in forecast['alerts'] 
            if get_alert_level(a['alert_type']) == 3 and a['district'] in severe_districts
        ]
        forecast_changes['persisting'] = list(set(forecast_changes['persisting'] + forecast_severe))
    
    # Identify worsening conditions
    for district in current_alerts[1] + current_alerts[2]:
        current_level = 2 if district in current_alerts[2] else 1
        for forecast in forecast_days:
            forecast_alert = next((a for a in forecast['alerts'] if a['district'] == district), None)
            if forecast_alert:
                forecast_level = get_alert_level(forecast_alert['alert_type'])
                if forecast_level > current_level:
                    if district not in forecast_changes['worsening']:
                        forecast_changes['worsening'].append(district)
    
    # Identify new alerts
    all_districts = [a['district'] for a in today_data['alerts']]
    for forecast in forecast_days:
        for alert in forecast['alerts']:
            district = alert['district']
            if get_alert_level(alert['alert_type']) >= 2:
                if (district not in current_alerts[3] and 
                    district not in current_alerts[2] and
                    district not in forecast_changes['new']):
                    forecast_changes['new'].append(district)
    
    # Generate summary
    summary = f"## Flood Alert Summary ({target_date})\n\n"
    
    # Current conditions
    summary += "### **Observed Flood Conditions**\n"
    summary += f"- **Severe Flooding (🔴 Level 3):** {', '.join(current_alerts[3]) or 'None'}\n"
    summary += f"- **Moderate Flooding (🟠 Level 2):** {', '.join(current_alerts[2]) or 'None'}\n"
    summary += f"- **Normal Conditions (🟢 Level 1):** All other districts\n\n"
    
    # Forecast
    if forecast_days:
        forecast_dates = ", ".join([f['date'] for f in forecast_days])
        summary += f"### **Forecast ({forecast_dates})**\n"
        summary += f"- **Persisting Severe Floods:** {', '.join(forecast_changes['persisting']) or 'None'}\n"
        summary += f"- **Worsening Conditions:** {', '.join(forecast_changes['worsening']) or 'None'}\n"
        summary += f"- **New Alerts:** {', '.join(forecast_changes['new']) or 'None'}\n\n"
    else:
        summary += "### **Forecast**\nNo forecast data available\n\n"
    
    # Recommendations
    summary += "### **Recommendations**\n"
    if current_alerts[3] or forecast_changes['persisting']:
        summary += "🚨 **High-Risk Districts (Level 3):** Evacuate vulnerable areas; avoid river travel\n"
    if current_alerts[2] or forecast_changes['worsening'] or forecast_changes['new']:
        summary += "⚠️ **Moderate-Risk Districts (Level 2):** Prepare emergency supplies; monitor hourly updates\n"
    summary += "ℹ️ **All Residents:** Check [ffwc.gov.bd](https://www.ffwc.gov.bd/) for real-time updates\n\n"
    
    # Footer
    summary += f"> Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Next update: 10:00 AM BST"
    
    return summary