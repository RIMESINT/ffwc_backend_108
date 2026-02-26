import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# API endpoints
BASE_URL = "https://api.ffwc.gov.bd/data_load/"
ENDPOINTS = {
    "stations": "stations-2025/?format=json",
    "recent_observed": "recent-observed/",
    "trends": "annotate-observed-trend/",
    "rainfall": "observed-rainfall/",
    "observed_7d": "seven-days-observed-waterlevel-by-station/{}/",
    "forecast_7d": "seven-days-forecast-waterlevel-by-station/{}/"
}

def fetch_data(url):
    """Fetch data from API with error handling"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {str(e)}")
        return None

def get_full_url(endpoint, station_id=None):
    """Construct full API URL"""
    path = ENDPOINTS[endpoint]
    if station_id is not None:
        path = path.format(station_id)
    return BASE_URL + path

def safe_compare(value, threshold):
    """Safely compare values handling None and type conversions"""
    if value is None or threshold is None:
        return False
    try:
        # Convert both to float for numerical comparison
        return float(value) > float(threshold)
    except (TypeError, ValueError):
        return False

def safe_convert_float(value, default=0.0):
    """Safely convert value to float with default fallback"""
    try:
        return float(value) if value not in [None, ""] else default
    except (TypeError, ValueError):
        return default

def process_station(station):
    """Process station data including 7-day observed and forecast"""
    station_id = station['id']
    
    # Fetch 7-day data
    observed = fetch_data(get_full_url("observed_7d", station_id)) or []
    forecast = fetch_data(get_full_url("forecast_7d", station_id)) or []
    
    # Process observed data
    max_observed = 0
    max_observed_date = "N/A"
    min_observed = float('inf')
    min_observed_date = "N/A"
    
    if observed and isinstance(observed, list):
        for entry in observed:
            if isinstance(entry, dict) and "waterlevel" in entry:
                try:
                    # Convert waterlevel to float
                    level = safe_convert_float(entry["waterlevel"])
                    
                    # Parse and convert date to local time
                    wl_date = entry.get("wl_date")
                    if wl_date:
                        try:
                            dt = datetime.fromisoformat(wl_date.replace('Z', '+00:00'))
                            # Convert to Bangladesh time (UTC+6)
                            dt_local = dt + timedelta(hours=6)
                            date_str = dt_local.strftime("%Y-%m-%d %H:%M")
                        except:
                            date_str = wl_date
                    else:
                        date_str = "N/A"
                    
                    # Track min/max values
                    if level > max_observed:
                        max_observed = level
                        max_observed_date = date_str
                    if level < min_observed:
                        min_observed = level
                        min_observed_date = date_str
                except (ValueError, TypeError):
                    continue
    
    # Process forecast data
    max_forecast = 0
    forecast_peak = "N/A"
    forecast_date = "N/A"
    if forecast and isinstance(forecast, list):
        for entry in forecast:
            if isinstance(entry, dict) and "waterlevel" in entry:
                try:
                    # Convert waterlevel to float
                    level = safe_convert_float(entry["waterlevel"])
                    
                    # Parse and convert date to local time
                    fc_date = entry.get("fc_date")
                    if fc_date:
                        try:
                            dt = datetime.fromisoformat(fc_date.replace('Z', '+00:00'))
                            # Convert to Bangladesh time (UTC+6)
                            dt_local = dt + timedelta(hours=6)
                            date_str = dt_local.strftime("%Y-%m-%d %H:%M")
                        except:
                            date_str = fc_date
                    else:
                        date_str = "N/A"
                    
                    # Track max forecast
                    if level > max_forecast:
                        max_forecast = level
                        forecast_peak = level
                        forecast_date = date_str
                except (ValueError, TypeError):
                    continue

    # Get danger level safely
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
        "above_danger": safe_compare(max_forecast, danger_level)
    }

# Fetch core datasets
print("Fetching core datasets...")
datasets = {
    "stations": fetch_data(get_full_url("stations")),
    "recent_observed": fetch_data(get_full_url("recent_observed")),
    "trends": fetch_data(get_full_url("trends")),
    "rainfall": fetch_data(get_full_url("rainfall"))
}

# Validate data
if not datasets["stations"]:
    print("Error: Failed to fetch station data. Exiting.")
    exit(1)

# Create lookup dictionaries for current levels
current_levels = {}
if datasets["recent_observed"]:
    for station_id_str, observations in datasets["recent_observed"].items():
        try:
            station_id = int(station_id_str)
            if observations and isinstance(observations, list) and observations:
                # Get last observation (most recent)
                last_obs = observations[-1]
                # Handle different response formats
                if isinstance(last_obs, dict):
                    # Format: [{"2023-01-01T00:00:00Z": "10.5"}]
                    timestamp, level_str = next(iter(last_obs.items()))
                else:
                    # Format: [["2023-01-01T00:00:00Z", "10.5"]]
                    timestamp, level_str = last_obs[0], last_obs[1]
                
                current_levels[station_id] = safe_convert_float(level_str)
        except (ValueError, TypeError, IndexError) as e:
            print(f"Error processing recent_observed for station {station_id_str}: {str(e)}")
            continue

# Create trends lookup
trends = {}
if datasets["trends"]:
    for station_id_str, trend_data in datasets["trends"].items():
        try:
            station_id = int(station_id_str)
            # Extract water levels and calculate trend
            if isinstance(trend_data, dict):
                waterlevels = [safe_convert_float(wl) for wl in trend_data.get("waterlevel", [])]
                if len(waterlevels) >= 2:
                    # Compare last two values to determine trend
                    if waterlevels[-1] > waterlevels[-2]:
                        trends[station_id] = "rising"
                    elif waterlevels[-1] < waterlevels[-2]:
                        trends[station_id] = "falling"
                    else:
                        trends[station_id] = "stable"
                else:
                    trends[station_id] = "insufficient data"
        except (ValueError, TypeError):
            trends[station_id] = "unknown"

# Prepare station list with current data
stations = []
for station in datasets["stations"]:
    station_id = station['id']
    stations.append({
        **station,
        "current_level": current_levels.get(station_id, "N/A"),
        "trend": trends.get(station_id, "unknown")
    })

# Process rainfall data with location details
rainfall_details = []
if datasets["rainfall"] and isinstance(datasets["rainfall"], list):
    for rain in datasets["rainfall"]:
        if isinstance(rain, dict):
            station_id = rain.get("st_id")
            station_name = rain.get("name")
            rainfall = safe_convert_float(rain.get("total_rainfall", 0))
            timestamp = rain.get("latest_date", "N/A")
            
            # Add readable date format
            if timestamp != "N/A":
                try:
                    # Parse ISO format and convert to local time
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    # Convert to Bangladesh time (UTC+6)
                    dt_local = dt + timedelta(hours=6)
                    date_str = dt_local.strftime("%Y-%m-%d")
                    time_str = dt_local.strftime("%H:%M")
                    time_ago = f"{(datetime.utcnow() - dt).seconds // 3600} hours ago"
                except Exception as e:
                    date_str = "N/A"
                    time_str = "N/A"
                    time_ago = "N/A"
            else:
                date_str = "N/A"
                time_str = "N/A"
                time_ago = "N/A"
            
            rainfall_details.append({
                "station_id": station_id,
                "station_name": station_name,
                "division": rain.get("division"),
                "district": rain.get("district"),
                "upazilla": rain.get("upazilla", "N/A"),
                "rainfall": rainfall,
                "date": date_str,
                "time": time_str,
                "time_ago": time_ago,
                "basin": rain.get("basin", "N/A")
            })

# Rainfall analysis
rainfall_summary = {
    "max": 0,
    "min": 0,
    "avg": 0,
    "max_location": {},
    "min_location": {},
    "heavy_rain": []
}

if rainfall_details:
    # Filter valid rainfall values
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

# Fetch 7-day data for all stations in parallel
print(f"Fetching 7-day data for {len(stations)} stations...")
station_details = []
with ThreadPoolExecutor(max_workers=15) as executor:
    futures = {executor.submit(process_station, station): station for station in stations}
    for i, future in enumerate(as_completed(futures)):
        try:
            station_details.append(future.result())
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}/{len(stations)} stations")
        except Exception as e:
            print(f"Error processing station: {str(e)}")
            continue

# Analysis
critical_stations = [s for s in station_details if s["above_danger"]]
top_forecast = sorted(station_details, key=lambda x: x["max_forecast"], reverse=True)[:10]
top_observed = sorted(station_details, key=lambda x: x["max_observed"], reverse=True)[:5]

# Generate report
report = f"""
Bangladesh Flood Forecasting and Warning Centre
COMPREHENSIVE FLOOD MONITORING REPORT
============================================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+6)
Data Period: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}
Data Source: FFWC API

