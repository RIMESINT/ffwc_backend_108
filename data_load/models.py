from django.db import models
from django.conf import settings
# from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder


class FloodAlertDisclaimer(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.CharField(max_length=5000)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'flood_alert_disclaimer'
        verbose_name = "Flood Alerts Disclaimer Item"
        verbose_name_plural = "Flood Alerts Disclaimer"

    def __str__(self):
        return self.message


class Messages(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.CharField(max_length=5000)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'Messages'
        verbose_name = "Message Item"
        verbose_name_plural = "Message"

    def __str__(self):
        return self.message

class ScrollerMessages(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.CharField(max_length=5000)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'scroller_messages'
        verbose_name = "Scroller Message"
        verbose_name_plural = "Scroller Messages"

    def __str__(self):
        return self.message

class SecondScrollerMessages(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.CharField(max_length=5000)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'second_scroller_messages'
        verbose_name = "Secondary Scroller Message"
        verbose_name_plural = "Secondary Scroller Messages"

    def __str__(self):
        return self.message


class FfwcLastUpdateDate(models.Model):
    last_update_date = models.DateField()
    # entry_date = models.DateTimeField()
    entry_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Delete any existing record to ensure only one record exists
        FfwcLastUpdateDate.objects.all().delete()
        super(FfwcLastUpdateDate, self).save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'ffwc_last_update_date'
        verbose_name = "Last Update Date"
        verbose_name_plural = "Last Update Dates"



class FfwcLastUpdateDateExperimental(models.Model):
    last_update_date = models.DateField()
    entry_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Delete any existing record to ensure only one record exists
        FfwcLastUpdateDateExperimental.objects.all().delete()
        super(FfwcLastUpdateDateExperimental, self).save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'ffwc_last_update_date_experimental'
        verbose_name = "Experimental Last Update Date"
        verbose_name_plural = "Experimental Last Update Dates"

class Basin(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, null=False)
    name_bn = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'basins'
        verbose_name = "River Basin"
        verbose_name_plural = "River Basins"

    def __str__(self):
        return self.name

class Unit(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, null=False)

    class Meta:
        managed = True
        db_table = 'units'
        verbose_name = "Measurement Unit"
        verbose_name_plural = "Measurement Units"
        

    def __str__(self):
        return self.name

class Station(models.Model):
    id = models.BigAutoField(primary_key=True)
    station_id = models.IntegerField(unique=True, blank=True, null=True)
    station_serial_no = models.IntegerField(blank=True, null=True)
    
    station_code = models.CharField(max_length=10, blank=True, null=True)
    bwdb_id = models.CharField(max_length=10, blank=True, null=True)
    name = models.CharField(max_length=50, null=False)
    name_bn = models.CharField(max_length=50, blank=True, null=True)
    ffdata_header = models.CharField(max_length=50, blank=True, null=True)
    ffdata_header_1 = models.CharField(max_length=50, blank=True, null=True)
    river = models.CharField(max_length=50, null=False)
    river_bn = models.CharField(max_length=50, blank=True, null=True)
    river_chainage = models.CharField(max_length=50, blank=True, null=True)
    basin = models.ForeignKey(Basin, on_delete=models.SET_NULL, blank=True, null=True)
    # basin_bn = models.CharField(max_length=50, blank=True, null=True)
    danger_level = models.FloatField(blank=True, null=True)
    pmdl = models.CharField(max_length=10, blank=True, null=True)
    highest_water_level = models.FloatField(blank=True, null=True)
    highest_water_level_date = models.DateField(blank=True, null=True)
    gauge_shift = models.FloatField(blank=True, null=True)
    gauge_factor = models.FloatField(blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)
    latitude = models.FloatField(null=False)
    longitude = models.FloatField(null=False)
    h_division = models.CharField(max_length=50, blank=True, null=True)
    h_division_bn = models.CharField(max_length=50, blank=True, null=True)
    division = models.CharField(max_length=50, null=False)
    division_bn = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, null=False)
    district_bn = models.CharField(max_length=50, blank=True, null=True)
    upazilla = models.CharField(max_length=50, blank=True, null=True)
    upazilla_bn = models.CharField(max_length=50, blank=True, null=True)
    union = models.CharField(max_length=50, blank=True, null=True)
    union_bn = models.CharField(max_length=50, blank=True, null=True)
    five_days_forecast = models.BooleanField(blank=True, null=True)
    ten_days_forecast = models.BooleanField(blank=True, null=True)
    monsoon_station = models.BooleanField(blank=True, null=True)
    pre_monsoon_station = models.BooleanField(blank=True, null=True)
    dry_period_station = models.BooleanField(blank=True, null=True)
    sms_id = models.CharField(max_length=10, blank=True, null=True)
    msi_date = models.DateField(blank=True, null=True)
    msi_year = models.IntegerField(blank=True, null=True)
    order_up_down = models.IntegerField(blank=True, null=True)
    forecast_observation = models.CharField(max_length=50, blank=True, null=True)
    status = models.BooleanField(default=True, null=False)
    station_order = models.IntegerField(blank=True, null=True)
    medium_range_station = models.BooleanField(blank=True, null=True)
    extended_range_station = models.BooleanField(blank=True, null=True)
    jason_2_satellite_station = models.BooleanField(blank=True, null=True)
    experimental = models.BooleanField(blank=True, null=True)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:

        db_table = 'stations'
        verbose_name = "Waterlevel Station"
        verbose_name_plural = "Waterlevel Stations"


        managed = True
        indexes = [
            models.Index(fields=['name'], name='idx_station_name'),
            models.Index(fields=['station_code'], name='idx_station_st_code'),
            models.Index(fields=['basin'], name='idx_basin_id'),
            models.Index(fields=['station_id'], name='idx_station_id'),
            
            # models.Index(fields=['station_id']),
            models.Index(fields=['station_serial_no'])
        ]

    def __str__(self):
        return self.name


class RainfallStation(models.Model):
    station_id = models.IntegerField(unique=True, blank=True, null=True)  # Maps to previous id
    station_code = models.CharField(max_length=10, blank=True, null=True)  # Maps to st_id
    name = models.CharField(max_length=50, blank=True, null=True)  # Maps to station
    name_bn = models.CharField(max_length=50, blank=True, null=True)  # Maps to dtation_bn
    basin = models.ForeignKey(Basin, on_delete=models.SET_NULL, blank=True, null=True)
    # basin_bn = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    division = models.CharField(max_length=50, blank=True, null=True)
    division_bn = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    district_bn = models.CharField(max_length=50, blank=True, null=True)
    upazilla = models.CharField(max_length=50, blank=True, null=True)
    upazilla_bn = models.CharField(max_length=50, blank=True, null=True)
    header = models.CharField(max_length=50, blank=True, null=True)
    unit = models.CharField(max_length=10, blank=True, null=True)
    status = models.BooleanField(default=True, blank=True, null=True)

    class Meta:
        db_table = 'rainfall_stations'
        managed = True
        indexes = [
            models.Index(fields=['station_code'], name='idx_rainfall_st_code'),
            models.Index(fields=['name'], name='idx_name'),
            models.Index(fields=['station_id'], name='idx_rainfall_station_id'),
        ]
        verbose_name = "Rainfall Monitoring Station"
        verbose_name_plural = "Rainfall Monitoring Stations"


    def __str__(self):
        return self.name or 'Unknown'

class MonthlyRainfall(models.Model):
    station_id = models.IntegerField()
    month_serial = models.IntegerField()
    month_name = models.CharField(max_length=15)
    unit = models.CharField(max_length=10, blank=True, null=True)
    max_rainfall = models.DecimalField(max_digits=8, decimal_places=2)
    normal_rainfall = models.DecimalField(max_digits=8, decimal_places=2)
    min_rainfall = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'monthly_rainfall'
        verbose_name = "Monthly Rainfall"
        verbose_name_plural = "Monthly Rainfalls"

    def __str__(self):
        return f"{self.station_id} - Month {self.month_serial}"


class WaterLevelObservation(models.Model):
    station_id = models.ForeignKey(Station, to_field='station_id', on_delete=models.SET_NULL, blank=True, null=True)
    observation_date = models.DateTimeField()
    water_level = models.DecimalField(max_digits=10, decimal_places=2)
    gauge_reader_water_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    # is_experimental = models.BooleanField(default=False)

    class Meta:
        db_table = 'water_level_observations'
        managed = True
        indexes = [
            models.Index(
                fields=['station_id', '-observation_date'], 
                name='idx_wtrlvl_st_id_date_desc'
            ),
            models.Index(fields=['station_id', 'observation_date'], name='idx_waterlevel_station_id_date'), 
            models.Index(fields=['observation_date']),
            models.Index(fields=['station_id']),
            models.Index(fields=['-station_id', '-observation_date'], name='-idx_wtrl_sta_id_dt_wlo'), 
        ]
        verbose_name = "Water Level Observation"
        verbose_name_plural = "Water Level Observations"

    def __str__(self):
        return f"{self.station_id.name if self.station_id else 'Unknown'} - {self.observation_date}"


class RainfallObservation(models.Model):
    station_id = models.ForeignKey(RainfallStation, on_delete=models.RESTRICT)
    observation_date = models.DateTimeField()
    rainfall = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = 'rainfall_observations'
        managed = True
        indexes = [
            models.Index(fields=['station_id', 'observation_date'], name='idx_rainfall_station_id_date'),
        ]

        verbose_name = "Rainfall Observation"
        verbose_name_plural = "Rainfall Observations"

    def __str__(self):
        return f"{self.station_id.name} - {self.observation_date}"
        

class WaterLevelForecast(models.Model):
    station_id = models.ForeignKey(Station, to_field='station_id', on_delete=models.RESTRICT)
    forecast_date = models.DateTimeField()
    water_level = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'water_level_forecasts'
        managed = True

        unique_together = ('station_id', 'forecast_date') 

        indexes = [
            models.Index(fields=['station_id', 'forecast_date'], name='idx_station_id_forecast_date'),
        ]
        verbose_name = "Water Level Forecast"
        verbose_name_plural = "Water Level Forecasts"

    def __str__(self):
        return f"{self.station_id.name} - {self.forecast_date}"


class WaterLevelObservationExperimentals(models.Model):

    station_id = models.ForeignKey('Station', to_field='station_id',on_delete=models.RESTRICT,)
    observation_date = models.DateTimeField()
    water_level = models.DecimalField(max_digits=10, decimal_places=2) 

    class Meta:
        managed = True
        db_table = 'water_level_observation_experimentals'
        verbose_name = "Water Level Observation (Experimental)"
        verbose_name_plural = "Water Level Observations (Experimental)"
        # Add a unique constraint to prevent duplicate observations for the same station and date
        constraints = [
            models.UniqueConstraint(fields=['station_id', 'observation_date'], name='unique_experimental_observation'),
        ]
        indexes = [
            models.Index(fields=['station_id', 'observation_date'], name='idx_exp_obs_stid_obsdate'),
        ]

    def __str__(self):
        return f"{self.station_id.name} - {self.observation_date} - {self.water_level} (Experimental Observation)"


class WaterLevelForecastsExperimentals(models.Model):
    id = models.AutoField(primary_key=True)
    station_id = models.ForeignKey('Station', to_field='station_id', on_delete=models.RESTRICT) # Changed 'Station' to string to avoid circular import if Station is in same models.py
    forecast_date = models.DateTimeField()

    waterlevel_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    waterlevel_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    waterlevel_mean = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'water_level_forecast_experimentals'
        # Add a unique constraint to prevent duplicate forecasts for the same station and date
        constraints = [
            models.UniqueConstraint(fields=['station_id', 'forecast_date'], name='unique_experimental_forecast'),
        ]
        indexes = [
            models.Index(fields=['station_id', 'forecast_date'], name='idx_exp_stid_fcdate'),
        ]
        verbose_name = "Water Level Forecast (Experimental)"
        verbose_name_plural = "Water Level Forecasts (Experimental)"

    def __str__(self):
        return f"{self.station_id.name} - {self.forecast_date} (Experimental)"


class ThresholdBasins(models.Model):
    id = models.AutoField(primary_key=True)
    basin_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'threshold_basins'
        managed = True

    def __str__(self):
        return self.basin_name

class UKMetMonsoonBasinWiseFlashFloodForecast(models.Model):
    prediction_date = models.DateField()
    basin_id = models.IntegerField()
    date = models.DateField()
    hours = models.IntegerField()
    thresholds = models.FloatField()
    value = models.FloatField()

    class Meta:
        db_table = 'ukmet_monsoon_basin_wise_flash_flood_forecast'
        managed = True

    def __str__(self):
        return f"Basin {self.basin_id} - {self.hours} hours"


class BMDWRFMonsoonBasinWiseFlashFloodForecast(models.Model):
    prediction_date = models.DateField()
    basin_id = models.IntegerField()
    date = models.DateField()
    hours = models.IntegerField()
    thresholds = models.FloatField()
    value = models.FloatField()

    class Meta:
        db_table = 'bmd_wrf_monsoon_basin_wise_flash_flood_forecast'
        managed = True

    def __str__(self):
        return f"Basin {self.basin_id} - {self.hours} hours"
        
class MonsoonBasinWiseFlashFloodForecast(models.Model):
    prediction_date = models.DateField()
    basin_id = models.IntegerField()
    date = models.DateField()
    hours = models.IntegerField()
    thresholds = models.FloatField()
    value = models.FloatField()

    class Meta:
        db_table = 'monsoon_basin_wise_flash_flood_forecast'
        managed = True

    def __str__(self):
        return f"Basin {self.basin_id} - {self.hours} hours"


class MonsoonProbabilisticFlashFloodForecast(models.Model):
    prediction_date = models.DateField()
    basin_id = models.IntegerField()
    date = models.DateField()
    hours = models.IntegerField()
    thresholds = models.FloatField()
    value = models.FloatField()

    class Meta:
        db_table = 'monsoon_probabilistic_flash_flood_forecast'
        managed = True

    def __str__(self):
        return f"Basin {self.basin_id} - {self.hours} hours"

class UKMetMonsoonProbabilisticFlashFloodForecast(models.Model):
    prediction_date = models.DateField()
    basin_id = models.IntegerField()
    date = models.DateField()
    hours = models.IntegerField()
    thresholds = models.FloatField()
    value = models.FloatField()

    class Meta:
        db_table = 'ukmet_monsoon_probabilistic_flash_flood_forecast'
        managed = True

    def __str__(self):
        return f"Basin {self.basin_id} - {self.hours} hours"


from django.core.serializers.json import DjangoJSONEncoder
class FloodReport(models.Model):
    report_date = models.DateField(unique=True, help_text="Date of the flood report")
    generated_at = models.DateTimeField(auto_now_add=True)
    report_data = models.JSONField(encoder=DjangoJSONEncoder)
    api_data = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
    processing_time = models.FloatField(default=0, help_text="Processing time in seconds")

    class Meta:
        ordering = ['-report_date']
        indexes = [
            models.Index(fields=['report_date']),
        ]

    def __str__(self):
        return f"Flood Report - {self.report_date}"




class FloodSummaryReport(models.Model):
    report_date = models.DateField(unique=True, help_text="The date for which the flood summary report is generated.")
    summary_data = models.JSONField(help_text="Stores the comprehensive flood summary report data in JSON format.")
    generated_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the report was first generated.")
    processing_time = models.FloatField(null=True, blank=True, help_text="Time taken to generate the report in seconds.")


    class Meta:
        verbose_name = "Flood Summary Report"
        verbose_name_plural = "Flood Summary Reports"
        ordering = ['-report_date'] # Order by most recent reports first

    def __str__(self):
        return f"Flood Summary Report for {self.report_date}"


class WaterlevelAlert(models.Model):
    alert_no = models.IntegerField(unique=True) # Now alert_no should be unique but not the primary key
    alert_type = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = True
        db_table = 'waterlevel_alert'
        verbose_name = 'Water Level Alert'
        verbose_name_plural = 'Water Level Alerts'

    def __str__(self):
        return self.alert_type

class DistrictFloodAlert(models.Model):
    alert_date = models.DateField()
    district_name = models.CharField(max_length=100)
    alert_type = models.ForeignKey(WaterlevelAlert, on_delete=models.CASCADE, to_field='alert_type')

    class Meta:
        managed = True
        db_table = 'district_flood_alert'
        verbose_name = 'District Flood Alert'
        verbose_name_plural = 'District Flood Alerts'
        # CHANGE THIS LINE: Remove 'alert_type' from unique_together
        unique_together = ('alert_date', 'district_name') # Now, only one entry per date and district

    def __str__(self):
        return f"ID: {self.id}, Date: {self.alert_date}, District: {self.district_name}, Alert Type: {self.alert_type.alert_type}"


from django.core.files.storage import default_storage
class Floodmaps(models.Model):
    file_name = models.CharField(max_length=255, blank=True)  # Make blank=True as it will be derived from the file
    file_date = models.DateField()
    file = models.FileField(upload_to='floodMaps/', null=True, blank=True)

    def save(self, *args, **kwargs):
        # If no file_name is provided, use the uploaded file's name
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name)

        # Handle file replacement/deletion of old file if it's an update
        if self.pk:
            old_instance = Floodmaps.objects.get(pk=self.pk)
            if old_instance.file and old_instance.file != self.file:
                # Delete the old file from storage if it exists and is different
                if default_storage.exists(old_instance.file.path):
                    default_storage.delete(old_instance.file.path)
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete the associated file from storage when the model instance is deleted
        if self.file:
            if default_storage.exists(self.file.path):
                default_storage.delete(self.file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.file_name if self.file_name else "No File Name"

    class Meta:
        # managed = False # Remove this line so Django manages the table
        db_table = 'floodmaps'



class MonsoonConfig(models.Model):
    config_year = models.IntegerField()
    title = models.CharField(max_length=50)
    sort_order = models.IntegerField()
    color = models.CharField(max_length=15)
    is_active = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'monsoon_config'
        unique_together = (('config_year', 'title'),)
        


class BulletinRelatedManue(models.Model):
    title = models.CharField(max_length=1024)
    title_bn = models.CharField(max_length=1024)
    url = models.TextField()

    def __str__(self):
        return self.title

    class Meta:
        # db_table = 'monsoon_probabilistic_flash_flood_forecast'
        # managed = True
        verbose_name = "Bulletin Related Manue"
        verbose_name_plural = "Bulletin Related Manues"
        
        


class StationSummaryMobileV1(models.Model):
    """
    Read-only model mapped to MySQL view `station_summary_view_mobile_v1`.
    station_id is used as primary key for easy lookups in DRF.
    """
    station_id = models.BigIntegerField(primary_key=True)
    station_pk = models.BigIntegerField(null=True)
    station_code = models.CharField(max_length=255, null=True)
    name = models.CharField(max_length=1024, null=True)
    name_bn = models.CharField(max_length=1024, null=True)
    station_serial_no = models.IntegerField(null=True)
    danger_level = models.FloatField(null=True)
    highest_water_level = models.FloatField(null=True)
    highest_water_level_date = models.DateTimeField(null=True)
    gauge_shift = models.FloatField(null=True)

    # admin & location
    h_division = models.CharField(max_length=255, null=True)
    h_division_bn = models.CharField(max_length=255, null=True)
    division = models.CharField(max_length=255, null=True)
    division_bn = models.CharField(max_length=255, null=True)
    district = models.CharField(max_length=255, null=True)
    district_bn = models.CharField(max_length=255, null=True)
    upazilla = models.CharField(max_length=255, null=True)
    upazilla_bn = models.CharField(max_length=255, null=True)
    union = models.CharField(max_length=255, null=True)
    union_bn = models.CharField(max_length=255, null=True)
    river = models.CharField(max_length=255, null=True)
    river_bn = models.CharField(max_length=255, null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)

    # boolean flags stored as tinyint/bool in the view
    five_days_forecast = models.BooleanField(null=True, blank=True)  # Django <4.0; for Django>=4.0 use BooleanField(null=True)
    ten_days_forecast = models.BooleanField(null=True, blank=True)
    monsoon_station = models.BooleanField(null=True, blank=True)
    pre_monsoon_station = models.BooleanField(null=True, blank=True)
    dry_period_station = models.BooleanField(null=True, blank=True)

    # basin
    basin = models.CharField(max_length=255, null=True)
    basin_bn = models.CharField(max_length=255, null=True)

    # water-level fields from the view
    last_water_level = models.FloatField(null=True)
    last_observation_date = models.DateTimeField(null=True)
    previous_water_level = models.FloatField(null=True)
    previous_observation_date = models.DateTimeField(null=True)
    level_difference = models.FloatField(null=True)
    status_name = models.CharField(max_length=32, null=True)

    water_level_24_hours_ago = models.FloatField(null=True)
    water_level_24_hours_ago_observation_date = models.DateTimeField(null=True)
    difference_water_level_24_hours = models.FloatField(null=True)

    station_flood_status = models.CharField(max_length=32, null=True)

    class Meta:
        managed = False
        db_table = 'station_summary_view_mobile_v1'
        ordering = ['station_serial_no']

    def __str__(self):
        return f"{self.station_id} - {self.name}"


class StationSummaryViewMobileV1(models.Model):
    """Unmanaged model mapped to MySQL VIEW `station_summary_view_mobile_v1`.
    Includes all 59 columns from the view.
    """

    id = models.BigIntegerField(primary_key=True)
    station_id = models.IntegerField(null=True, blank=True)
    station_code = models.CharField(max_length=10, null=True, blank=True)
    bwdb_id = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=50)
    name_bn = models.CharField(max_length=50, null=True, blank=True)
    ffdata_header = models.CharField(max_length=50, null=True, blank=True)
    ffdata_header_1 = models.CharField(max_length=50, null=True, blank=True)
    river = models.CharField(max_length=50)
    river_bn = models.CharField(max_length=50, null=True, blank=True)
    river_chainage = models.CharField(max_length=50, null=True, blank=True)
    danger_level = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    pmdl = models.CharField(max_length=10, null=True, blank=True)
    highest_water_level = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    highest_water_level_date = models.DateField(null=True, blank=True)
    gauge_shift = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    gauge_factor = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    h_division = models.CharField(max_length=50, null=True, blank=True)
    h_division_bn = models.CharField(max_length=50, null=True, blank=True)
    division = models.CharField(max_length=50)
    division_bn = models.CharField(max_length=50, null=True, blank=True)
    district = models.CharField(max_length=50)
    district_bn = models.CharField(max_length=50, null=True, blank=True)
    upazilla = models.CharField(max_length=50, null=True, blank=True)
    upazilla_bn = models.CharField(max_length=50, null=True, blank=True)
    union = models.CharField(max_length=50, null=True, blank=True)
    union_bn = models.CharField(max_length=50, null=True, blank=True)

    five_days_forecast = models.BooleanField(null=True)
    ten_days_forecast = models.BooleanField(null=True)
    monsoon_station = models.BooleanField(null=True)
    pre_monsoon_station = models.BooleanField(null=True)
    dry_period_station = models.BooleanField(null=True)
    sms_id = models.CharField(max_length=10, null=True, blank=True)
    msi_date = models.DateField(null=True, blank=True)
    msi_year = models.IntegerField(null=True, blank=True)
    order_up_down = models.IntegerField(null=True, blank=True)
    forecast_observation = models.CharField(max_length=50, null=True, blank=True)
    status = models.BooleanField(default=False)
    station_order = models.IntegerField(null=True, blank=True)
    medium_range_station = models.BooleanField(null=True)
    jason_2_satellite_station = models.BooleanField(null=True)
    experimental = models.BooleanField(null=True)
    basin_id = models.BigIntegerField(null=True, blank=True)
    unit_id = models.BigIntegerField(null=True, blank=True)
    extended_range_station = models.BooleanField(null=True)
    station_serial_no = models.IntegerField(null=True, blank=True)

    last_observation_date = models.DateTimeField(null=True, blank=True)
    last_water_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    previous_observation_date = models.DateTimeField(null=True, blank=True)
    previous_water_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    water_level_24_hours_ago_observation_date = models.DateTimeField(null=True, blank=True)
    water_level_24_hours_ago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status_name = models.CharField(max_length=16, null=True, blank=True)
    station_flood_status = models.CharField(max_length=16, null=True, blank=True)
    level_difference = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    difference_water_level_24_hours = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'station_summary_view_mobile_v1'
        ordering = ['-last_observation_date']

    def __str__(self):
        return f"{self.station_code or self.bwdb_id or self.id} - {self.name}"

        

class ScheduledTask(models.Model):
    task_name = models.CharField(max_length=100, unique=True, help_text="A unique identifier for the task")
    is_enabled = models.BooleanField(default=True, help_text="Uncheck this to disable the scheduled task.")
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.task_name} - {'Enabled' if self.is_enabled else 'Disabled'}"

    class Meta:
        verbose_name = "Scheduled Task Status"
        verbose_name_plural = "Scheduled Task Statuses"


class DistrictFloodAlertAutoUpdate(models.Model):
    
    district_name = models.CharField(max_length=100)
    auto_update = models.BooleanField(default=True)

    def __str__(self):
        return self.district_name


class JsonEntry(models.Model):
    # This single field will store the entire JSON object.
    data = models.JSONField()

    def __str__(self):
        # We can try to get an ID from the JSON data if it exists for a better admin display
        entry_id = self.id
        return f"JSON Entry ID: {entry_id}"





"""
    ################################################################
    ### Added by SHAIF | Date: 2025-AUG-19
    ### Assigned by Sajib Bhai
    ################################################################
""" 
class EnsModelChoice(models.Model):
    """
    Represents the choice of an ensemble model for a specific station and date.
    """
    station_id = models.IntegerField(
        help_text="The ID of the station.",
        null=True, blank=True,
    )
    date = models.DateTimeField(
        help_text="The date and time for which the model was chosen.",
        null=True, blank=True,
    )
    model_name = models.CharField(
        max_length=1024, 
        help_text="The name of the chosen model (e.g., 'ECMWF-ENS', 'GEFS').",
        null=True, blank=True,
    )

    class Meta: 
        db_table = 'ens_model_choice' 
        verbose_name = "Ensemble Model Choice"
        verbose_name_plural = "Ensemble Model Choices" 
        # unique_together = ('station_id', 'date')

    def __str__(self): 
        return f"{self.model_name} for station {self.station_id} on {self.date.strftime('%Y-%m-%d')}"




