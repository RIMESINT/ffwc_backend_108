from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django import forms
from django.shortcuts import render
from django.contrib import messages

from django_celery_results.models import TaskResult, GroupResult


from django.urls import path, reverse 

from django.http import HttpResponseRedirect, JsonResponse 
from celery.result import AsyncResult
from django.conf import settings 


from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from rangefilter.filters import DateRangeFilterBuilder


import os 
import io 
import pandas as pd 
import re 
import logging 
from datetime import datetime 

import csv
import io
from datetime import datetime
import pytz
from django import forms

from django.conf import settings
from django.urls import path, reverse 
from django.http import HttpResponseRedirect, JsonResponse 
from celery.result import AsyncResult,states
from .tasks import process_observations_csv,import_forecast_files,import_experimental_forecast_files 
from .tasks import generate_rainfall_map_task,generate_flood_alerts_task

from .forms import CSVUploadForm, ForecastCsvImportForm 
from .utils import ExportCsvMixin 


from .models import (
    Station, RainfallStation, MonthlyRainfall, WaterLevelObservation,
    WaterLevelForecast, WaterLevelForecastsExperimentals, RainfallObservation,
    FfwcLastUpdateDate
)

from .models import Messages, ScrollerMessages, SecondScrollerMessages
from .models import DistrictFloodAlert,Floodmaps,MonsoonConfig


logger = logging.getLogger(__name__) 


# Set the header for the admin site
admin.site.site_header = 'Forecasters Admin Panel'
admin.site.site_title = 'Forecasters Admin'


try:
    admin.site.unregister(TaskResult)
except admin.sites.NotRegistered:
    pass  # TaskResult was not registered, so no need to unregister

try:
    admin.site.unregister(GroupResult)
except admin.sites.NotRegistered:
    pass  # GroupResult was not registered, so no need to unregister


# Unregister default admin classes
admin.site.unregister(User)
admin.site.unregister(Group)

# Custom User admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'groups')
    search_fields = ('username', 'email')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# Custom Group admin
class CustomGroupAdmin(GroupAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Group, CustomGroupAdmin)


