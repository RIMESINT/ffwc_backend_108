# data_load/flood_report_generator.py

import os
import django
from django.conf import settings
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import defaultdict
import pytz
from django.db.models import Max, Q # Ensure these imports are present for the logic below
from django.utils import timezone

# IMPORTANT: Configure Django settings for standalone execution.
# This block is crucial if you intend to run this script directly,
# but it will be skipped when imported by Django management commands.
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings') # <--- REPLACE 'your_project_name'
    django.setup()

# Import your application's models and serializers
from data_load import models as models
from data_load import serializers as serializers # Assuming you have these

# Define flood level categories (can be moved to a common utils if used elsewhere)
FLOOD_LEVELS = {
    "na": "N/A",
    "normal": "Normal",
    "warning": "Warning",
    "flood": "Flood",
    "severe": "Severe Flood"
}

def safe_convert_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def safe_compare(value, threshold):
    if value is None or threshold is None:
        return False
    try:
        return float(value) > float(threshold)
    except (TypeError, ValueError):
        return False


def calculate_flood_level(water_level, danger_level):
    """Calculates the flood level category based on water level and danger level."""
    if danger_level is None or water_level is None or water_level < 0:
        return "na"
    elif water_level >= danger_level + 1:
        return "severe"
    elif water_level >= danger_level:
        return "flood"
    elif water_level >= danger_level - 0.5:
        return "warning"
    else:
        return "normal"


def get_alert_level(alert_type):
    """Map alert types to severity levels"""
    alert_type = alert_type.lower()
    if "severe" in alert_type:
        return 3
    elif "flood" in alert_type:
        return 2
    elif "warning" in alert_type:
        return 2
    return 1

def generate_text_summary(metadata, current, trends, recommendations):
    """Generate human-readable text summary"""
    summary = f"## Flood Alert Summary ({metadata['request_date']})\n\n"
    summary += "### **Observed Flood Conditions**\n"
    summary += f"- **Severe Flooding (🔴 Level 3):** {', '.join(current['severe_flood']) or 'None'}\n"
    summary += f"- **Moderate Flooding (🟠 Level 2):** {', '.join(current['moderate_flood']) or 'None'}\n"
    summary += f"- **Normal Conditions (🟢 Level 1):** All other districts\n\n"
    summary += f"### **Forecast ({', '.join(metadata['forecast_dates'])})**\n"
    summary += f"- **Persisting Severe Floods:** {', '.join(trends['persisting_severe']) or 'None'}\n"
    worsening = [item['district'] for item in trends['worsening']]
    summary += f"- **Worsening Conditions:** {', '.join(worsening) or 'None'}\n"
    new_alerts = [item['district'] for item in trends['new_alerts']]
    summary += f"- **New Alerts:** {', '.join(new_alerts) or 'None'}\n\n"
    summary += "### **Recommendations**\n"
    for rec in recommendations:
        if rec['level'] == 'critical':
            summary += f"🚨 **Critical Alert:** {rec['message']}\n"
        elif rec['level'] == 'warning':
            summary += f"⚠️ **Warning:** {rec['message']}\n"
        else:
            summary += f"ℹ️ **Information:** {rec['message']}\n"
    summary += f"\n> Generated on {metadata['generated_at']} | Source: FFWC"
    return summary


# --- Data Retrieval Helper Functions (Direct DB Access) ---

def get_stations_data():
    queryset = models.Station.objects.all().order_by('station_id')
    serializer = serializers.StationsEndpointSerializer(queryset, many=True)
    return serializer.data

def get_recent_observed_data():
    try:
        latest_record = models.WaterLevelObservation.objects.latest('observation_date')
        entry_date_time = latest_record.observation_date
    except models.WaterLevelObservation.DoesNotExist:
        return {}

    one_day_ago = entry_date_time - timedelta(days=1)
    observed_values_dict = defaultdict(list)

    observations = models.WaterLevelObservation.objects.filter(
        observation_date__gte=one_day_ago
    ).values('station_id', 'observation_date', 'water_level').order_by('station_id', 'observation_date')

    for result in observations:
        st_id = result['station_id']
        wl_date = result['observation_date'].strftime('%Y-%m-%d %H')
        water_level = f"{result['water_level']:.2f}"
        observed_values_dict[st_id].append({wl_date: water_level})
    return dict(observed_values_dict)

