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

                'elasinghat': 'elasin',
                'elashinghat': 'elasin',
                'hardinge-bridge':'hardinge-rb',
                'hardinge':'hardinge-rb',
                'sureshwar':'sureshswar'

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
    
    
    


@shared_task(bind=True)
def import_experimental_forecast_files(self, duration, forecastDF_dict, stationNameToIdDict, station_name):

    progress_recorder = ProgressRecorder(self)
    inserted_forecast_count = 0
    updated_forecast_count = 0
    inserted_observation_count = 0
    updated_observation_count = 0
    skipped_rows_count = 0
    total_initial_rows = 0

    logger.info(f"Task started for station: {station_name}. Duration: {duration}")

    try:
        ffwc_last_update_date_experimental()

        logger.info(f"Starting import_experimental_forecast_files task for station: {station_name}")
        progress_recorder.set_progress(5, 100, description="Converting data to DataFrame")

        forecastDF = pd.DataFrame(forecastDF_dict)
        total_initial_rows = len(forecastDF)
        logger.debug(f"Initial DataFrame has {total_initial_rows} rows. Columns: {forecastDF.columns.tolist()}")

        # --- Date Parsing Regex Patterns (REVISED ORDER FOR PRIORITY) ---
        pattern_two = r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2}):(\d{2})"
        pattern_one = r"(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(\d{1,2}):(\d{2})"

        progress_recorder.set_progress(10, 100, description=f"Processing experimental data for station '{station_name}'...")

        station_id_for_df = stationNameToIdDict.get(station_name)
        if station_id_for_df is None:
            error_msg = f"Station '{station_name}' not found in stationNameToIdDict or has None ID."
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            return None
        logger.debug(f"Station '{station_name}' mapped to ID: {station_id_for_df}")


        # Ensure 'st_id' column is present for both forecast and observation processing
        forecastDF['st_id'] = station_id_for_df

        # --- Identify experimental forecast columns based on suffixes. ---
        min_col = next((col for col in forecastDF.columns.tolist() if col.endswith('-16')), None)
        max_col = next((col for col in forecastDF.columns.tolist() if col.endswith('-84')), None)
        mean_col = next((col for col in forecastDF.columns.tolist() if col.endswith('-Mean')), None)
        logger.debug(f"Identified forecast columns: Min='{min_col}', Max='{max_col}', Mean='{mean_col}'")


        # --- Identify observation column ---
        observation_col_name_expected = f"{station_name}-obs"
        actual_observation_col = next((col for col in forecastDF.columns.tolist() if col.lower() == observation_col_name_expected.lower()), None)
        logger.info(f"Searching for observation column '{observation_col_name_expected}'. Found: '{actual_observation_col}'")
        if not actual_observation_col:
            logger.warning(f"Observation column '{observation_col_name_expected}' not found in DataFrame for station '{station_name}'. Observations will not be processed.")


        # --- MODIFIED COLUMN PRESENCE CHECK FOR FORECASTS ---
        if not mean_col:
            error_msg = (
                f"Missing essential experimental forecast column '{station_name}-Mean' for station '{station_name}'. "
                f"Found: Min='{min_col}', Max='{max_col}', Mean='{mean_col}'. Task requires Mean column."
            )
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            return None

        # Build list of columns to select from DataFrame for both forecast and observation.
        columns_to_select = ['YYYY-MM-DD HH:MM:SS', mean_col, 'st_id']
        if min_col: columns_to_select.append(min_col)
        if max_col: columns_to_select.append(max_col)
        # Ensure actual_observation_col is added only if found and not already in the list
        if actual_observation_col and actual_observation_col not in columns_to_select:
             columns_to_select.append(actual_observation_col)
        logger.debug(f"Final columns selected from DataFrame: {columns_to_select}")

        # Validate all columns_to_select exist in the original DataFrame
        missing_cols_in_df = [col for col in columns_to_select if col not in forecastDF.columns.tolist()]
        if missing_cols_in_df:
            error_msg = f"Critical error: Required columns {missing_cols_in_df} are missing in the input DataFrame. Available: {forecastDF.columns.tolist()}"
            logger.error(error_msg)
            progress_recorder.set_progress(100, 100, description=error_msg)
            self.update_state(state=states.FAILURE, meta={'message': error_msg})
            return None


        forecastDF = forecastDF[columns_to_select].copy()

        # Rename columns for consistency with model fields
        rename_map = {'YYYY-MM-DD HH:MM:SS': 'date_time', mean_col: 'waterlevel_mean'}
        if min_col: rename_map[min_col] = 'waterlevel_min'
        if max_col: rename_map[max_col] = 'waterlevel_max'

        # Only add to rename_map if actual_observation_col was found
        if actual_observation_col:
            rename_map[actual_observation_col] = 'waterlevel_obs'

        forecastDF.rename(columns=rename_map, inplace=True)
        logger.debug(f"DataFrame columns after renaming: {forecastDF.columns.tolist()}")
        logger.debug(f"First 5 rows of processed DataFrame:\n{forecastDF.head()}")


        # Drop rows with missing 'date_time' as it's essential for all records
        forecastDF = forecastDF.dropna(subset=['date_time'])
        logger.debug(f"DataFrame has {len(forecastDF)} rows after dropping rows with missing 'date_time'.")


        total_rows_after_filter = len(forecastDF)
        if total_rows_after_filter == 0:
            logger.warning(f"No valid data (with dates) to process after initial filtering for station {station_name}")
            progress_recorder.set_progress(100, 100, description="No valid data to process")
            self.update_state(state=states.SUCCESS, meta={'message': f"No valid data (with dates) for station {station_name}"})
            return {"inserted_rows": 0, "updated_rows": 0, "skipped_rows": skipped_rows_count, "total_rows": total_initial_rows, "state": states.SUCCESS}

        forecastDF.reset_index(drop=True, inplace=True)

        # --- Date parsing and timezone handling ---
        parsed_data = []
        obs_none_count = 0
        obs_valid_count = 0

        for index, row in forecastDF.iterrows():
            dateTimeString = str(row['date_time']).strip()
            try:
                dt_obj_naive = None
                match_two = re.match(pattern_two, dateTimeString)
                match_one = re.match(pattern_one, dateTimeString)

                if match_two:
                    dt_obj_naive = datetime.strptime(dateTimeString, '%Y-%m-%d %H:%M:%S')
                elif match_one:
                    dt_obj_naive = datetime.strptime(dateTimeString, '%d/%m/%y %H:%M')
                else:
                    logger.warning(f"Invalid date format at row {index} for {station_name}: {dateTimeString}. Skipping row.")
                    skipped_rows_count += 1
                    continue

                if dt_obj_naive.tzinfo is None:
                    dt_obj_aware = pytz.utc.localize(dt_obj_naive)
                else:
                    dt_obj_aware = dt_obj_naive.astimezone(pytz.utc)

                normalized_dt = normalize_datetime(dt_obj_aware)
                normalized_dt = normalized_dt.replace(second=0)

                def to_decimal_or_none(value):
                    if pd.isna(value) or (isinstance(value, (int, float)) and value == -9999.0):
                        return None
                    try:
                        return Decimal(str(round(float(value), 2)))
                    except (ValueError, TypeError, InvalidOperation):
                        return None

                waterlevel_obs_val = None
                if 'waterlevel_obs' in row:
                    waterlevel_obs_val = to_decimal_or_none(row['waterlevel_obs'])

                record = {
                    'station_id_val': row['st_id'],
                    'date_time': normalized_dt,
                    'waterlevel_min': to_decimal_or_none(row.get('waterlevel_min')),
                    'waterlevel_max': to_decimal_or_none(row.get('waterlevel_max')),
                    'waterlevel_mean': to_decimal_or_none(row.get('waterlevel_mean')),
                    'waterlevel_obs': waterlevel_obs_val,
                }
                parsed_data.append(record)

                if waterlevel_obs_val is None:
                    obs_none_count += 1
                else:
                    obs_valid_count += 1

            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(f"Date/value parsing error at row {index} for {station_name}: {dateTimeString}, Error: {str(e)}. Skipping row.")
                skipped_rows_count += 1
                continue

            progress_recorder.set_progress(
                20 + int((index + 1) * 20 / total_rows_after_filter),
                100,
                description=f"Parsed {index + 1}/{total_rows_after_filter} dates for {station_name}"
            )
        logger.info(f"Finished parsing data. Total rows parsed: {len(parsed_data)}. Valid observations: {obs_valid_count}, None observations: {obs_none_count}.")


        if not parsed_data:
            logger.warning(f"No valid data to process after parsing for station {station_name}")
            progress_recorder.set_progress(100, 100, description="No valid data to process")
            self.update_state(state=states.SUCCESS, meta={'message': f"No valid data for station {station_name}"})
            return {"inserted_rows": 0, "updated_rows": 0, "skipped_rows": skipped_rows_count, "total_rows": total_initial_rows, "state": states.SUCCESS}

        total_processed_rows = len(parsed_data)
    
        progress_recorder.set_progress(40, 100, description=f"Performing database operations for {station_name}...")
    
        with transaction.atomic():
            station_ids_to_fetch = {data['station_id_val'] for data in parsed_data}
            station_objects_map = {s.station_id: s for s in Station.objects.filter(station_id__in=station_ids_to_fetch)}
            logger.debug(f"Fetched station objects with IDs: {list(station_objects_map.keys())}")


            # --- Lists for Forecast Data ---
            experimental_forecasts_for_create = []
            experimental_forecasts_for_update_list = [] # Will be populated if existing conflicts

            existing_experimental_forecast_objects = WaterLevelForecastsExperimentals.objects.filter(
                station_id__station_id__in=station_ids_to_fetch,
                forecast_date__in=[data['date_time'] for data in parsed_data]
            ).select_related('station_id')

            existing_experimental_forecast_map = {
                (obj.station_id.station_id, obj.forecast_date): obj
                for obj in existing_experimental_forecast_objects
            }
            logger.debug(f"Found {len(existing_experimental_forecast_objects)} existing experimental forecasts in DB for lookup.")


            # --- Lists for Observation Data ---
            experimental_observations_for_create = []
            experimental_observations_for_update_list = [] # Will be populated if existing conflicts

            existing_experimental_observation_objects = WaterLevelObservationExperimentals.objects.filter(
                station_id__station_id__in=station_ids_to_fetch,
                observation_date__in=[data['date_time'] for data in parsed_data]
            ).select_related('station_id')

            existing_experimental_observation_map = {
                (obj.station_id.station_id, obj.observation_date): obj
                for obj in existing_experimental_observation_objects
            }
            logger.debug(f"Found {len(existing_experimental_observation_objects)} existing experimental observations in DB for lookup.")


            for i, data_row in enumerate(parsed_data):
                station_obj = station_objects_map.get(data_row['station_id_val'])
                if not station_obj:
                    logger.warning(f"Station with ID {data_row['station_id_val']} not found for experimental data. Skipping row.")
                    skipped_rows_count += 1
                    continue

                common_key = (data_row['station_id_val'], data_row['date_time'])

                # --- Process Forecast Data ---
                if data_row['waterlevel_mean'] is not None:
                    if common_key in existing_experimental_forecast_map:
                        obj_to_update = existing_experimental_forecast_map[common_key]
                        if (obj_to_update.waterlevel_min != data_row['waterlevel_min'] or
                            obj_to_update.waterlevel_max != data_row['waterlevel_max'] or
                            obj_to_update.waterlevel_mean != data_row['waterlevel_mean']):

                            obj_to_update.waterlevel_min = data_row['waterlevel_min']
                            obj_to_update.waterlevel_max = data_row['waterlevel_max']
                            obj_to_update.waterlevel_mean = data_row['waterlevel_mean']
                            experimental_forecasts_for_update_list.append(obj_to_update)
                            logger.debug(f"Forecast for {common_key} added to update list.")
                    else:
                        experimental_forecasts_for_create.append(
                            WaterLevelForecastsExperimentals(
                                station_id=station_obj,
                                forecast_date=data_row['date_time'],
                                waterlevel_min=data_row['waterlevel_min'],
                                waterlevel_max=data_row['waterlevel_max'],
                                waterlevel_mean=data_row['waterlevel_mean']
                            )
                        )
                        logger.debug(f"Forecast for {common_key} added to create list.")
                else:
                    logger.debug(f"Skipping forecast processing for {common_key} as waterlevel_mean is None.")


                # --- Process Observation Data ---
                if data_row['waterlevel_obs'] is not None:
                    if common_key in existing_experimental_observation_map:
                        obj_to_update = existing_experimental_observation_map[common_key]
                        if obj_to_update.water_level != data_row['waterlevel_obs']:
                            obj_to_update.water_level = data_row['waterlevel_obs']
                            experimental_observations_for_update_list.append(obj_to_update)
                            logger.debug(f"Observation for {common_key} added to update list.")
                    else:
                        experimental_observations_for_create.append(
                            WaterLevelObservationExperimentals(
                                station_id=station_obj,
                                observation_date=data_row['date_time'],
                                water_level=data_row['waterlevel_obs']
                            )
                        )
                        logger.debug(f"Observation for {common_key} added to create list.")
                else:
                    logger.debug(f"Skipping observation processing for {common_key} as waterlevel_obs is None.")


                progress_recorder.set_progress(
                    40 + int((i + 1) * 50 / total_processed_rows),
                    100,
                    description=f"Preparing {i + 1}/{total_processed_rows} records for DB for {station_name}"
                )

            # --- Perform Bulk Operations for Forecasts ---
            if experimental_forecasts_for_create:
                logger.info(f"Attempting bulk_create for {len(experimental_forecasts_for_create)} experimental forecasts.")
                WaterLevelForecastsExperimentals.objects.bulk_create(experimental_forecasts_for_create, ignore_conflicts=True)
                inserted_forecast_count = len(experimental_forecasts_for_create)

            if experimental_forecasts_for_update_list:
                logger.info(f"Attempting bulk_update for {len(experimental_forecasts_for_update_list)} experimental forecasts.")
                updated_forecast_count = WaterLevelForecastsExperimentals.objects.bulk_update(
                    experimental_forecasts_for_update_list,
                    fields=['waterlevel_min', 'waterlevel_max', 'waterlevel_mean']
                )
                logger.debug(f"Bulk_update completed for forecasts. Actual updated: {updated_forecast_count}")
            else:
                logger.info("No experimental forecasts needed updating.")


            # --- Perform Bulk Operations for Observations ---
            if experimental_observations_for_create:
                logger.info(f"Attempting bulk_create for {len(experimental_observations_for_create)} experimental observations.")
                WaterLevelObservationExperimentals.objects.bulk_create(experimental_observations_for_create, ignore_conflicts=True)
                inserted_observation_count = len(experimental_observations_for_create)
            if experimental_observations_for_update_list:
                logger.info(f"Attempting bulk_update for {len(experimental_observations_for_update_list)} experimental observations.")
                updated_observation_count = WaterLevelObservationExperimentals.objects.bulk_update(
                    experimental_observations_for_update_list,
                    fields=['water_level']
                )
                logger.debug(f"Bulk_update completed for observations. Actual updated: {updated_observation_count}")
            else:
                logger.info("No experimental observations needed updating.")

            progress_recorder.set_progress(90, 100, description=f"Database operations complete for {station_name}.")

        result_message = (
            f"Processed Experimental Data for {station_name}: "
            f"Forecasts: {inserted_forecast_count} inserted, {updated_forecast_count} updated. "
            f"Observations: {inserted_observation_count} inserted, {updated_observation_count} updated. "
            f"Total skipped rows (parsing errors/missing stations): {skipped_rows_count}. "
            f"Total file rows: {total_initial_rows}."
        )
        logger.info(result_message)

        self.update_state(
            state=states.SUCCESS,
            meta={
                'message': result_message,
                'inserted_forecasts': inserted_forecast_count,
                'updated_forecasts': updated_forecast_count,
                'inserted_observations': inserted_observation_count,
                'updated_observations': updated_observation_count,
                'skipped_rows': skipped_rows_count,
                'total_rows': total_initial_rows
            }
        )
        return {
            "inserted_forecasts": inserted_forecast_count,
            "updated_forecasts": updated_forecast_count,
            "inserted_observations": inserted_observation_count,
            "updated_observations": updated_observation_count,
            "skipped_rows": skipped_rows_count,
            "total_rows": total_initial_rows,
            "state": states.SUCCESS
        }

    except Ignore:
        logger.warning(f"Task for {station_name} ignored based on task logic.")
        self.update_state(state=states.REVOKED, meta={'message': f"Task for {station_name} ignored."})
        return None

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message_for_log = f"Task for {station_name} failed: {e}\n{error_traceback}"
        logger.error(error_message_for_log)

        self.update_state(state=states.FAILURE, meta={'message': str(e), 'percent': 100})

        return None

    