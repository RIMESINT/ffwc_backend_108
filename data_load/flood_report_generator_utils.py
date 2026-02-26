# data_load/flood_summary_generator_db.py

import os
import django
from django.conf import settings
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import defaultdict
import pytz
from django.db.models import Max, Q
from django.utils import timezone

# IMPORTANT: Configure Django settings for standalone execution.
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings')
    django.setup()

# Import your application's models (using the new model names)
# NOTE: Assumes these models are available in a 'data_load.models' module.
from data_load.models import Station, WaterLevelObservation, WaterLevelForecast, RainfallObservation


# Define flood level categories
FLOOD_LEVELS = {
    "na": "N/A",
    "normal": "Normal",
    "warning": "Warning",
    "flood": "Flood",
    "severe": "Severe Flood"
}

# Define the specific timezone (Asia/Dhaka, which is UTC+6)
TARGET_TIMEZONE_NAME = 'Asia/Dhaka'
TARGET_TIMEZONE_DHAKA_UTC_PLUS_6 = pytz.timezone(TARGET_TIMEZONE_NAME)

def safe_convert_float(value):
    """Safely converts a value to a float or returns None if conversion fails."""
    if value is None or isinstance(value, str) and value.upper() == 'NA':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def safe_compare(value, threshold):
    """Safely compares a value to a threshold, returning False if either is invalid."""
    if value is None or threshold is None:
        return False
    try:
        return float(value) > float(threshold)
    except (TypeError, ValueError):
        return False

def calculate_flood_level(water_level, danger_level):
    """Calculates the flood level category."""
    if danger_level is None or water_level is None:
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
    # Return 0 for 'N/A' and other unknown types to ensure they're not
    # treated as a valid level for trend comparison
    elif "na" in alert_type:
        return 0
    else:
        return 1

def generate_text_summary(metadata, current, trends, recommendations):
    """Generate human-readable text summary"""
    summary = f"## Flood Alert Summary ({metadata['request_date']})\n\n"
    summary += "### **Observed Flood Conditions**\n"
    summary += f"- **Severe Flooding (🔴 Level 3):** {', '.join(current['severe_flood']) or 'None'}\n"
    summary += f"- **Moderate Flooding (🟠 Level 2):** {', '.join(current['moderate_flood']) or 'None'}\n"
    summary += f"- **Normal Conditions (🟢 Level 1):** All other districts\n\n"
    summary += f"### **Forecast ({', '.join(metadata['forecast_dates'])})**\n"
    
    persisting_severe_msg = ', '.join(trends['persisting_severe']) if trends['persisting_severe'] else 'None reported. Current severe flood conditions are expected to improve or stabilize.'
    worsening_msg = ', '.join([item['district'] for item in trends['worsening']]) if trends['worsening'] else 'None reported. No districts are currently forecasted to worsen into higher flood alert levels.'
    new_alerts_msg = ', '.join([item['district'] for item in trends['new_alerts']]) if trends['new_alerts'] else 'None reported. No new flood alerts (Warning, Flood, Severe) are expected to be issued for unaffected districts.'

    summary += f"- **Persisting Severe Floods:** {persisting_severe_msg}\n"
    summary += f"- **Worsening Conditions:** {worsening_msg}\n"
    summary += f"- **New Alerts:** {new_alerts_msg}\n\n"

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
    queryset = Station.objects.all().order_by('station_id')
    
    stations_data = []
    for station in queryset:
        stations_data.append({
            'id': station.station_id,
            'name': station.name,
            'river': station.river,
            'danger_level': station.danger_level, 
            'division': station.division,
            'district': station.district,
            'upazilla': station.upazilla,
            'union': station.union, 
            'basin': station.basin.name if station.basin else None,
        })
    return stations_data