def get_trends_data():
    try:
        latest_record = models.WaterLevelObservation.objects.latest('observation_date')
        entry_date_time = latest_record.observation_date
    except models.WaterLevelObservation.DoesNotExist:
        return {}

    d2 = entry_date_time - timedelta(days=2)
    water_level_date_dict = defaultdict(list)
    water_level_values_dict = defaultdict(list)
    station_value_diff_by_hour = {}

    observations = models.WaterLevelObservation.objects.filter(
        observation_date__gte=d2
    ).values('station_id', 'observation_date', 'water_level').order_by('station_id', '-observation_date')

    for result in observations:
        st_id = result['station_id']
        water_level_date_dict[st_id].append(result['observation_date'])
        water_level_values_dict[st_id].append(float(result['water_level']))

    for st_id in water_level_date_dict.keys():
        dates = water_level_date_dict[st_id]
        values = water_level_values_dict[st_id]
        length = len(dates)

        if length < 2:
            station_value_diff_by_hour[st_id] = {'wl_date': [3, 24], 'waterlevel': ['na', 'na']}
            continue

        latest_date = dates[0]
        latest_value = values[0]
        value_3h = 'na'
        value_24h = 'na'

        for i in range(1, length):
            date_diff = latest_date - dates[i]
            hours_diff = date_diff.total_seconds() / 3600

            if value_3h == 'na' and abs(hours_diff - 3) <= 1:
                value_3h = round(latest_value - values[i], 4)
            if value_24h == 'na' and abs(hours_diff - 24) <= 1:
                value_24h = round(latest_value - values[i], 4)

            if value_3h != 'na' and value_24h != 'na':
                break

        station_value_diff_by_hour[st_id] = {
            'wl_date': [3, 24],
            'waterlevel': [value_3h, value_24h]
        }
    return dict(station_value_diff_by_hour)

def get_rainfall_data():
    latest_entries = models.RainfallObservation.objects.values('station_id').annotate(
        latest_observation_date=Max('observation_date')
    )
    conditions = [Q(station_id=entry['station_id'], observation_date=entry['latest_observation_date']) for entry in latest_entries]
    if not conditions:
        return []
    combined_condition = conditions[0]
    for condition in conditions[1:]:
        combined_condition |= condition
    queryset = models.RainfallObservation.objects.filter(combined_condition).select_related('station_id', 'station_id__basin')

    rainfall_details = []
    local_tz = pytz.timezone('Asia/Dhaka')
    for rain_obs in queryset:
        timestamp_utc = rain_obs.observation_date
        timestamp_local = timestamp_utc.astimezone(local_tz)
        date_str = timestamp_local.strftime("%Y-%m-%d")
        time_str = timestamp_local.strftime("%H:%M")
        now_utc = datetime.now(pytz.utc)
        time_diff = now_utc - timestamp_utc
        hours_ago = time_diff.total_seconds() // 3600
        time_ago = f"{int(hours_ago)} hours ago" if hours_ago >= 0 else "future"

        rainfall_details.append({
            "st_id": rain_obs.station_id.id,
            "total_rainfall": float(rain_obs.rainfall),
            "latest_date": timestamp_utc.isoformat().replace('+00:00', 'Z'),
            "name": rain_obs.station_id.name if rain_obs.station_id else None,
            "division": rain_obs.station_id.division if rain_obs.station_id else None,
            "district": rain_obs.station_id.district if rain_obs.station_id else None,
            "upazilla": rain_obs.station_id.upazilla if rain_obs.station_id else "N/A",
            "basin": rain_obs.station_id.basin.name if rain_obs.station_id and rain_obs.station_id.basin else "N/A",
            "rainfall": float(rain_obs.rainfall),
            "date": date_str,
            "time": time_str,
            "time_ago": time_ago,
        })
    return rainfall_details


def get_seven_days_observed_waterlevel_by_station(station_id):
    local_tz = pytz.timezone('Asia/Dhaka')
    utc = pytz.UTC
    try:
        get_last_update_time = models.WaterLevelObservation.objects.filter(
            station_id__station_id=station_id
        ).order_by('-observation_date').values_list('observation_date', flat=True).first()

        if not get_last_update_time:
            return []
        get_last_update_time = get_last_update_time.astimezone(utc)
        database_time = get_last_update_time.replace(hour=6, minute=0, second=0, microsecond=0)
        new_database_time = database_time - timedelta(days=7)
        queryset = models.WaterLevelObservation.objects.filter(
            station_id__station_id=station_id,
            observation_date__gte=new_database_time
        ).order_by('observation_date').select_related('station_id')
        data = []
        for obs in queryset:
            data.append({
                "st_id": obs.station_id.station_id,
                "wl_date": obs.observation_date.astimezone(local_tz).isoformat(),
                "waterlevel": float(obs.water_level)
            })
        return data
    except Exception as e:
        print(f"Error fetching 7-day observed for station {station_id}: {str(e)}")
        return []