from .models import FloodAlertDisclaimer
from .forms import FloodAlertDisclaimerForm
@admin.register(FloodAlertDisclaimer)
class FloodAlertDisclaimerAdmin(admin.ModelAdmin):
    list_display = ('message', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('message',)
    form = FloodAlertDisclaimerForm

from .forms import MessagesForm
@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ('message', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('message',)
    form = MessagesForm

from .forms import ScrollerMessagesForm
@admin.register(ScrollerMessages)
class ScrollerMessagesAdmin(admin.ModelAdmin):
    list_display = ('message', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('message',)
    form = ScrollerMessagesForm

from .forms import SecondScrollerMessagesForm
@admin.register(SecondScrollerMessages)
class SecondScrollerMessagesAdmin(admin.ModelAdmin):
    list_display = ('message', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('message',)
    form = SecondScrollerMessagesForm


    
# Form for CSV upload
class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='Upload CSV File')

# Custom Admin for Station
@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('station_id', 'name', 'station_code', 'river', 'basin', 'status')
    list_filter = ('station_id', 'status', 'basin', 'division', 'district')
    search_fields = ('name', 'station_id', 'station_code', 'river')
    list_per_page = 25
    fieldsets = (
        ('Basic Info', {'fields': ('station_id', 'station_code', 'bwdb_id', 'name', 'name_bn')}),
        ('Location', {'fields': ('latitude', 'longitude', 'division', 'district', 'upazilla', 'union')}),
        ('River Info', {'fields': ('river', 'river_bn', 'river_chainage', 'basin')}),
        ('Water Level Info', {'fields': ('danger_level', 'highest_water_level', 'highest_water_level_date')}),
        ('Forecast Settings', {'fields': ('five_days_forecast', 'ten_days_forecast', 'monsoon_station', 'pre_monsoon_station', 'dry_period_station')}),
        ('Other', {'fields': ('status', 'station_order', 'medium_range_station', 'experimental', 'ffdata_header')}),
    )

# Custom Admin for RainfallStation
@admin.register(RainfallStation)
class RainfallStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'station_id', 'station_code', 'basin', 'status')
    list_filter = ('status', 'basin', 'division', 'district')
    search_fields = ('name', 'station_id', 'station_code')
    list_per_page = 25
    fieldsets = (
        ('Basic Info', {'fields': ('station_id', 'station_code', 'name', 'name_bn')}),
        ('Location', {'fields': ('latitude', 'longitude', 'division', 'division_bn', 'district', 'district_bn', 'upazilla', 'upazilla_bn')}),
        ('Other', {'fields': ('basin', 'header', 'unit', 'status')}),
    )

# Custom Admin for MonthlyRainfall
@admin.register(MonthlyRainfall)
class MonthlyRainfallAdmin(admin.ModelAdmin):
    list_display = ('station_id', 'month_name', 'max_rainfall', 'normal_rainfall', 'min_rainfall')
    list_filter = ('month_name',)
    search_fields = ('station_id', 'month_name')
    list_per_page = 25
    fieldsets = (
        ('Basic Info', {'fields': ('station_id', 'month_serial', 'month_name')}),
        ('Rainfall Data', {'fields': ('max_rainfall', 'normal_rainfall', 'min_rainfall', 'unit')}),
    )

# Custom Admin for WaterLevelObservation
from .filters import WaterLevelDateFilter,StationNameFilter
@admin.register(WaterLevelObservation)
class WaterLevelObservationAdmin(admin.ModelAdmin):

    list_display = ('display_station_id', 'station_name', 'station_code', 'observation_date', 'water_level')
    list_filter = (('observation_date', WaterLevelDateFilter), 'station_id__name','station_id')
    # list_filter = (('observation_date', DateRangeFilter),StationNameFilter,'station_id')
    # list_filter = (WaterLevelDateFilter, StationNameFilter, 'station_id')

    search_fields = ('station_id__name',)
    ordering = ('station_id_id',)
    list_per_page = 25
    fieldsets = (
        ('Observation Info', {'fields': ('station_id', 'observation_date', 'water_level')}),
    )

    class Media:
            js = (
                'admin/js/vendor/jquery/jquery.min.js',
                'admin/js/jquery.init.js',
                'admin/js/core.js',
                'admin/js/calendar.js',
                'admin/js/admin/DateTimeShortcuts.js',
            )
            css = {
                'all': ('admin/css/widgets.css',)
            }


    change_list_template = 'admin/data_load/waterlevelobservation/change_list.html'




    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv_view), name='waterlevelobservation-upload-csv'),
            # New URL for JavaScript to poll for task status
            path('task-status/<str:task_id>/', self.admin_site.admin_view(self.task_status_view), name='task_status'),
        ]
        return custom_urls + urls

    def upload_csv_view(self, request):
        if request.method == 'POST':
            form = CSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                # Read the CSV content as a string to pass to Celery
                csv_data_string = csv_file.read().decode('utf-8')

                # Dispatch the Celery task
                # Pass the CSV data string and the current timezone to the task
                task = process_observations_csv.delay(csv_data_string, settings.TIME_ZONE)

                messages.info(request, f"CSV upload started in the background. Task ID: {task.id}.")
                
                # Redirect to the same upload page, passing the task_id in the URL
                # The JavaScript on the page will pick this up to start polling
                # return HttpResponseRedirect(self.get_admin_url('upload-csv') + f'?task_id={task.id}')
                return HttpResponseRedirect(reverse('admin:waterlevelobservation-upload-csv') + f'?task_id={task.id}')
            else:
                messages.error(request, 'Please correct the error below.')
        else: # GET request
            form = CSVUploadForm()

        context = self.admin_site.each_context(request)
        # context['title'] = 'Upload Observations CSV'
        context['form'] = form
        context['opts'] = self.model._meta
        
        # Pass the task_id to the template if it's present in GET parameters
        task_id = request.GET.get('task_id')
        if task_id:
            context['task_id'] = task_id
            context['task_status_url_name'] = 'admin:task_status'
        
        return render(request, 'admin/csv_upload.html', context)


    # def task_status_view(self, request, task_id):
    #     """
    #     API endpoint for JavaScript to poll for task progress.
    #     """
    #     result = AsyncResult(task_id) # Get the Celery task result object
        
    #     response_data = {
    #         'state': result.state, # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    #         'message': '',
    #         'percent': 0,
    #         'current': 0,
    #         'total': 0,
    #         'status_url': reverse('admin:task_status', args=[task_id])
    #     }

    #     # ONLY attempt to update from result.info if it is actually a dictionary.
    #     if isinstance(result.info, dict):
    #         # If it's a dict, update response_data with its contents
    #         response_data.update(result.info)
    #         # Ensure message, percent, current, total are consistently pulled
    #         # from the updated response_data, with fallbacks to avoid None/KeyError
    #         # These .get() calls are still good practice to handle potentially missing keys within result.info
    #         response_data['message'] = response_data.get('message', 'Processing...')
    #         response_data['percent'] = response_data.get('percent', 0)
    #         response_data['current'] = response_data.get('current', 0)
    #         response_data['total'] = response_data.get('total', 0)
    #     elif result.state == 'FAILURE' and result.info is not None:
    #          # This handles cases where info might be an exception object directly on failure
    #          response_data['message'] = f"Task failed: {result.info}"
    #          response_data['percent'] = 100 # Mark as 100% complete even on failure for UI


    #     # Refine messages based on state (now using response_data's already set values or defaults)
    #     if response_data['state'] == 'PENDING':
    #         # Only set message if not already set by a more specific result.info
    #         if 'message' not in result.info or not isinstance(result.info, dict):
    #             response_data['message'] = 'Task is pending...'
    #     elif response_data['state'] == 'STARTED':
    #         if 'message' not in result.info or not isinstance(result.info, dict):
    #             response_data['message'] = 'Task has started...'
    #     elif response_data['state'] == 'PROGRESS':
    #         # Message and percent should already be updated from result.info if it was a dict
    #         pass # No extra update needed here
    #     elif response_data['state'] == 'SUCCESS':
    #         if 'message' not in result.info or not isinstance(result.info, dict):
    #             response_data['message'] = 'Task completed successfully.'
    #         response_data['percent'] = 100 # Ensure it's 100% on success
    #     elif response_data['state'] == 'FAILURE':
    #         if 'message' not in result.info or not isinstance(result.info, dict):
    #             response_data['message'] = 'Task failed.'
    #         response_data['percent'] = 100 # Ensure it's 100% on failure
        
    #     return JsonResponse(response_data)


    def task_status_view(self, request, task_id):
            return JsonResponse(_get_task_status_response_data(task_id, 'admin:task_status'))


    # def get_admin_url(self, name):
    #     """Helper to get admin URL names more reliably."""
    #     return reverse(f'admin:{self.opts.app_label}_{self.opts.model_name}_{name}')


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('station_id').exclude(station_id__isnull=True)

    def display_station_id(self, obj):
        return obj.station_id_id if obj.station_id else None
    display_station_id.short_description = 'Station ID'
    display_station_id.admin_order_field = 'station_id_id'

    def station_name(self, obj):
        return obj.station_id.name if obj.station_id else 'Unknown'
    station_name.short_description = 'Name'

    def station_code(self, obj):
        return obj.station_id.station_code if obj.station_id else None
    station_code.short_description = 'Station Code'



