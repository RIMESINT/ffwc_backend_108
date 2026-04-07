from django.contrib import admin

from django.urls import path
from django.shortcuts import render, redirect
from django.core.management import call_command
from django.contrib import messages

import time
from django.http import StreamingHttpResponse
from django.utils.html import format_html


from app_user_mobile.models import MobileAuthUser

from data_load.models import Station,RainfallStation
from .models import WaterLevelSync
from .forms import HydroSyncForm,HourlySyncForm
from io import StringIO

from django.conf import settings
import requests
# Adding - by Sajib 

try:
    admin.site.unregister(WaterLevelSync)
except admin.sites.NotRegistered:
    pass


@admin.register(WaterLevelSync)
class WaterLevelSyncAdmin(admin.ModelAdmin):

    list_display = ('station_id', 'observation_date', 'water_level')
    change_list_template = "admin/waterlevel_sync_list.html"

    def get_urls(self):
        urls = super().get_urls()
        return [
            path('execute-sync/', self.admin_site.admin_view(self.sync_view), name='execute-sync'),
            path('execute-hourly-sync/', self.admin_site.admin_view(self.hourly_sync_view), name='execute-hourly-sync'),
        ] + urls


    def hourly_sync_view(self, request):
        if request.method == 'POST':
            form = HourlySyncForm(request.POST)
            if form.is_valid():
                selected_station = form.cleaned_data['station']
                hours = form.cleaned_data['hours']
                mode = form.cleaned_data['mode']
                stations = Station.objects.filter(status=True) if not selected_station else [selected_station]

                def stream_hourly():
                    yield f"DATA:START:{len(stations)}\n"
                    for index, station in enumerate(stations, 1):
                        out = StringIO()
                        call_command('sync_hydro_hourly', f'--{mode}', station_code=station.station_code, hours=hours, stdout=out)
                        yield f"DATA:MSG:{out.getvalue()}\n"
                        yield f"DATA:PROGRESS:{index}\n"
                    yield f"DATA:COMPLETE:Hourly Sync Finished.\n"
                return StreamingHttpResponse(stream_hourly(), content_type='text/plain')
        else:
            form = HourlySyncForm()

        context = {**self.admin_site.each_context(request), 'form': form, 'opts': self.model._meta, 'title': 'Hourly Sync'}
        return render(request, "admin/sync_hydro_form.html", context)

    def sync_view(self, request):
            if request.method == 'POST':
                form = HydroSyncForm(request.POST)
                if form.is_valid():
                    selected_station = form.cleaned_data['station']
                    from_date = form.cleaned_data['from_date'].strftime('%Y-%m-%d')
                    to_date = form.cleaned_data['to_date'].strftime('%Y-%m-%d')
                    mode = form.cleaned_data['mode']

                    if selected_station is None:
                        stations = Station.objects.filter(status=True)
                    else:
                        stations = [selected_station]

                    def stream_output():
                        total = len(stations) 
                        yield f"DATA:START:{total}\n"
                        
                        for index, station in enumerate(stations, 1):
                            try:
                                # We capture the stdout of the command
                                from io import StringIO
                                out = StringIO()
                                call_command(
                                    'sync_hydro_data', 
                                    f'--{mode}', 
                                    station_code=station.station_code, 
                                    from_date=from_date, 
                                    to_date=to_date,
                                    stdout=out # Redirect command output
                                )
                                # Send the output to the browser
                                yield f"DATA:MSG:{out.getvalue()}\n"
                                # Send progress update
                                yield f"DATA:PROGRESS:{index}\n"
                            except Exception as e:
                                yield f"DATA:MSG:Error at {station.name}: {str(e)}\n"
                            
                        yield f"DATA:COMPLETE:Successfully processed {total} stations.\n"

                    # Return a streaming response so the browser stays open
                    return StreamingHttpResponse(stream_output(), content_type='text/plain')

            else:
                form = HydroSyncForm()

            context = self.admin_site.each_context(request)
            context.update({
                'form': form,
                'opts': self.model._meta,
                'title': 'Sync Data from External FFWC API'
            })
            return render(request, "admin/sync_hydro_form.html", context)