def get_seven_days_forecast_waterlevel_by_station(station_id):
    local_tz = pytz.timezone('Asia/Dhaka')
    utc = pytz.UTC
    try:
        get_last_update_time = models.WaterLevelForecast.objects.filter(
            station_id__station_id=station_id
        ).order_by('-forecast_date').values_list('forecast_date', flat=True).first()

        if not get_last_update_time:
            return []
        get_last_update_time = get_last_update_time.astimezone(utc)
        database_time = get_last_update_time - timedelta(days=9)
        queryset = models.WaterLevelForecast.objects.filter(
            station_id__station_id=station_id,
            forecast_date__gte=database_time
        ).order_by('forecast_date')
        data = []
        for fc in queryset:
            data.append({
                "st_id": fc.station_id.station_id,
                "fc_date": fc.forecast_date.astimezone(local_tz).isoformat(),
                "waterlevel": float(fc.water_level)
            })
        return data
    except Exception as e:
        print(f"Error fetching 7-day forecast for station {station_id}: {str(e)}")
        return []

def process_station(station):
    station_id = station['id']
    observed = get_seven_days_observed_waterlevel_by_station(station_id) or []
    forecast = get_seven_days_forecast_waterlevel_by_station(station_id) or []
    max_observed = 0
    max_observed_date = "N/A"
    min_observed = float('inf')
    min_observed_date = "N/A"
    
    if observed and isinstance(observed, list):
        for entry in observed:
            if isinstance(entry, dict) and "waterlevel" in entry:
                try:
                    level = safe_convert_float(entry["waterlevel"])
                    wl_date = entry.get("wl_date")
                    if wl_date:
                        try:
                            dt = datetime.fromisoformat(wl_date)
                            date_str = dt.strftime("%Y-%m-%d %H:%M")
                        except ValueError:
                            date_str = wl_date
                    else:
                        date_str = "N/A"
                    if level > max_observed:
                        max_observed = level
                        max_observed_date = date_str
                    if level < min_observed:
                        min_observed = level
                        min_observed_date = date_str
                except (ValueError, TypeError):
                    continue
    max_forecast = 0
    forecast_peak = "N/A"
    forecast_date = "N/A"
    if forecast and isinstance(forecast, list):
        for entry in forecast:
            if isinstance(entry, dict) and "waterlevel" in entry:
                try:
                    level = safe_convert_float(entry["waterlevel"])
                    fc_date = entry.get("fc_date")
                    if fc_date:
                        try:
                            dt = datetime.fromisoformat(fc_date)
                            date_str = dt.strftime("%Y-%m-%d %H:%M")
                        except ValueError:
                            date_str = fc_date
                    else:
                        date_str = "N/A"
                    if level > max_forecast:
                        max_forecast = level
                        forecast_peak = level
                        forecast_date = date_str
                except (ValueError, TypeError):
                    continue
    danger_level = safe_convert_float(station.get('dl'), float('inf'))
    return {
        "id": station_id,
        "name": station.get('station'),
        "river": station.get('river'),
        "division": station.get('division'),
        "district": station.get('district'),
        "upazilla": station.get('upazilla', 'N/A'),
        "danger_level": danger_level,
        "max_observed": max_observed,
        "max_observed_date": max_observed_date,
        "min_observed": min_observed if min_observed != float('inf') else 0,
        "min_observed_date": min_observed_date,
        "max_forecast": max_forecast,
        "forecast_peak": forecast_peak,
        "forecast_date": forecast_date,
        "above_danger": safe_compare(max_forecast, danger_level),
        "current_level": station.get('current_level', 'N/A'),
        "trend": station.get('trend', 'unknown')
    }

def fetch_core_datasets_direct():
    print("Fetching core datasets directly from DB...")
    return {
        "stations": get_stations_data(),
        "recent_observed": get_recent_observed_data(),
        "trends": get_trends_data(),
        "rainfall": get_rainfall_data()
    }