1. NATIONAL OVERVIEW
------------------------------------------------------------
- Monitoring Stations: {len(station_details)}
- Rainfall Gauges: {len(rainfall_details)}
- Critical Stations (Forecasted Above Danger): {len(critical_stations)}

- Rainfall (24h):
  • Maximum: {rainfall_summary['max']} mm at {
      rainfall_summary['max_location'].get('station_name', 'N/A')} ({
      rainfall_summary['max_location'].get('upazilla', 'N/A')}, {
      rainfall_summary['max_location'].get('district', 'N/A')}) - Recorded on {
      rainfall_summary['max_location'].get('date', 'N/A')} at {
      rainfall_summary['max_location'].get('time', 'N/A')} ({
      rainfall_summary['max_location'].get('time_ago', 'N/A')})
      - Basin: {rainfall_summary['max_location'].get('basin', 'N/A')}
  
  • Minimum: {rainfall_summary['min']} mm at {
      rainfall_summary['min_location'].get('station_name', 'N/A')} ({
      rainfall_summary['min_location'].get('upazilla', 'N/A')}, {
      rainfall_summary['min_location'].get('district', 'N/A')}) - Recorded on {
      rainfall_summary['min_location'].get('date', 'N/A')} at {
      rainfall_summary['min_location'].get('time', 'N/A')}
      - Basin: {rainfall_summary['min_location'].get('basin', 'N/A')}
  
  • Average: {rainfall_summary['avg']:.1f} mm