from .models import RainfallSync
from .forms import RainfallSyncForm,RainfallHourlySyncForm

@admin.register(RainfallSync)
class RainfallSyncAdmin(admin.ModelAdmin):
    list_display = ('station_id', 'observation_date', 'rainfall')
    change_list_template = "admin/rainfall_sync_list.html"

    def get_urls(self):
            urls = super().get_urls()
            return [
                path('execute-rainfall-sync/', self.admin_site.admin_view(self.sync_view), name='execute-rainfall-sync'),
                path('execute-rainfall-hourly-sync/', self.admin_site.admin_view(self.hourly_sync_view), name='execute-rainfall-hourly-sync'),
            ] + urls

    def hourly_sync_view(self, request):
            if request.method == 'POST':
                # Use the Rainfall specific hourly form here
                form = RainfallHourlySyncForm(request.POST) 
                if form.is_valid():
                    selected_station = form.cleaned_data['station']
                    hours = form.cleaned_data['hours']
                    mode = form.cleaned_data['mode']

                    # Ensure we are filtering RainfallStation
                    stations = RainfallStation.objects.filter(status=True) if not selected_station else [selected_station]

                    def stream_rainfall_hourly():
                        yield f"DATA:START:{len(stations)}\n"
                        for index, station in enumerate(stations, 1):
                            out = StringIO()
                            # Ensure this calls the rainfall hourly command
                            call_command(
                                'sync_rainfall_hourly', 
                                f'--{mode}', 
                                station_code=station.station_code, 
                                hours=hours, 
                                stdout=out
                            )
                            yield f"DATA:MSG:{out.getvalue()}\n"
                            yield f"DATA:PROGRESS:{index}\n"
                        yield f"DATA:COMPLETE:Rainfall Hourly Sync Finished.\n"
                    
                    return StreamingHttpResponse(stream_rainfall_hourly(), content_type='text/plain')
            else:
                # Use the Rainfall specific hourly form here
                form = RainfallHourlySyncForm()

            context = {
                **self.admin_site.each_context(request), 
                'form': form, 
                'opts': self.model._meta, 
                'title': 'Rainfall Hourly Sync'
            }
            return render(request, "admin/sync_hydro_form.html", context)

    def sync_view(self, request):
        if request.method == 'POST':
            form = RainfallSyncForm(request.POST)
            if form.is_valid():
                selected_station = form.cleaned_data['station']
                from_date = form.cleaned_data['from_date'].strftime('%Y-%m-%d')
                to_date = form.cleaned_data['to_date'].strftime('%Y-%m-%d')
                mode = form.cleaned_data['mode']

                stations = RainfallStation.objects.filter(status=True) if not selected_station else [selected_station]

                def stream_rainfall():
                    yield f"DATA:START:{len(stations)}\n"
                    for index, station in enumerate(stations, 1):
                        out = StringIO()
                        call_command('sync_rainfall_data', f'--{mode}', 
                                     station_code=station.station_code, 
                                     from_date=from_date, to_date=to_date, stdout=out)
                        yield f"DATA:MSG:{out.getvalue()}\n"
                        yield f"DATA:PROGRESS:{index}\n"
                    yield f"DATA:COMPLETE:Rainfall Sync Finished.\n"

                return StreamingHttpResponse(stream_rainfall(), content_type='text/plain')
        else:
            form = RainfallSyncForm()

        context = {**self.admin_site.each_context(request), 'form': form, 'opts': self.model._meta, 'title': 'Rainfall Data Sync'}
        return render(request, "admin/sync_hydro_form.html", context)


# Existing Codes before Adding SMS interface