def process_datasets(datasets):
    current_levels = {}
    if datasets["recent_observed"]:
        for station_id_str, observations in datasets["recent_observed"].items():
            try:
                station_id = int(station_id_str)
                if observations and isinstance(observations, list) and observations:
                    last_obs = observations[-1]
                    if isinstance(last_obs, dict):
                        timestamp, level_str = next(iter(last_obs.items()))
                    else:
                        timestamp, level_str = last_obs[0], last_obs[1]
                    current_levels[station_id] = safe_convert_float(level_str)
            except (ValueError, TypeError, IndexError) as e:
                print(f"Error processing recent_observed for station {station_id_str}: {str(e)}")
                continue

    trends = {}
    if datasets["trends"]:
        for station_id_str, trend_data in datasets["trends"].items():
            try:
                station_id = int(station_id_str)
                if isinstance(trend_data, dict):
                    waterlevels = [safe_convert_float(wl) for wl in trend_data.get("waterlevel", [])]
                    if len(waterlevels) >= 2:
                        if waterlevels[-1] > waterlevels[-2]:
                            trends[station_id] = "rising"
                        elif waterlevels[-1] < waterlevels[-2]:
                            trends[station_id] = "falling"
                        else:
                            trends[station_id] = "stable"
                    else:
                        trends[station_id] = "insufficient data"
            except (ValueError, TypeError) as e:
                print(f"Error processing trends for station {station_id_str}: {str(e)}")
                trends[station_id] = "unknown"

    stations = []
    if datasets["stations"]:
        for station in datasets["stations"]:
            station_id = station['id']
            stations.append({
                **station,
                "current_level": current_levels.get(station_id, "N/A"),
                "trend": trends.get(station_id, "unknown")
            })

    rainfall_details = datasets["rainfall"]

    rainfall_summary = {
        "max": 0, "min": 0, "avg": 0, "max_location": {}, "min_location": {}, "heavy_rain": []
    }
    if rainfall_details:
        valid_rain = [r for r in rainfall_details if isinstance(r["rainfall"], (int, float))]
        if valid_rain:
            max_rain = max(valid_rain, key=lambda x: x["rainfall"])
            min_rain = min(valid_rain, key=lambda x: x["rainfall"])
            rainfall_summary = {
                "max": max_rain["rainfall"],
                "min": min_rain["rainfall"],
                "avg": sum(r["rainfall"] for r in valid_rain) / len(valid_rain),
                "max_location": max_rain,
                "min_location": min_rain,
                "heavy_rain": sorted(
                    [r for r in valid_rain if r["rainfall"] >= 50],
                    key=lambda x: x["rainfall"],
                    reverse=True
                )
            }

    station_details = []
    if stations:
        print(f"Fetching 7-day data for {len(stations)} stations in parallel...")
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(process_station, station): station for station in stations}
            for i, future in enumerate(as_completed(futures)):
                try:
                    result = future.result()
                    if result:
                        station_details.append(result)
                    if (i+1) % 10 == 0:
                        print(f"Processed {i+1}/{len(stations)} stations")
                except Exception as e:
                    print(f"Error processing station in thread pool: {str(e)}")
                    continue

    critical_stations = [s for s in station_details if s["above_danger"]]
    top_observed = sorted(station_details, key=lambda x: x["max_observed"], reverse=True)[:5]
    
    return {
        "station_details": station_details,
        "rainfall_details": rainfall_details,
        "rainfall_summary": rainfall_summary,
        "critical_stations": critical_stations,
        "top_observed": top_observed
    }