def get_recent_observed_data():
    try:
        latest_record = WaterLevelObservation.objects.latest('observation_date')
        entry_date_time = latest_record.observation_date
    except WaterLevelObservation.DoesNotExist:
        return {}

    one_day_ago = entry_date_time - timedelta(days=1)
    observed_values_dict = defaultdict(list)

    observations = WaterLevelObservation.objects.filter(
        observation_date__gte=one_day_ago
    ).values('station_id', 'observation_date', 'water_level').order_by('station_id', 'observation_date')

    for result in observations:
        st_id = result['station_id']
        wl_date = result['observation_date'].astimezone(TARGET_TIMEZONE_DHAKA_UTC_PLUS_6).strftime('%Y-%m-%d %H')
        water_level = result['water_level']
        if water_level is not None:
            water_level = f"{water_level:.2f}"
        observed_values_dict[st_id].append({wl_date: water_level})
    return dict(observed_values_dict)

def get_trends_data():
    try:
        latest_record = WaterLevelObservation.objects.latest('observation_date')
        entry_date_time = latest_record.observation_date
    except WaterLevelObservation.DoesNotExist:
        return {}

    d2 = entry_date_time - timedelta(days=2)
    water_level_date_dict = defaultdict(list)
    water_level_values_dict = defaultdict(list)
    station_value_diff_by_hour = {}

    observations = WaterLevelObservation.objects.filter(
        observation_date__gte=d2
    ).values('station_id', 'observation_date', 'water_level').order_by('station_id', '-observation_date')

    for result in observations:
        st_id = result['station_id']
        water_level_date_dict[st_id].append(result['observation_date'])
        converted_level = safe_convert_float(result['water_level'])
        if converted_level is not None:
            water_level_values_dict[st_id].append(converted_level)

    for st_id in water_level_date_dict.keys():
        dates = water_level_date_dict[st_id]
        values = water_level_values_dict[st_id]
        length = len(dates)

        if length < 2:
            station_value_diff_by_hour[st_id] = {'observation_date': [3, 24], 'water_level': ['na', 'na']}
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
            'observation_date': [3, 24],
            'water_level': [value_3h, value_24h]
        }
    return dict(station_value_diff_by_hour)

def get_rainfall_data():
    try:
        latest_entries_raw = RainfallObservation.objects.values('station_id').annotate(
            latest_rf_date=Max('observation_date')
        )
        
        conditions = [Q(station_id=entry['station_id'], observation_date=entry['latest_rf_date']) for entry in latest_entries_raw]
        
        if not conditions:
            return []
        
        combined_condition = conditions[0]
        for condition in conditions[1:]:
            combined_condition |= condition
        
        latest_rainfall_observations = RainfallObservation.objects.filter(combined_condition)
        
        station_ids = [obs.station_id_id for obs in latest_rainfall_observations]
        stations_map = {
            s.station_id: s for s in Station.objects.filter(station_id__in=station_ids).select_related('basin')
        }

        rainfall_details = []
        local_tz = TARGET_TIMEZONE_DHAKA_UTC_PLUS_6
        for rain_obs in latest_rainfall_observations:
            timestamp_utc = rain_obs.observation_date 
            timestamp_local = timestamp_utc.astimezone(local_tz)
            date_str = timestamp_local.strftime("%Y-%m-%d")
            time_str = timestamp_local.strftime("%H:%M")
            now_utc = datetime.now(pytz.utc) 
            time_diff = now_utc - timestamp_utc
            hours_ago = time_diff.total_seconds() // 3600
            time_ago = f"{int(hours_ago)} hours ago" if hours_ago >= 0 else "future"

            station_info = stations_map.get(rain_obs.station_id_id)
            
            if station_info:
                rainfall_details.append({
                    "station_id": rain_obs.station_id_id, 
                    "total_rainfall": float(rain_obs.rainfall) if rain_obs.rainfall is not None else "N/A", 
                    "latest_date": timestamp_utc.isoformat().replace('+00:00', 'Z'),
                    "name": station_info.name, 
                    "division": station_info.division,
                    "district": station_info.district,
                    "upazilla": station_info.upazilla,
                    "basin": station_info.basin.name if station_info.basin else 'N/A', 
                    "rainfall": float(rain_obs.rainfall) if rain_obs.rainfall is not None else "N/A",
                    "date": date_str,
                    "time": time_str,
                    "time_ago": time_ago,
                })
        return rainfall_details
    except Exception as e:
        print(f"Error in get_rainfall_data: {e}")
        return []