@admin.register(MobileAuthUser)
class MobileAuthUserAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = [
        'mobile_number', 
        'full_name', 
        'is_verified', 
        'created_at'
    ]
    
    # Fields that can be clicked to edit
    list_display_links = ['mobile_number', 'full_name']
    
    # Fields to filter by (right sidebar)
    list_filter = ['is_verified', 'created_at']
    
    # Fields to search in
    search_fields = ['mobile_number', 'first_name', 'last_name']
    
    # Fields to make editable directly from list view
    list_editable = ['is_verified']
    
    # Pagination (show 20 records per page)
    list_per_page = 20
    
    # Order records by most recent first
    ordering = ['-created_at']



from .models import SMSSync
from .forms import SMSSyncForm

@admin.register(SMSSync)
class SMSSyncAdmin(admin.ModelAdmin):


    change_list_template = "admin/sms_sync_list.html"

    # Prevent Django from querying a non-existent table
    def get_queryset(self, request):
        return self.model.objects.none()

    # Prevent the "Total" count query from crashing
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


    def get_urls(self):
        urls = super().get_urls()
        return [path('execute-sms-sync/', self.admin_site.admin_view(self.sms_sync_view), name='execute-sms-sync')] + urls

    def sms_sync_view(self, request):
            if request.method == 'POST':
                form = SMSSyncForm(request.POST)
                if form.is_valid():
                    source = form.cleaned_data['source']
                    df = form.cleaned_data['date_from'].strftime('%Y-%m-%d')
                    dt = form.cleaned_data['date_to'].strftime('%Y-%m-%d')

                    def stream_sms_output():
                        # 1. Immediate yield to prevent 'NoneType' response error
                        yield "DATA:MSG:>>> Initializing Connection...\n"

                        # 2. Fetch total count from Gateway for realistic progress
                        gateway_url = f"{settings.SMS_BASE_URL}/sms/list"
                        payload = {
                            "userid": settings.SMS_USERID,
                            "apikey": settings.SMS_APIKEY,
                            "source": source,
                            "datefrom": df,
                            "dateto": dt
                        }
                        
                        try:
                            resp = requests.post(gateway_url, json=payload, timeout=15)
                            resp_data = resp.json()
                            sms_list = resp_data.get('data', [])
                            total_sms = len(sms_list)
                        except Exception as e:
                            yield f"DATA:MSG:Connection Error to Gateway: {str(e)}\n"
                            yield "DATA:COMPLETE:Sync Failed.\n"
                            return

                        if total_sms == 0:
                            yield "DATA:START:1\n"
                            yield "DATA:MSG:No messages found in this date range.\n"
                            yield "DATA:PROGRESS:1\n"
                            yield "DATA:COMPLETE:Finished.\n"
                            return

                        # 3. Start progress bar with ACTUAL count
                        yield f"DATA:START:{total_sms}\n"

                        # 4. Run the command and capture output
                        out = StringIO()
                        try:
                            # no_color=True removes the [32;1m garbage characters
                            call_command(
                                'sync_sms_data', 
                                source=source, 
                                datefrom=df, 
                                dateto=dt, 
                                stdout=out,
                                no_color=True 
                            )
                            
                            output_content = out.getvalue()
                            current_idx = 0
                            
                            # 5. Parse output line by line to update progress realistically
                            for line in output_content.splitlines():
                                if not line.strip(): continue
                                
                                yield f"DATA:MSG:{line}\n"
                                
                                # Update progress bar whenever a new SMS ID is processed
                                if "[Processing SMS ID:" in line:
                                    current_idx += 1
                                    yield f"DATA:PROGRESS:{current_idx}\n"
                                    
                        except Exception as e:
                            yield f"DATA:MSG:Execution Error: {str(e)}\n"
                        
                        yield f"DATA:COMPLETE:Processed {total_sms} messages.\n"

                    # Return the response immediately
                    response = StreamingHttpResponse(stream_sms_output(), content_type='text/plain')
                    # Optional: Ensure it doesn't get cached
                    response['Cache-Control'] = 'no-cache'
                    return response
            else:
                form = SMSSyncForm()

            context = {
                **self.admin_site.each_context(request), 
                'form': form, 
                'opts': self.model._meta, 
                'title': 'SMS Data Parser & Sync'
            }
            return render(request, "admin/sync_hydro_form.html", context)