def get_district_flood_alerts_direct(target_date_str):
    """
    Fetches and processes district-level flood alerts directly from the database.
    This function replicates the logic of the 'district-flood-alerts-observed-forecast-by-observed-dates' API endpoint.
    """
    try:
        start_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        print(f"Processing flood alerts for start date: {start_date}")
    except ValueError:
        print(f"Error: Invalid date format: {target_date_str}. Use YYYY-MM-DD.")
        return {"error": "Invalid date format"}, 400

    stations = models.Station.objects.filter(
        district__isnull=False,
        danger_level__isnull=False,
        station_id__isnull=False
    ).exclude(
        district=''
    ).values('station_id', 'name', 'district', 'danger_level')

    if not stations:
        print("No valid station data found with non-null district and danger_level")
        return {"error": "No valid station data found."}, 500

    print(f"Found {len(stations)} valid stations")

    latest_forecast = models.WaterLevelForecast.objects.aggregate(Max('forecast_date'))
    latest_forecast_date = latest_forecast['forecast_date__max']
    print(f"Latest forecast date: {latest_forecast_date}")

    result = []

    max_days = 7
    if latest_forecast_date:
        forecast_end_date = latest_forecast_date.date()
        forecast_start_date = start_date + timedelta(days=1)
        days_available = (forecast_end_date - forecast_start_date).days + 1
        max_forecast_days = min(6, max(0, days_available))
        max_days = min(max_days, 1 + max_forecast_days)
    else:
        max_days = 1
        print("No forecast data available, limiting to observed data")

    for day_offset in range(max_days):
        current_date = start_date + timedelta(days=day_offset)
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
        day_start = timezone.make_aware(day_start)
        day_end = timezone.make_aware(day_end)
        
        print(f"Processing day {day_offset}: {day_start} to {day_end}")

        district_alerts = defaultdict(lambda: {"severe": 0, "flood": 0, "warning": 0, "normal": 0, "na": 0})

        if day_offset == 0:
            try:
                latest_data = models.WaterLevelObservation.objects.filter(
                    observation_date__range=(day_start, day_end),
                    station_id__isnull=False,
                    station_id__station_id__in=[s['station_id'] for s in stations]
                ).values('station_id__station_id').annotate(
                    max_waterlevel=Max('water_level')
                ).values('station_id__station_id', 'max_waterlevel')
            except Exception as e:
                print(f"Error fetching observed data: {str(e)}")
                latest_data = []
        else:
            latest_data = models.WaterLevelForecast.objects.filter(
                forecast_date__range=(day_start, day_end),
                forecast_date__hour=6,
                station_id__isnull=False,
                station_id__station_id__in=[s['station_id'] for s in stations]
            ).values('station_id__station_id').annotate(
                max_waterlevel=Max('water_level')
            ).values('station_id__station_id', 'max_waterlevel')

        print(f"Found {len(latest_data)} data records for {current_date}")

        data_dict = {item['station_id__station_id']: item for item in latest_data}

        for station in stations:
            station_id = station['station_id']
            district_name = station['district'].lower().strip()
            if not district_name:
                continue

            if station_id in data_dict:
                data = data_dict[station_id]
                try:
                    water_level = float(data['max_waterlevel'])
                    danger_level = float(station['danger_level'])
                    flood_level = calculate_flood_level(water_level, danger_level)
                    district_alerts[district_name][flood_level] += 1
                except (ValueError, TypeError) as e:
                    print(f"Invalid data for station {station_id}: {str(e)}")
                    district_alerts[district_name]["na"] += 1
            else:
                district_alerts[district_name]["na"] += 1

        daily_alerts = []
        for district, levels in district_alerts.items():
            max_level = "na"
            for level_key in ["severe", "flood", "warning", "normal"]:
                if levels[level_key] > 0:
                    max_level = level_key
                    break
            daily_alerts.append({
                "district": district.capitalize(),
                "alert_type": FLOOD_LEVELS[max_level],
            })

        daily_alerts = sorted(daily_alerts, key=lambda x: x['district'])

        result.append({
            "date": current_date.strftime('%Y-%m-%d'),
            "alerts": daily_alerts
        })

    if not result:
        print("No data available for the specified period")
        return {"warning": "No data available for the specified period"}, 200

    return result, 200

