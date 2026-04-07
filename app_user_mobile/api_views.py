import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import process_vendor_wl_logic

@csrf_exempt
def vendor_wl_push_api(request):
    if request.method != 'POST':
        return JsonResponse({"status": "Failed", "message": "POST required"}, status=405)

    try:
        payload = json.loads(request.body)
        
        # Extract fields from vendor JSON
        st_code = payload.get('station_code')
        f_date = payload.get('from_date')
        t_date = payload.get('to_date')
        mode = payload.get('mode', 'fill_missing')
        data = payload.get('data', [])

        if not all([st_code, f_date, t_date, data]):
            return JsonResponse({"status": "Error", "message": "Missing required fields"}, status=400)

        success, message = process_vendor_wl_logic(st_code, f_date, t_date, data, mode)
        
        if success:
            return JsonResponse({"status": "Success", "message": message}, status=201)
        else:
            return JsonResponse({"status": "Failed", "message": message}, status=404)

    except Exception as e:
        return JsonResponse({"status": "Error", "message": str(e)}, status=500)