# Custom Admin for WaterLevelForecast

@admin.register(WaterLevelForecast) 
class WaterlevelForecastAdmin(admin.ModelAdmin, ExportCsvMixin):

    # template path
    change_list_template = "admin/data_load/waterlevelforecast/change_list.html"  

    class Media:
        css = {
            'all': ('admin/css/admin_custom.css',), # Ensure this path is correct in your staticfiles
        }
        # Add jQuery if your admin doesn't include it by default and your custom JS needs it
        # js = (
        #     'https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js',
        # )
        
    def get_station_name(self, obj):
        try:
            # Adapt to your current Station model and foreign key setup
            # obj.station_id is a Station object; obj.station_id.station_id is its integer ID
            name = Station.objects.filter(station_id=obj.station_id.station_id).values_list('name', flat=True).first()
            return name if name else 'Unknown'
        except (ValueError, TypeError, Station.DoesNotExist): # Corrected model exception
            return 'Unknown'

    get_station_name.short_description = 'Station Name'

    # Corrected list_display to match WaterLevelForecast model fields
    list_display = ('station_id', 'get_station_name', 'forecast_date', 'water_level')
    # Corrected list_filter and search_fields to match WaterLevelForecast model
    list_filter = ('forecast_date', 'station_id')
    search_fields = ('station_id__name', 'water_level') 
    actions = ["export_as_csv"]

    def get_urls(self):
        logger.info("Registering WaterlevelForecastAdmin URLs")
        urls = super().get_urls()
        my_urls = [
            # Using your provided URL name 'forecast-import-csv'
            path('forecast-import-csv/', self.admin_site.admin_view(self.forecast_import_csv), name='forecast-import-csv'),
            # New URL for polling task status for these multiple forecast uploads
            path('task-status-multiple/<str:task_id>/', self.admin_site.admin_view(self.task_status_multiple_view), name='task_status_multiple'),
        ]
        logger.info(f"Custom URLs for WaterlevelForecastAdmin: {my_urls}")
        return my_urls + urls
        

    def forecast_import_csv(self, request):
        logger.info("Starting forecast_import_csv at %s", datetime.now())
        # task_ids and file_names are now handled by the JsonResponse for JS
        
        if request.method == "POST":
            logger.info("Received POST request for forecast CSV import")
            
            form = ForecastCsvImportForm(request.POST, request.FILES) # Use the specific form for multiple files

            if not form.is_valid():
                logger.error(f"Invalid form data: {form.errors.as_json()}")
                messages.error(request, f"Invalid form data: {form.errors.as_text()}")
                # For non-AJAX fallback (optional, as the JS will handle JSON)
                if 'no-ajax' in request.POST:
                    return render(request, "admin/multiple_csv_upload.html", {"form": form})
                return JsonResponse({"error": "Invalid form data", "details": form.errors.as_json()}, status=400)

            # Use form.cleaned_data.get('forecast_csv_file') which returns a list of files
            uploaded_files = form.cleaned_data.get('forecast_csv_file', [])
            noOfFiles = len(uploaded_files)
            logger.info(f"Received {noOfFiles} files: {[f.name for f in uploaded_files]}")

            if noOfFiles == 0:
                logger.error("No files uploaded")
                messages.error(request, "No files were uploaded.")
                if 'no-ajax' in request.POST:
                    return render(request, "admin/multiple_csv_upload.html", {"form": form})
                return JsonResponse({"error": "No files uploaded"}, status=400)

            # --- Pre-fetch and prepare station data ---
            station_name_to_id_map = {}
            for s in Station.objects.all():
                if s.name:
                    normalized_db_name = s.name.strip().replace(' ', '').lower()
                    station_name_to_id_map[normalized_db_name] = s.station_id # Store Station.station_id
            logger.info(f"Station name to ID map built: {station_name_to_id_map}")

            station_aliases = {
                'baiderbazar': 'baidyarbazar',
                'barisal': 'barishal',
                'bogra': 'bogura',
                'c-nawabganj': 'chapai-nawabganj',
                'chittagong': 'chattogram',
                'chittagong': 'chattogram',
                'elasinghat': 'elasin',
                'manu-rly-br': 'manu-rb',
                'meghna-br': 'meghnabridge',
                'mohadevpur': 'mohadebpur',
                'rekabibazar': 'rekabi-bazar',
                'sherpur': 'sherpur-sylhet',
                'comilla': 'cumilla',
                'jibanpur': 'debidwar',

                # 'rekabibazar': 'rekabi',
                # 'c-nawabganj': 'c',
                # 'meghna-br': 'meghna',
                # 'hardinge-rb': 'hardinge',
                # 'manu-rly-br': 'manu',
                # 'gorai-rb': 'gorai'
            }
            logger.info(f"Custom station aliases: {station_aliases}")
            
            dispatched_task_ids_with_filenames = [] # To store task_id and filename for frontend tracking
            tasks_dispatched_count = 0

            for f in uploaded_files: # Iterate over cleaned_data files
                try:
                    file_station_name = os.path.splitext(f.name)[0].strip().replace(' ', '').lower()
                    logger.info(f"Processing file: {f.name}, derived station_name: {file_station_name}")

                    if file_station_name in station_aliases:
                        logger.info(f"Found alias for '{file_station_name}', mapping to '{station_aliases[file_station_name]}'")
                        file_station_name = station_aliases[file_station_name]
                        
                    if file_station_name not in station_name_to_id_map:
                        error_msg = f"Station '{file_station_name}' derived from filename '{f.name}' not found in station mapping. Skipping this file."
                        logger.error(error_msg)
                        messages.warning(request, error_msg)
                        continue

                    file_obj = f.read()
                    pd_csv = io.BytesIO(file_obj)
                    # Corrected delimiter and skiprows for Aricha.csv structure
                    forecastDF = pd.read_csv(pd_csv, skiprows=1, encoding='utf-8-sig', delimiter=',')
                    
                    logger.info(f"DataFrame for {f.name} columns: {forecastDF.columns.tolist()}")
                    logger.debug(f"First 3 rows of {f.name}:\n{forecastDF.head(3).to_string()}")

                    # Dispatch task for each file
                    # 'duration' parameter seems unused in task, pass a dummy '1'
                    task = import_forecast_files.delay(1, forecastDF.to_dict(), station_name_to_id_map, file_station_name)
                    dispatched_task_ids_with_filenames.append({'id': task.id, 'name': f.name})
                    tasks_dispatched_count += 1
                    logger.info(f"Started import_forecast_files task with ID: {task.id} for file: {f.name}")
                except Exception as e:
                    logger.error(f"Error processing file {f.name}: {str(e)}", exc_info=True)
                    messages.error(request, f"Error processing file {f.name}: {str(e)}")
                    continue

            if dispatched_task_ids_with_filenames:
                messages.success(request, f"Started import tasks for {tasks_dispatched_count} of {noOfFiles} files.")
                # Return JSON response for AJAX
                return JsonResponse({
                    "task_ids": dispatched_task_ids_with_filenames, # Pass a list of objects for frontend
                    "total_files": noOfFiles,
                    "message": f"Started processing {tasks_dispatched_count} file(s)"
                })
            else:
                messages.error(request, "No tasks were started. Please check the uploaded files and try again.")
                return JsonResponse({"error": "No tasks started"}, status=400)

        logger.info("Rendering multiple forecast CSV import form")
        form = ForecastCsvImportForm()
        # Ensure this template path is correct (relative to your TEMPLATES settings)
        return render(request, "admin/multiple_csv_upload.html", {"form": form})

    # Re-using the shared helper for status view
    def task_status_multiple_view(self, request, task_id):
        return JsonResponse(_get_task_status_response_data(task_id, 'admin:task_status_multiple'))



