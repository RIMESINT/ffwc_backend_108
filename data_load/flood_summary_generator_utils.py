import os
import django
import logging
import time
from datetime import datetime, timedelta
from collections import defaultdict
from django.conf import settings
from django.db.models import Max
from django.utils import timezone

# Configure Django if run standalone
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ffwc_django_project.settings')
    django.setup()

from data_load import models

logger = logging.getLogger(__name__)

FLOOD_LEVELS = {
    "na": "N/A",
    "normal": "Normal",
    "warning": "Warning",
    "flood": "Flood",
    "severe": "Severe Flood"
}

# --- HELPER FUNCTIONS ---

def safe_float(value):
    if value is None: return None
    try: return float(value)
    except (ValueError, TypeError): return None

def get_alert_level(alert_type):
    val = str(alert_type).lower()
    if "severe" in val: return 3
    if "flood" in val or "warning" in val: return 2
    if "normal" in val: return 1
    return 0

def calculate_flood_level(water_level, danger_level):
    wl = safe_float(water_level)
    dl = safe_float(danger_level)
    if wl is None or dl is None or wl < 0: return "na"
    if wl >= dl + 1: return "severe"
    if wl >= dl: return "flood"
    if wl >= dl - 0.5: return "warning"
    return "normal"

# --- DATA RETRIEVAL FUNCTIONS ---

def get_historical_obs_trends(hours=48):
    """Calculates observed trends over a window (e.g. 48h) for fallback logic."""
    try:
        latest_record = models.WaterLevelObservation.objects.latest('observation_date')
        now = latest_record.observation_date
        past_limit = now - timedelta(hours=hours)
        
        stations = models.Station.objects.exclude(district='').values('station_id', 'district', 'danger_level')
        dist_history = defaultdict(lambda: {'now': [], 'past': [], 'all_lvls': []})

        observations = models.WaterLevelObservation.objects.filter(
            observation_date__range=(past_limit, now)
        ).order_by('observation_date')

        st_map = {s['station_id']: s for s in stations}
        
        for obs in observations:
            sid = obs.station_id_id
            if sid in st_map:
                dist = st_map[sid]['district'].strip().capitalize()
                lvl = get_alert_level(calculate_flood_level(obs.water_level, st_map[sid]['danger_level']))
                dist_history[dist]['all_lvls'].append(lvl)
                
                if obs.observation_date == now:
                    dist_history[dist]['now'].append(obs.water_level)
                elif obs.observation_date <= past_limit + timedelta(hours=1):
                    dist_history[dist]['past'].append(obs.water_level)

        results = {}
        for dist, data in dist_history.items():
            now_avg = sum(data['now'])/len(data['now']) if data['now'] else 0
            past_avg = sum(data['past'])/len(data['past']) if data['past'] else now_avg
            results[dist] = {
                'diff': now_avg - past_avg,
                'past_lvl': data['all_lvls'][0] if data['all_lvls'] else 1,
                'is_consistently_severe': all(l == 3 for l in data['all_lvls']) if data['all_lvls'] else False
            }
        return results
    except:
        return {}

def get_district_flood_alerts_direct(target_date_str):
    """Core logic to fetch district-wise alert levels from DB."""
    start_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    stations = models.Station.objects.exclude(district='').values('station_id', 'district', 'danger_level')
    result = []
    
    for i in range(4): # Current + 3 Forecast days
        curr_date = start_date + timedelta(days=i)
        d_start = timezone.make_aware(datetime.combine(curr_date, datetime.min.time()))
        d_end = d_start + timedelta(days=1)
        
        if i == 0:
            data = models.WaterLevelObservation.objects.filter(observation_date__range=(d_start, d_end)).values('station_id__station_id').annotate(max_wl=Max('water_level'))
        else:
            data = models.WaterLevelForecast.objects.filter(forecast_date__range=(d_start, d_end), forecast_date__hour=6).values('station_id__station_id').annotate(max_wl=Max('water_level'))
        
        wl_map = {item['station_id__station_id']: item['max_wl'] for item in data}
        dist_alerts = {}
        for s in stations:
            sid, dist = s['station_id'], s['district'].strip().capitalize()
            if sid in wl_map and wl_map[sid] is not None:
                lvl = calculate_flood_level(wl_map[sid], s['danger_level'])
                if dist not in dist_alerts or get_alert_level(FLOOD_LEVELS[lvl]) > get_alert_level(dist_alerts[dist]):
                    dist_alerts[dist] = FLOOD_LEVELS[lvl]
            elif dist not in dist_alerts:
                dist_alerts[dist] = "N/A"

        result.append({
            "date": curr_date.strftime('%Y-%m-%d'),
            "alerts": [{"district": d, "alert_type": l} for d, l in dist_alerts.items()]
        })
    return result