def generate_flood_summary_data(target_date_str):
    """
    Generates the comprehensive flood summary report data.
    This function replaces the entire logic of the original flood_summary view,
    but it now fetches data directly from the DB.
    """
    start_generation_time = time.time()
    print(f"Generating flood summary for {target_date_str}...")

    # Call the direct DB fetching function for district-level alerts
    # This replaces the requests.get() call
    api_data, status_code = get_district_flood_alerts_direct(target_date_str)

    if status_code != 200:
        print(f"Error fetching district alerts: {api_data.get('error', 'Unknown error')}")
        return {"error": api_data.get('error', 'Unknown error fetching district alerts'), "status": status_code}

    current_day = next((day for day in api_data if day['date'] == target_date_str), None)
    if not current_day:
        print(f"No district-level data available for {target_date_str}")
        return {"error": f'No district-level data available for {target_date_str}', "status": 404}

    forecast_dates = []
    current_dt = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    for i in range(1, 4):
        forecast_date = (current_dt + timedelta(days=i)).strftime('%Y-%m-%d')
        forecast_dates.append(forecast_date)

    current_alerts = {
        'severe': [a for a in current_day['alerts'] if get_alert_level(a['alert_type']) == 3],
        'moderate': [a for a in current_day['alerts'] if get_alert_level(a['alert_type']) == 2],
        'normal': [a for a in current_day['alerts'] if get_alert_level(a['alert_type']) == 1]
    }

    forecast_data = {}
    for forecast_date in forecast_dates:
        forecast_day = next((day for day in api_data if day['date'] == forecast_date), None)
        if forecast_day:
            forecast_data[forecast_date] = forecast_day['alerts']

    trends = {
        'persisting_severe': [], 'worsening': [], 'improving': [], 'new_alerts': []
    }

    current_severe = [a['district'] for a in current_alerts['severe']]
    for district in current_severe:
        for date in forecast_dates:
            if date in forecast_data:
                forecast_alert = next((a for a in forecast_data[date] if a['district'] == district), None)
                if forecast_alert and get_alert_level(forecast_alert['alert_type']) == 3:
                    if district not in trends['persisting_severe']:
                        trends['persisting_severe'].append(district)

    for alert in current_day['alerts']:
        district = alert['district']
        current_level = get_alert_level(alert['alert_type'])
        for date in forecast_dates:
            if date in forecast_data:
                forecast_alert = next((a for a in forecast_data[date] if a['district'] == district), None)
                if forecast_alert:
                    forecast_level = get_alert_level(forecast_alert['alert_type'])
                    if forecast_level > current_level:
                        trends['worsening'].append({
                            'district': district,
                            'current_alert': alert['alert_type'],
                            'future_alert': forecast_alert['alert_type'],
                            'forecast_date': date,
                            'change': f"{alert['alert_type']} → {forecast_alert['alert_type']}"
                        })

    all_current_districts = [a['district'] for a in current_day['alerts']]
    for date in forecast_dates:
        if date in forecast_data:
            for alert in forecast_data[date]:
                if alert['district'] not in all_current_districts:
                    alert_level = get_alert_level(alert['alert_type'])
                    if alert_level >= 2:
                        trends['new_alerts'].append({
                            'district': alert['district'],
                            'alert_type': alert['alert_type'],
                            'forecast_date': date,
                            'severity': alert_level
                        })

    recommendations = []
    if current_alerts['severe'] or trends['persisting_severe']:
        districts = list(set([a['district'] for a in current_alerts['severe']] + trends['persisting_severe']))
        recommendations.append({
            'level': 'critical',
            'message': 'Evacuate vulnerable areas immediately; avoid river travel',
            'districts': districts,
            'priority': 1
        })
    if current_alerts['moderate'] or trends['worsening'] or trends['new_alerts']:
        districts = list(set([a['district'] for a in current_alerts['moderate']] +
                             [item['district'] for item in trends['worsening']] +
                             [item['district'] for item in trends['new_alerts']]))
        recommendations.append({
            'level': 'warning',
            'message': 'Prepare emergency supplies; monitor FFWC hourly updates',
            'districts': districts,
            'priority': 2
        })
    recommendations.append({
        'level': 'info',
        'message': 'All residents should monitor FFWC updates at ffwc.gov.bd',
        'districts': 'All districts',
        'priority': 3
    })
    recommendations.sort(key=lambda x: x['priority'])

    metadata = {
        'request_date': target_date_str,
        'forecast_dates': forecast_dates,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data_source': "FFWC Database",
        'total_districts': len(current_day['alerts'])
    }

    text_summary = generate_text_summary(
        metadata,
        {'severe_flood': [a['district'] for a in current_alerts['severe']],
         'moderate_flood': [a['district'] for a in current_alerts['moderate']],
         'normal_conditions': [a['district'] for a in current_alerts['normal']]},
        trends,
        recommendations
    )

    response_data = {
        'metadata': metadata,
        'text_summary': text_summary,
        'current_conditions': {
            'severe_flood': current_alerts['severe'],
            'moderate_flood': current_alerts['moderate'],
            'normal_conditions': current_alerts['normal']
        },
        'forecast_trends': trends,
        'recommendations': recommendations,
        'forecast_data': forecast_data
    }

    processing_duration = time.time() - start_generation_time
    print(f"Flood summary generation for {target_date_str} completed in {processing_duration:.2f} seconds.")
    return response_data

# Note: The __main__ block should generally be avoided in modules intended for import.
# It's here for completeness if you were testing this file directly.
# if __name__ == "__main__":
#     # Example usage:
#     # This will only run if flood_report_generator.py is executed directly.
#     # For a Django project, you'd use the management command.
#     target_date = "2025-07-07" # Example date
#     summary_data = generate_flood_summary_data(target_date)
#     if "error" in summary_data:
#         print(f"Error generating summary: {summary_data['error']}")
#     else:
#         import json
#         print(json.dumps(summary_data, indent=4))