# Custom Admin for WaterLevelForecastsExperimentals
@admin.register(WaterLevelForecastsExperimentals)
class WaterLevelForecastsExperimentalsAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('display_station_id', 'station_code', 'station_name', 'forecast_date', 'waterlevel_min', 'waterlevel_max', 'waterlevel_mean')
    list_filter = ('forecast_date',)
    search_fields = ('station_id__name', 'station_id__station_code')
    list_per_page = 25
    ordering = ('station_id_id',)

    change_list_template = "admin/data_load/waterlevelforecastsexperimental/change_list.html" # Path for the changelist template

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # URL for importing experimental forecast CSVs (uses same form)
            path('import-csv/', self.admin_site.admin_view(self.import_experimental_forecast_csv), name='experimental-forecast-import-csv'),
            # URL for polling task status for experimental forecasts
            path('task-status-experimental/<str:task_id>/', self.admin_site.admin_view(self.task_status_experimental_view), name='task_status_experimental'),
        ]
        return custom_urls + urls

    def import_experimental_forecast_csv(self, request):
        logger.info("Starting import_experimental_forecast_csv at %s", datetime.now())
        
        if request.method == "POST":
            logger.info("Received POST request for experimental forecast CSV import")
            form = ForecastCsvImportForm(request.POST, request.FILES) # Use the same form for multiple files

            if not form.is_valid():
                logger.error(f"Invalid form data: {form.errors.as_json()}")
                messages.error(request, f"Invalid form data: {form.errors.as_text()}")
                return JsonResponse({"error": "Invalid form data", "details": form.errors.as_json()}, status=400)

            uploaded_files = form.cleaned_data.get('forecast_csv_file', [])
            noOfFiles = len(uploaded_files)
            logger.info(f"Received {noOfFiles} files: {[f.name for f in uploaded_files]}")

            if noOfFiles == 0:
                logger.error("No files uploaded")
                messages.error(request, "No files were uploaded.")
                return JsonResponse({"error": "No files uploaded"}, status=400)

            station_name_to_id_map = {}
            for s in Station.objects.all():
                if s.name:
                    normalized_db_name = s.name.strip().replace(' ', '').lower()
                    station_name_to_id_map[normalized_db_name] = s.station_id
            logger.info(f"Station name to ID map built: {station_name_to_id_map}")

            station_aliases = {

                # 'gorai-rb': 'gorai'
                # 'rekabibazar': 'rekabi', 'c-nawabganj': 'c', 'meghna-br': 'meghna',
                # 'hardinge-rb': 'hardinge', 'manu-rly-br': 'manu', 'gorai-rb': 'gorai'
                # 'baiderbazar': 'baidyarbazar',
                # 'barisal': 'barishal',
                # 'bogra': 'bogura',
                # 'c-nawabganj': 'chapai-nawabganj',
                # 'chittagong': 'chattogram',
                # 'chittagong': 'chattogram',
                'elasinghat': 'elasin',
                'elashinghat': 'elasin',
                'hardinge-bridge':'hardinge-rb',
                'hardinge':'hardinge-rb',
                'sureshwar':'sureshswar'

                
                # 'manu-rly-br': 'manu-rb',
                # 'meghna-br': 'meghnabridge',
                # 'mohadevpur': 'mohadebpur',
                # 'rekabibazar': 'rekabi-bazar',
                # 'sherpur': 'sherpur-sylhet',
                # 'comilla': 'cumilla',
                # 'jibanpur': 'debidwar',

            }
            logger.info(f"Custom station aliases: {station_aliases}")
            
            dispatched_task_ids_with_filenames = []
            tasks_dispatched_count = 0

            for f in uploaded_files:
                try:
                    file_station_name = os.path.splitext(f.name)[0].strip().replace(' ', '').lower()
                    logger.info(f"Processing file: {f.name}, derived station_name: {file_station_name}")

                    if file_station_name in station_aliases:
                        file_station_name = station_aliases[file_station_name]
                        
                    if file_station_name not in station_name_to_id_map:
                        error_msg = f"Station '{file_station_name}' derived from filename '{f.name}' not found in mapping. Skipping this file."
                        logger.error(error_msg)
                        messages.warning(request, error_msg)
                        continue

                    file_obj = f.read()
                    pd_csv = io.BytesIO(file_obj)
                    # --- UPDATED: skiprows=2 and delimiter=',' for experimental files ---
                    forecastDF = pd.read_csv(pd_csv, skiprows=1, encoding='utf-8-sig', delimiter=',')
                    
                    logger.info(f"DataFrame for {f.name} columns: {forecastDF.columns.tolist()}")

                    # Dispatch to the new experimental forecast task
                    task = import_experimental_forecast_files.delay(1, forecastDF.to_dict(), station_name_to_id_map, file_station_name)
                    dispatched_task_ids_with_filenames.append({'id': task.id, 'name': f.name})
                    tasks_dispatched_count += 1
                    logger.info(f"Started import_experimental_forecast_files task with ID: {task.id} for file: {f.name}")
                except Exception as e:
                    logger.error(f"Error processing file {f.name}: {str(e)}", exc_info=True)
                    messages.error(request, f"Error processing file {f.name}: {str(e)}")
                    continue

            if dispatched_task_ids_with_filenames:
                messages.success(request, f"Started import tasks for {tasks_dispatched_count} of {noOfFiles} files.")
                return JsonResponse({
                    "task_ids": dispatched_task_ids_with_filenames,
                    "total_files": noOfFiles,
                    "message": f"Started processing {tasks_dispatched_count} file(s)"
                })
            else:
                messages.error(request, "No tasks were started. Please check the uploaded files and try again.")
                return JsonResponse({"error": "No tasks started"}, status=400)

        logger.info("Rendering experimental forecast CSV import form")
        form = ForecastCsvImportForm()
        # Reusing the multiple_csv_upload template
        context = self.admin_site.each_context(request)
        context['title'] = 'Upload Experimental Water Level Forecasts CSV'
        context['form'] = form
        context['opts'] = self.model._meta
        # Crucially, pass the correct task status URL name for the JS
        context['task_status_url_name'] = 'admin:task_status_experimental' 
        return render(request, "admin/multiple_csv_upload.html", context)



    # Re-using the shared helper for status view
    def task_status_experimental_view(self, request, task_id):
        return JsonResponse(_get_task_status_response_data(task_id, 'admin:task_status_experimental'))


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('station_id').exclude(station_id__isnull=True)

    def display_station_id(self, obj):
        return obj.station_id_id if obj.station_id else None
    display_station_id.short_description = 'Station ID'
    display_station_id.admin_order_field = 'station_id_id'

    def station_name(self, obj):
        return obj.station_id.name if obj.station_id else 'Unknown'
    station_name.short_description = 'Name'

    def station_code(self, obj):
        return obj.station_id.station_code if obj.station_id else None
    station_code.short_description = 'Station Code'