# --- MAIN GENERATOR ---

def generate_flood_summary_data(target_date_str):
    """Processes trends including Persisting Severe and New Alerts."""
    api_data = get_district_flood_alerts_direct(target_date_str)
    current_day = next((d for d in api_data if d['date'] == target_date_str), None)
    if not current_day: return {"error": "No data"}

    history = get_historical_obs_trends(hours=48)
    forecast_dates = [(datetime.strptime(target_date_str, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 4)]
    forecast_data = {d['date']: d['alerts'] for d in api_data if d['date'] in forecast_dates}
    
    trends = {'persisting_severe': [], 'worsening': [], 'improving': [], 'new_alerts': []}

    for alert in current_day['alerts']:
        dist = alert['district']
        c_type = alert['alert_type']
        c_lvl = get_alert_level(c_type)
        
        future_lvls = []
        for date in forecast_dates:
            f_alert = next((x for x in forecast_data.get(date, []) if x['district'] == dist), None)
            if f_alert and f_alert['alert_type'] not in ["N/A", "Normal"]:
                future_lvls.append({'lvl': get_alert_level(f_alert['alert_type']), 'type': f_alert['alert_type'], 'date': date})

        if future_lvls:
            # --- FORECAST LOGIC ---
            highest_f = max(future_lvls, key=lambda x: x['lvl'])
            
            if c_lvl == 3 and highest_f['lvl'] == 3:
                trends['persisting_severe'].append({'district': dist, 'current_alert': c_type, 'future_alert': 'Severe (FC)', 'forecast_date': highest_f['date'], 'change': 'Consistent Severe'})
            elif c_lvl == 1 and highest_f['lvl'] >= 2:
                trends['new_alerts'].append({'district': dist, 'current_alert': 'Normal', 'future_alert': highest_f['type'], 'forecast_date': highest_f['date'], 'change': f'Rising to {highest_f["type"]}'})
            elif highest_f['lvl'] > c_lvl:
                trends['worsening'].append({'district': dist, 'current_alert': c_type, 'future_alert': highest_f['type'], 'forecast_date': highest_f['date'], 'change': f'{c_type} → {highest_f["type"]}'})
            elif highest_f['lvl'] < c_lvl and c_lvl > 1:
                trends['improving'].append({'district': dist, 'current_alert': c_type, 'future_alert': highest_f['type'], 'forecast_date': highest_f['date'], 'change': f'{c_type} → {highest_f["type"]}'})
        else:
            # --- OBSERVED FALLBACK (NO FORECAST) ---
            dist_h = history.get(dist, {})
            diff = dist_h.get('diff', 0)
            past_lvl = dist_h.get('past_lvl', 1)
            
            if c_lvl == 3 and dist_h.get('is_consistently_severe'):
                trends['persisting_severe'].append({'district': dist, 'current_alert': c_type, 'future_alert': 'Severe (OBS)', 'forecast_date': target_date_str, 'change': '48h Consistent Severe'})
            elif past_lvl == 1 and c_lvl >= 2:
                trends['new_alerts'].append({'district': dist, 'current_alert': 'Normal (48h)', 'future_alert': c_type, 'forecast_date': target_date_str, 'change': f'Recent Rise to {c_type}'})
            elif diff > 0.05:
                trends['worsening'].append({'district': dist, 'current_alert': c_type, 'future_alert': 'Rising', 'forecast_date': target_date_str, 'change': f'Observed Rise (+{diff:.2f}m)'})
            elif diff < -0.05 and c_lvl > 1:
                trends['improving'].append({'district': dist, 'current_alert': c_type, 'future_alert': 'Falling', 'forecast_date': target_date_str, 'change': f'Observed Fall (-{abs(diff):.2f}m)'})

    return {
        'metadata': {'request_date': target_date_str, 'forecast_dates': forecast_dates, 'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
        'current_conditions': {
            'severe_flood': [a for a in current_day['alerts'] if get_alert_level(a['alert_type']) == 3],
            'moderate_flood': [a for a in current_day['alerts'] if get_alert_level(a['alert_type']) == 2],
            'normal_conditions': [a for a in current_day['alerts'] if get_alert_level(a['alert_type']) == 1]
        },
        'forecast_trends': trends,
        'forecast_data': forecast_data
    }