def get_seven_days_observed_waterlevel_by_station(station_id):
    local_tz = TARGET_TIMEZONE_DHAKA_UTC_PLUS_6
    utc = pytz.UTC
    try:
        get_last_update_time = WaterLevelObservation.objects.filter(
            station_id=station_id
        ).order_by('-observation_date').values_list('observation_date', flat=True).first()

        if not get_last_update_time:
            return []
        get_last_update_time = get_last_update_time.astimezone(utc)
        database_time = get_last_update_time.replace(hour=6, minute=0, second=0, microsecond=0)
        new_database_time = database_time - timedelta(days=7)
        queryset = WaterLevelObservation.objects.filter(
            station_id=station_id,
            observation_date__gte=new_database_time
        ).order_by('observation_date')

        data = []
        for obs in queryset:
            data.append({
                "station_id": obs.station_id.station_id,
                "observation_date": obs.observation_date.astimezone(local_tz).isoformat(),
                "water_level": float(obs.water_level) if obs.water_level is not None else "N/A",
            })
        return data
    except Exception as e:
        print(f"Error fetching 7-day observed for station {station_id}: {str(e)}")
        return []

def get_seven_days_forecast_waterlevel_by_station(station_id):
    local_tz = TARGET_TIMEZONE_DHAKA_UTC_PLUS_6
    utc = pytz.UTC
    try:
        get_last_update_time = WaterLevelForecast.objects.filter(
            station_id=station_id
        ).order_by('-forecast_date').values_list('forecast_date', flat=True).first()

        if not get_last_update_time:
            return []
        get_last_update_time = get_last_update_time.astimezone(utc)
        database_time = get_last_update_time - timedelta(days=9) 
        queryset = WaterLevelForecast.objects.filter(
            station_id=station_id,
            forecast_date__gte=database_time
        ).order_by('forecast_date')

        data = []
        for fc in queryset:
            data.append({
                "station_id": fc.station_id.station_id,
                "forecast_date": fc.forecast_date.astimezone(local_tz).isoformat(),
                "water_level": float(fc.water_level) if fc.water_level is not None else "N/A",
            })
        return data
    except Exception as e:
        print(f"Error fetching 7-day forecast for station {station_id}: {str(e)}")
        return []