# Custom Admin for RainfallObservation
@admin.register(RainfallObservation)
class RainfallObservationAdmin(admin.ModelAdmin):
    list_display = ('display_station_id', 'station_code', 'station_name', 'observation_date', 'rainfall')
    list_filter = ('observation_date',)
    search_fields = ('station_id__name', 'station_id__station_code')
    list_per_page = 25
    ordering = ('station_id_id',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('station_id').exclude(station_id__isnull=True)

    def display_station_id(self, obj):
        return obj.station_id_id if obj.station_id else None
    display_station_id.short_description = 'Station ID'
    display_station_id.admin_order_field = 'station_id_id'

    def station_name(self, obj):
        return obj.station_id.name if obj.station_id else 'Unknown'
    station_name.short_description = 'Name'

    def station_code(self, obj):
        return obj.station_id.station_code if obj.station_id else None
    station_code.short_description = 'Station Code'

# Set the header for grouping models under "Forecasters" after registration
for model in [Station, RainfallStation, MonthlyRainfall, WaterLevelObservation, 
              WaterLevelForecast, WaterLevelForecastsExperimentals, RainfallObservation]:
    admin.site._registry[model].header = 'Forecasters'


# --- NEW SHARED HELPER FUNCTION FOR TASK STATUS ---
def _get_task_status_response_data(task_id, reverse_url_name):
    result = AsyncResult(task_id)
    
    response_data = {
        'state': result.state,
        'message': 'Polling task status...', # Initial default message
        'percent': 0,
        'current': 0,
        'total': 0,
        'status_url': reverse(reverse_url_name, args=[task_id])
    }

    # First, attempt to get data from result.info IF it's a dictionary.
    if isinstance(result.info, dict):
        response_data.update(result.info)
        response_data['message'] = response_data.get('message', 'Processing...')
        response_data['percent'] = response_data.get('percent', 0)
        response_data['current'] = response_data.get('current', 0)
        response_data['total'] = response_data.get('total', 0)
        
        # If the task returned a custom status/message (e.g., from an error or ignore)
        if 'status' in response_data and response_data['status'] in [states.FAILURE, states.REVOKED]:
            response_data['state'] = response_data['status'] # Override state with custom returned status
            response_data['message'] = response_data.get('message', f"Task completed with status: {response_data['status']}")
            response_data['percent'] = 100 # Mark as 100% complete for UI on terminal states

    else: # If result.info is not a dict (e.g., None, or a serialized native exception)
        if result.state == states.FAILURE:
            # result.result would contain the serialized exception object from raise e
            # Accessing result.result can sometimes trigger deserialization errors if malformed.
            # Safest to just provide a generic message or try to get result.result as string
            try:
                # Attempt to get the result, which might be the error string if raised
                error_content = str(result.result) if result.result else "Unknown error"
            except Exception: # Catch any error during result access
                error_content = "Error details unavailable"
            response_data['message'] = f"Task failed: {error_content}"
            response_data['percent'] = 100
        elif result.state == states.REVOKED:
            response_data['message'] = "Task was ignored/revoked."
            response_data['percent'] = 100

    # Final refinement of message based on state if it's still the initial generic one
    if response_data['state'] == states.PENDING and response_data['message'] == 'Polling task status...':
        response_data['message'] = 'Task is pending...'
    elif response_data['state'] == states.STARTED and response_data['message'] == 'Polling task status...':
        response_data['message'] = 'Task has started...'
    elif response_data['state'] == states.SUCCESS:
        # Ensure a success message is present, and percent is 100
        if response_data['message'] == 'Polling task status...' or not response_data['message']:
             response_data['message'] = 'Task completed successfully.'
        response_data['percent'] = 100
    
    return response_data




class RainfallAdminSite(AdminSite):
    site_header = "Forecasters Admin Panel"
    site_title = "Forecasters Admin"
    # index_title = "Welcome to Forecasters Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-rainfall-map/', self.admin_view(self.run_rainfall_map_view), name='run-rainfall-map'),
        ]
        return custom_urls + urls

    @method_decorator(csrf_protect)
    @method_decorator(require_POST)
    def run_rainfall_map_view(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse({'status': 'error', 'message': "You do not have permission to run this command."}, status=403)

        try:
            task = generate_rainfall_map_task.delay() # Get the task object
            return JsonResponse({
                'status': 'success',
                'message': "Rainfall distribution map generation task started successfully.",
                'task_id': task.id # Return the task ID
            })
        except Exception as e:
            print(f"Error triggering Celery task: {e}")
            return JsonResponse({'status': 'error', 'message': f"Error starting task: {str(e)}"}, status=500)

admin.site.__class__ = RainfallAdminSite


@admin.register(DistrictFloodAlert)
class DistrictFloodAlertAdmin(admin.ModelAdmin):
    # List fields to display in the change list page of the admin
    list_display = (
        'alert_date',
        'district_name',
        'alert_type',
        'alert_type_alert_no_display' # Custom method to display alert_no
    )

    # Fields to use for searching
    search_fields = (
        'district_name',
        'alert_type__alert_type' # Allows searching by alert_type string
    )

    # Fields to use for filtering
    list_filter = (
        # ('alert_date',DateRangeFilterBuilder()),
        'alert_date',
        'alert_type__alert_type', # Allows filtering by alert_type string
        'district_name',
    )

    # Make alert_date a clickable link to the detail page
    list_display_links = ('alert_date', 'district_name',)

    # Fields to order by default
    ordering = ('-alert_date', 'district_name',) # Order by most recent date first

    # Readonly fields (you likely don't want to manually edit these if they are generated by script)
    readonly_fields = ('alert_date', 'district_name',)

    # Add a fieldset for better organization in the detail view (optional)
    fieldsets = (
        (None, {
            'fields': ('alert_date', 'district_name', 'alert_type'),
        }),
    )

    # Method to display related alert_no from WaterlevelAlert
    # This assumes WaterlevelAlert has an 'alert_no' field
    def alert_type_alert_no_display(self, obj):
        return obj.alert_type.alert_no if obj.alert_type else 'N/A'
    alert_type_alert_no_display.short_description = 'Alert No' # Column header


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-flood-alerts/', self.admin_site.admin_view(self.run_flood_alerts_view), name='data_load_districtfloodalert_run-flood-alerts'),
            # The URL name needs to be unique. A common pattern is app_label_model_name_action.
        ]
        return custom_urls + urls

    @method_decorator(csrf_protect)
    @method_decorator(require_POST)
    def run_flood_alerts_view(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse({'status': 'error', 'message': "You do not have permission to run this command."}, status=403)
        try:
            task = generate_flood_alerts_task.delay()
            return JsonResponse({
                'status': 'success',
                'message': "Flood alerts generation task started successfully.",
                'task_id': task.id
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error starting task: {str(e)}"}, status=500)



from .forms import FloodmapsUploadForm
from django.core.files.storage import default_storage
import re
from datetime import datetime, timedelta
import os
from django.db import transaction

@admin.register(Floodmaps)
class FloodmapsAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'file_date', 'file')
    search_fields = ('file_name',)
    change_list_template = "admin/data_load/floodmaps/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('upload-floodmaps-csv/', self.admin_site.admin_view(self.upload_floodmaps_csv), name='upload-floodmaps-csv'),
        ]
        return my_urls + urls

    def upload_floodmaps_csv(self, request):
        if request.method == "POST":
            form = FloodmapsUploadForm(request.POST, request.FILES)
            if form.is_valid():
                files = form.cleaned_data['floodmap_files']
                
                if not files:
                    messages.warning(request, "No files selected for upload.")
                    return HttpResponseRedirect("../")

                try:
                    with transaction.atomic():
                        # 1. Delete all existing Floodmaps records and their associated files
                        deleted_count = 0
                        existing_records = Floodmaps.objects.all()
                        for record in existing_records:
                            if record.file:
                                if default_storage.exists(record.file.path):
                                    default_storage.delete(record.file.path)
                            record.delete()
                            deleted_count += 1
                        
                        messages.info(request, f"Deleted {deleted_count} existing flood map record(s) and their files.")

                        # 2. Insert all newly uploaded files with incrementing dates
                        uploaded_count = 0
                        
                        # Get the current date (today) in Dhaka timezone
                        # Make sure pytz is imported if you're localizing
                        import pytz
                        bangladesh_tz = pytz.timezone('Asia/Dhaka')
                        current_date = datetime.now(bangladesh_tz).date() # Start with today's date

                        # Sort files to ensure predictable date assignment
                        # Assuming Flood_EF0.tif, Flood_EF1.tif, etc., sorting by name will work.
                        sorted_files = sorted(files, key=lambda f: f.name)

                        for f in sorted_files:
                            try:
                                file_name_from_upload = f.name
                                
                                # Determine file_date based on file_name
                                if "Flood_EF0.tif" in file_name_from_upload:
                                    file_date_for_record = current_date # Today for EF0
                                else:
                                    # For other files, try to extract the number and increment date
                                    ef_match = re.search(r'Flood_EF(\d+)\.tif', file_name_from_upload)
                                    if ef_match:
                                        ef_number = int(ef_match.group(1))
                                        # date = current_date + (ef_number days)
                                        file_date_for_record = current_date + timedelta(days=ef_number)
                                    else:
                                        # Fallback if filename pattern doesn't match for other files
                                        file_date_for_record = current_date 

                                floodmap_instance = Floodmaps(
                                    file=f,
                                    file_name=file_name_from_upload,
                                    file_date=file_date_for_record
                                )
                                floodmap_instance.save()
                                uploaded_count += 1
                                
                            except Exception as e:
                                messages.error(request, f"Error uploading {f.name}: {str(e)}")
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.exception(f"Error saving new floodmap file {f.name}")
                                raise 

                        messages.success(request, f"Successfully uploaded {uploaded_count} new flood map file(s).")
                        
                except Exception as e:
                    messages.error(request, f"An error occurred during the batch upload process. All changes were rolled back. Error: {str(e)}")
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.exception("Batch flood map upload failed.")
                    
                return HttpResponseRedirect("../")
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            form = FloodmapsUploadForm()
        
        context = self.admin_site.each_context(request)
        context['form'] = form
        context['title'] = "Upload Flood Maps"
        return render(request, "admin/data_load/floodmaps/upload_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_upload_button'] = True
        return super().changelist_view(request, extra_context=extra_context)





class MonsoonConfigAdmin(admin.ModelAdmin):
    list_display = ('config_year', 'title', 'sort_order', 'color', 'is_active')
    list_filter = ('config_year', 'is_active')
    search_fields = ('title',)
    ordering = ('config_year', 'sort_order')

admin.site.register(MonsoonConfig, MonsoonConfigAdmin)


from .models import ScheduledTask
from data_load.tasks import generate_flood_alerts_task

@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'is_enabled', 'description')
    list_filter = ('is_enabled',)
    search_fields = ('task_name', 'description')
    list_editable = ('is_enabled',)

    # Adds the custom URL for our button
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'run-flood-alerts/',
                self.admin_site.admin_view(self.run_flood_alerts_view),
                name='run-flood-alerts'
            ),
        ]
        return custom_urls + urls

    # The view that runs the flood alert task
    def run_flood_alerts_view(self, request):
        if not request.user.is_staff:
            messages.error(request, "You do not have permission to run this command.")
        elif request.method == 'POST':
            try:
                generate_flood_alerts_task.delay()
                messages.success(request, "Flood alert generation started in the background.")
            except Exception as e:
                messages.error(request, f"Error starting flood alert task: {str(e)}")
        
        # Redirect back to the main admin dashboard
        return HttpResponseRedirect('/admin/')


from .models import DistrictFloodAlertAutoUpdate 
class DistrictFloodAlertAutoUpdateAdmin(admin.ModelAdmin):
    list_display = ('district_name', 'auto_update')
admin.site.register(DistrictFloodAlertAutoUpdate, DistrictFloodAlertAutoUpdateAdmin)


from .models import JsonEntry
admin.site.register(JsonEntry)