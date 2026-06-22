from datetime import datetime
from django.utils.timezone import make_aware
from data_load.models import Station, WaterLevelObservation

def process_vendor_wl_logic(station_code, from_date, to_date, data_list, mode='fill_missing'):
    try:
        station = Station.objects.get(station_code=station_code)
    except Station.DoesNotExist:
        return False, f"Station {station_code} not found."

    # If mode is 'update', clear existing data in that range first
    if mode == 'update':
        WaterLevelObservation.objects.filter(
            station_id=station,
            observation_date__date__range=[from_date, to_date]
        ).delete()

    count = 0
    for item in data_list:
        # Vendor format: "06-04-2026 12:00:00"
        naive_dt = datetime.strptime(item['datetime'], '%d-%m-%Y %H:%M:%S')
        aware_dt = make_aware(naive_dt)
        
        if mode == 'update':
            WaterLevelObservation.objects.create(
                station_id=station,
                observation_date=aware_dt,
                water_level=item['value']
            )
        else:
            WaterLevelObservation.objects.update_or_create(
                station_id=station,
                observation_date=aware_dt,
                defaults={'water_level': item['value']}
            )
        count += 1
    
    return True, f"Successfully processed {count} records."



# app_user_mobile/services.py

def process_bulk_water_level(data_list, mode='fill_missing'):
    results = []
    processed_count = 0

    for item in data_list:
        st_code = item['station_id']
        dt_str = item['datetime']
        val = item['value']

        try:
            # 1. Find the station
            station = Station.objects.get(station_code=st_code)

            # 2. Parse DateTime
            naive_dt = datetime.strptime(dt_str, '%d-%m-%Y %H:%M:%S')
            aware_dt = make_aware(naive_dt)

            # 3. Handle Mode logic
            if mode == 'update':
                # Remove existing record for this specific timestamp only
                WaterLevelObservation.objects.filter(
                    station_id=station, 
                    observation_date=aware_dt
                ).delete()
                
            # 4. Create or Update
            obj, created = WaterLevelObservation.objects.update_or_create(
                station_id=station,
                observation_date=aware_dt,
                defaults={'water_level': val}
            )
            
            processed_count += 1
            results.append({"station": st_code, "datetime": dt_str, "status": "Success"})

        except Station.DoesNotExist:
            results.append({"station": st_code, "datetime": dt_str, "status": "Failed", "error": "Station not found"})
        except Exception as e:
            results.append({"station": st_code, "datetime": dt_str, "status": "Error", "error": str(e)})

    return True, {"total": processed_count, "details": results}



from data_load.models import RainfallStation, RainfallObservation

def process_bulk_rainfall_data(data_list, mode='fill_missing'):
    results = []
    count = 0

    for item in data_list:
        st_code = item['station_id']
        dt_str = item['datetime']
        val = item['value']

        try:
            # 1. Lookup in RainfallStation table
            station = RainfallStation.objects.get(station_code=st_code)

            # 2. Parse DateTime
            aware_dt = make_aware(datetime.strptime(dt_str, '%d-%m-%Y %H:%M:%S'))

            # 3. Handle Mode
            if mode == 'update':
                RainfallObservation.objects.filter(
                    station_id=station, 
                    observation_date=aware_dt
                ).delete()
            
            # 4. Create or Update Rainfall Record
            RainfallObservation.objects.update_or_create(
                station_id=station,
                observation_date=aware_dt,
                defaults={'rainfall': val} # Field name is 'rainfall'
            )
            count += 1
            results.append({"station": st_code, "datetime": dt_str, "status": "Success"})

        except RainfallStation.DoesNotExist:
            results.append({"station": st_code, "status": "Failed", "error": f"Rainfall Station {st_code} not found"})
        except Exception as e:
            results.append({"station": st_code, "status": "Error", "error": str(e)})

    return True, {"total": count, "details": results}