def process_station(station):
    station_id = station['id'] 
    observed = get_seven_days_observed_waterlevel_by_station(station_id) or []
    forecast = get_seven_days_forecast_waterlevel_by_station(station_id) or []
    max_observed = None
    max_observed_date = "N/A"
    min_observed = float('inf')
    min_observed_date = "N/A"
    
    if observed and isinstance(observed, list):
        for entry in observed:
            if isinstance(entry, dict) and "water_level" in entry:
                try:
                    level = safe_convert_float(entry["water_level"])
                    if level is not None:
                        obs_date = entry.get("observation_date")
                        if obs_date:
                            try:
                                dt = datetime.fromisoformat(obs_date).astimezone(TARGET_TIMEZONE_DHAKA_UTC_PLUS_6)
                                date_str = dt.strftime("%Y-%m-%d %H:%M")
                            except ValueError:
                                date_str = obs_date
                        else:
                            date_str = "N/A"
                        if max_observed is None or level > max_observed:
                            max_observed = level
                            max_observed_date = date_str
                        if level < min_observed:
                            min_observed = level
                            min_observed_date = date_str
                except (ValueError, TypeError):
                    continue
    max_forecast = None
    forecast_peak = "N/A"
    forecast_date = "N/A"
    if forecast and isinstance(forecast, list):
        for entry in forecast:
            if isinstance(entry, dict) and "water_level" in entry:
                try:
                    level = safe_convert_float(entry["water_level"])
                    if level is not None:
                        fc_date = entry.get("forecast_date")
                        if fc_date:
                            try:
                                dt = datetime.fromisoformat(fc_date).astimezone(TARGET_TIMEZONE_DHAKA_UTC_PLUS_6)
                                date_str = dt.strftime("%Y-%m-%d %H:%M")
                            except ValueError:
                                date_str = fc_date
                        else:
                            date_str = "N/A"
                        if max_forecast is None or level > max_forecast:
                            max_forecast = level
                            forecast_peak = level
                            forecast_date = date_str
                except (ValueError, TypeError):
                    continue
    danger_level = safe_convert_float(station.get('danger_level'))
    return {
        "id": station_id, 
        "name": station.get('name'), 
        "river": station.get('river'), 
        "division": station.get('division'),
        "district": station.get('district'),
        "upazilla": station.get('upazilla', 'N/A'),
        "danger_level": danger_level,
        "max_observed": max_observed if max_observed is not None else "N/A",
        "max_observed_date": max_observed_date,
        "min_observed": min_observed if min_observed != float('inf') else "N/A",
        "min_observed_date": min_observed_date,
        "max_forecast": max_forecast if max_forecast is not None else "N/A",
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
                    converted_level = safe_convert_float(level_str)
                    if converted_level is not None:
                        current_levels[station_id] = converted_level
            except (ValueError, TypeError, IndexError) as e:
                print(f"Error processing recent_observed for station {station_id_str}: {str(e)}")
                continue

    trends = {}
    if datasets["trends"]:
        for station_id_str, trend_data in datasets["trends"].items():
            try:
                station_id = int(station_id_str)
                if isinstance(trend_data, dict):
                    waterlevels = [safe_convert_float(wl) for wl in trend_data.get("water_level", []) if safe_convert_float(wl) is not None]
                    if len(waterlevels) >= 2:
                        if waterlevels[0] > waterlevels[1]: 
                            trends[station_id] = "rising"
                        elif waterlevels[0] < waterlevels[1]:
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
        "max": "N/A", "min": "N/A", "avg": "N/A", "max_location": {}, "min_location": {}, "heavy_rain": []
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

    valid_station_details = [s for s in station_details if isinstance(s.get("max_observed"), (int, float))]
    critical_stations = [s for s in station_details if safe_compare(s.get("max_forecast"), s.get("danger_level"))]
    top_observed = sorted(valid_station_details, key=lambda x: x["max_observed"], reverse=True)[:5]
    
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
    """
    try:
        start_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        print(f"Processing flood alerts for start date: {start_date}")
    except ValueError:
        print(f"Error: Invalid date format: '{target_date_str}'. Please useYYYY-MM-DD.")
        return {"error": "Invalid date format"}, 400

    stations = Station.objects.filter(
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

    latest_forecast = WaterLevelForecast.objects.aggregate(Max('forecast_date'))
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
        
        day_start = TARGET_TIMEZONE_DHAKA_UTC_PLUS_6.localize(day_start)
        day_end = TARGET_TIMEZONE_DHAKA_UTC_PLUS_6.localize(day_end)
        
        print(f"Processing day {day_offset}: {day_start} to {day_end}")

        district_alerts = defaultdict(lambda: {"severe": 0, "flood": 0, "warning": 0, "normal": 0, "na": 0})

        if day_offset == 0:
            try:
                latest_data = WaterLevelObservation.objects.filter(
                    observation_date__range=(day_start, day_end),
                    station_id__isnull=False,
                    station_id__in=[s['station_id'] for s in stations]
                ).values('station_id').annotate(
                    max_waterlevel=Max('water_level')
                ).values('station_id', 'max_waterlevel')
            except Exception as e:
                print(f"Error fetching observed data: {str(e)}")
                latest_data = []
        else:
            latest_data = WaterLevelForecast.objects.filter(
                forecast_date__range=(day_start, day_end),
                forecast_date__hour=6,
                station_id__isnull=False,
                station_id__in=[s['station_id'] for s in stations]
            ).values('station_id').annotate(
                max_waterlevel=Max('water_level')
            ).values('station_id', 'max_waterlevel')

        print(f"Found {len(latest_data)} data records for {current_date}")

        data_dict = {item['station_id']: item for item in latest_data}

        for station in stations:
            station_id = station['station_id']
            district_name = station['district'].lower().strip()
            if not district_name:
                continue

            if station_id in data_dict:
                data = data_dict[station_id]
                try:
                    water_level = safe_convert_float(data['max_waterlevel'])
                    danger_level = safe_convert_float(station['danger_level'])
                    if water_level is not None and danger_level is not None:
                        flood_level = calculate_flood_level(water_level, danger_level)
                        district_alerts[district_name][flood_level] += 1
                    else:
                        district_alerts[district_name]["na"] += 1
                except (ValueError, TypeError) as e:
                    print(f"Invalid data for station {station_id}: {str(e)}")
                    district_alerts[district_name]["na"] += 1
            else:
                district_alerts[district_name]["na"] += 1

        daily_alerts = []
        for district, levels in district_alerts.items():
            max_level = "na"
            if levels["severe"] > 0:
                max_level = "severe"
            elif levels["flood"] > 0:
                max_level = "flood"
            elif levels["warning"] > 0:
                max_level = "warning"
            elif levels["normal"] > 0:
                max_level = "normal"

            if max_level != "na":
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


def generate_flood_summary_data(target_date_str_unused=None):
    """
    Generates the comprehensive flood summary report data by directly
    accessing the Django database models.
    """
    start_generation_time = time.time()
    print("Generating flood summary based on the latest observed data...")

    try:
        latest_observation = WaterLevelObservation.objects.latest('observation_date')
        latest_observed_date_dt = latest_observation.observation_date.astimezone(TARGET_TIMEZONE_DHAKA_UTC_PLUS_6)
        current_day_str = latest_observed_date_dt.strftime('%Y-%m-%d')
        print(f"Latest observed data date: {current_day_str}")
    except WaterLevelObservation.DoesNotExist:
        print("No water level observations found. Cannot generate summary.")
        return {"error": "No water level observations found to base the summary on.", "status": 500}
    except Exception as e:
        print(f"Error determining latest observed date: {e}")
        return {"error": f"Error determining latest observed date: {e}", "status": 500}

    api_data, status_code = get_district_flood_alerts_direct(current_day_str)

    if status_code != 200:
        print(f"Error fetching district alerts: {api_data.get('error', 'Unknown error')}")
        return {"error": api_data.get('error', 'Unknown error fetching district alerts'), "status": status_code}

    current_day = next((day for day in api_data if day['date'] == current_day_str), None)
    if not current_day:
        print(f"No district-level data available for the determined current day: {current_day_str}")
        return {"error": f'No district-level data available for {current_day_str}', "status": 404}

    forecast_dates = []
    current_dt = datetime.strptime(current_day_str, '%Y-%m-%d').date()
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
            forecast_data[forecast_date] = [a for a in forecast_day['alerts'] if get_alert_level(a['alert_type']) != 0]

    trends = {
        'persisting_severe': [], 'worsening': [], 'improving': [], 'new_alerts': []
    }

    current_severe_districts = {a['district'] for a in current_alerts['severe']}
    for district in current_severe_districts:
        persists_in_forecast = False
        for date in forecast_dates:
            if date in forecast_data:
                forecast_alert = next((a for a in forecast_data[date] if a['district'] == district), None)
                if forecast_alert and get_alert_level(forecast_alert['alert_type']) == 3:
                    persists_in_forecast = True
                    break
        if persists_in_forecast:
            if district not in trends['persisting_severe']:
                trends['persisting_severe'].append(district)
    trends['persisting_severe'].sort()

    worsening_districts_added = set()
    improving_districts_added = set()

    for alert in current_day['alerts']:
        district = alert['district']
        current_level = get_alert_level(alert['alert_type'])
        
        # Only check for trends if the current alert is a valid, non-N/A alert
        if current_level != 0:
            for date in forecast_dates:
                if date in forecast_data:
                    forecast_alert = next((a for a in forecast_data[date] if a['district'] == district), None)
                    
                    if forecast_alert and get_alert_level(forecast_alert['alert_type']) != 0:
                        forecast_level = get_alert_level(forecast_alert['alert_type'])
                        
                        if forecast_level > current_level and district not in worsening_districts_added:
                            worsening_entry = {
                                'district': district,
                                'current_alert': alert['alert_type'],
                                'future_alert': forecast_alert['alert_type'],
                                'forecast_date': date,
                                'change': f"{alert['alert_type']} → {forecast_alert['alert_type']}"
                            }
                            trends['worsening'].append(worsening_entry)
                            worsening_districts_added.add(district)
                        elif forecast_level < current_level and district not in improving_districts_added:
                            improving_entry = {
                                'district': district,
                                'current_alert': alert['alert_type'],
                                'future_alert': forecast_alert['alert_type'],
                                'forecast_date': date,
                                'change': f"{alert['alert_type']} → {forecast_alert['alert_type']}"
                            }
                            trends['improving'].append(improving_entry)
                            improving_districts_added.add(district)
    
    trends['worsening'].sort(key=lambda x: x['district'])
    trends['improving'].sort(key=lambda x: x['district'])

    all_current_districts = {a['district'] for a in current_day['alerts'] if a['alert_type'] != "N/A"}
    new_alerts_districts_added = set()

    for date in forecast_dates:
        if date in forecast_data:
            for alert in forecast_data[date]:
                if alert['district'] not in all_current_districts and \
                   get_alert_level(alert['alert_type']) != 0 and \
                   alert['district'] not in new_alerts_districts_added:
                    alert_level = get_alert_level(alert['alert_type'])
                    if alert_level >= 2:
                        new_alert_entry = {
                            'district': alert['district'],
                            'alert_type': alert['alert_type'],
                            'forecast_date': date,
                            'severity': alert_level
                        }
                        trends['new_alerts'].append(new_alert_entry)
                        new_alerts_districts_added.add(alert['district'])
    trends['new_alerts'].sort(key=lambda x: x['district'])

    recommendations = []
    if current_alerts['severe'] or trends['persisting_severe']:
        districts = list(set([a['district'] for a in current_alerts['severe']] + trends['persisting_severe']))
        recommendations.append({
            'level': 'critical',
            'message': 'Evacuate vulnerable areas immediately; avoid river travel',
            'districts': sorted(districts),
            'priority': 1
        })
    
    moderate_affected_districts = {a['district'] for a in current_alerts['moderate']}
    worsening_affected_districts = {item['district'] for item in trends['worsening']}
    new_alerts_affected_districts = {item['district'] for item in trends['new_alerts']}
    
    all_warning_districts = list(moderate_affected_districts.union(worsening_affected_districts).union(new_alerts_affected_districts))

    if all_warning_districts:
        recommendations.append({
            'level': 'warning',
            'message': 'Prepare emergency supplies; monitor FFWC hourly updates',
            'districts': sorted(all_warning_districts),
            'priority': 2
        })
    
    recommendations.append({
        'level': 'info',
        'message': 'All residents should monitor FFWC updates at ffwc.gov.bd',
        'districts': 'All districts',
        'priority': 3
    })
    recommendations.sort(key=lambda x: x['priority'])

    utc_now = timezone.now()
    generated_at_dhaka_time = utc_now.astimezone(TARGET_TIMEZONE_DHAKA_UTC_PLUS_6)
    generated_at_string = generated_at_dhaka_time.strftime('%Y-%m-%d %H:%M:%S')

    metadata = {
        'request_date': current_day_str,
        'forecast_dates': sorted(forecast_dates),
        'generated_at': generated_at_string,
        'data_source': "FFWC Database",
        'total_districts': len(current_day['alerts'])
    }

    text_summary = generate_text_summary(
        metadata,
        {'severe_flood': sorted([a['district'] for a in current_alerts['severe']]), 
         'moderate_flood': sorted([a['district'] for a in current_alerts['moderate']]), 
         'normal_conditions': sorted([a['district'] for a in current_alerts['normal']])}, 
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
    print(f"Flood summary generation for {current_day_str} completed in {processing_duration:.2f} seconds.")
    return response_data