- Heavy Rainfall Events (>50mm):"""

if rainfall_summary.get("heavy_rain"):
    for i, rain in enumerate(rainfall_summary["heavy_rain"][:5], 1):
        report += f"""
  {i}. {rain['rainfall']} mm at {rain['station_name']} ({rain['upazilla']}, {rain['district']})
      - Date: {rain['date']} {rain['time']} ({rain['time_ago']})
      - Basin: {rain.get('basin', 'N/A')}"""
else:
    report += "\n  No significant rainfall events reported"

report += "\n\n2. CRITICAL STATIONS (FORECASTED ABOVE DANGER LEVEL)\n------------------------------------------------------------"

if critical_stations:
    for i, station in enumerate(critical_stations[:5], 1):
        # Safely get all values
        current_level = station.get('current_level', 'N/A')
        trend = station.get('trend', 'unknown')
        
        # Safely calculate above danger difference
        above_diff = station['max_forecast'] - station['danger_level'] if station['danger_level'] != float('inf') else "N/A"
        above_diff_str = f"{above_diff:.2f} m" if isinstance(above_diff, float) else above_diff
        
        report += f"""
{i}. {station['name']} ({station['district']})
    • River: {station['river']}
    • Danger Level: {station['danger_level']:.2f} m
    • Current Level: {current_level} m ({trend})
    • Forecasted Peak: {station['max_forecast']:.2f} m on {station['forecast_date']}
    • Above Danger: {above_diff_str}
    • Location: {station['upazilla']} Upazila, {station['division']}"""
else:
    report += "\nNo stations forecasted above danger level"

report += "\n\n3. TOP STATIONS BY FORECASTED PEAK LEVEL\n------------------------------------------------------------"

for i, station in enumerate(top_forecast, 1):
    status = "⚠️ CRITICAL" if station['above_danger'] else "✅ Stable"
    
    # Handle infinite danger level
    danger_level_str = f"{station['danger_level']:.2f} m" if station['danger_level'] != float('inf') else "N/A"
    
    # Safely get current_level and trend
    current_level = station.get('current_level', 'N/A')
    trend = station.get('trend', 'unknown')
    
    report += f"""
{i}. {station['name']} ({station['district']})
    • Forecasted Peak: {station['max_forecast']:.2f} m ({status}) on {station['forecast_date']}
    • Danger Level: {danger_level_str}
    • Current Level: {current_level} m ({trend})
    • Location: {station['upazilla']} Upazila, {station['division']}
    • Observed Range: {station['min_observed']:.2f}-{station['max_observed']:.2f} m
      (Min: {station['min_observed_date']}, Max: {station['max_observed_date']})"""

report += "\n\n4. RECENT HIGH WATER LEVELS (OBSERVED)\n------------------------------------------------------------"

for i, station in enumerate(top_observed, 1):
    # Safely get current_level and trend
    current_level = station.get('current_level', 'N/A')
    trend = station.get('trend', 'unknown')
    
    report += f"""
{i}. {station['name']} ({station['district']})
    • River: {station['river']}
    • Highest Observed: {station['max_observed']:.2f} m on {station['max_observed_date']}
    • Current Level: {current_level} m ({trend})
    • Location: {station['upazilla']} Upazila, {station['division']}"""

report += f"""
============================================================
Key:
⚠️ CRITICAL - Forecasted above danger level
✅ Stable   - Below danger threshold
============================================================
Note: Forecasts based on 7-day hydrological models
Data updated as of {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+6)
"""

print(report)