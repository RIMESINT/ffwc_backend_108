from django.db import models









# Create your models here.
class SourceDataType(models.Model):
    """ 
        Purpose: Source Data Type of weather data table
    """

    name      = models.CharField('Source Data Type Name',max_length=128, null=True, blank=True)


    def __str__(self):
        return f'{self.name}'
    
    class Meta: 
        verbose_name = "Source Data Type"
        verbose_name_plural = "Source Data Types" 



class BasinDetails(models.Model):
    """ 
        Purpose: Name of data source table
    """

    name = models.CharField('Forecast Source Name',max_length=128)
    shape_file_path = models.CharField('Path of the shape file',max_length=4096, blank=True, null=True)
    destination_path = models.CharField('Path of the destination file',max_length=4096, blank=True, null=True)  

    def __str__(self):
        return f'{self.name}'

    class Meta: 
        verbose_name = "Source"
        verbose_name_plural = "Sources"
        # indexes = [
        #     models.Index(fields=['name', 'country'], name='source_nmcon_idx'),   
        # ]


class Parameter(models.Model):
    """ 
        Purpose: Parameters of weather data table
    """

    name      = models.CharField('Parameter Name',max_length=128, null=True, blank=True)
    full_name = models.CharField('Full Parameter Name',max_length=256, null=True, blank=True)
    unit      = models.CharField('Parameter Unit',max_length=32, null=True, blank=True)


    def __str__(self):
        return f'{self.name}//{self.unit}'
    
    class Meta: 
        verbose_name = "Parameter"
        verbose_name_plural = "Parameters"
        indexes = [
            models.Index(fields=['name'], name='param_name_idx'),   
        ]



class Source(models.Model):
    """ 
        Purpose: Name of data source table
    """

    name = models.CharField('Forecast Source Name',max_length=128)
    name_visualize = models.CharField(
        'Forecast Source Name for visualization', max_length=128,
        blank=True, null=True
    )
    source_path = models.CharField('Path of the source file',max_length=4096, blank=True, null=True)
    destination_path = models.CharField(
        'Path of the destination file', max_length=4096, 
        blank=True, null=True
    ) 

    source_type = models.CharField('Type of Source',max_length=128, blank=True, null=True)
    source_data_type = models.ForeignKey(
        SourceDataType, on_delete=models.CASCADE, 
        related_name='source_data_type_id',
        null=True, blank=True
    ) 

    def __str__(self):
        return f'{self.name}//{self.source_type}//{self.source_data_type.name}'


    class Meta: 
        verbose_name = "Source"
        verbose_name_plural = "Sources"
        # indexes = [
        #     models.Index(fields=['name', 'country'], name='source_nmcon_idx'),   
        # ]




class SystemState(models.Model):
    """
        Last updated info of various sources 
    """

    name = models.CharField('name of state', max_length=256) 
    source        = models.ForeignKey(Source, on_delete=models.CASCADE)
    last_update   = models.DateTimeField('Last Update Date')
    updated_at    = models.DateTimeField('Last modification made', auto_now=True)

    def __str__(self):
        return f'{self.source.name}//{self.last_update}' 
    
    class Meta: 
        verbose_name = "System State"
        verbose_name_plural = "System States"






class ForecastSteps(models.Model):
    """
        Purpose: Table for forcast data on 3 hourly basis
    """

    # generally contain all steps of first day
    parameter     = models.ForeignKey(Parameter,on_delete=models.CASCADE, null=True, blank=True)
    source        = models.ForeignKey(Source,on_delete=models.CASCADE, null=True, blank=True)
    
    basin_details = models.ForeignKey(
        BasinDetails, on_delete=models.CASCADE, related_name='forecast_step_basin_id',
        null=True, blank=True
    )

    # location      = models.ForeignKey(
    #     GeoData,on_delete=models.CASCADE, null=True, blank=True, 
    #     related_name='forecast_step_location_id'
    # )
    # country      = models.ForeignKey(
    #     GeoData, on_delete=models.CASCADE, null=True, blank=True, 
    #     related_name='forecast_step_country_id',
    #     limit_choices_to={'parent': BD['Country']['parent_id']}
    # )
    # level         = models.ForeignKey(GeoLevel, on_delete=models.CASCADE, null=True, blank=True)

    forecast_date = models.DateField('Date of Forecast Generation', null=True, blank=True)
    step_start    = models.DateTimeField('Forecast step start time', null=True, blank=True)
    step_end      = models.DateTimeField('Forecast step end time', null=True, blank=True)
    val_min       = models.FloatField('Min Value/Instant value(dir)', null=True, blank=True)
    val_avg		  = models.FloatField('Average Value,', null=True, blank=True)
    val_max		  = models.FloatField('Max,accumulated', null=True, blank=True)

    class Meta:
        # indexes = [ 
        #     models.Index(fields=['forecast_date'], name='frcst_stp_fdt_idx'),
        #     models.Index(fields=['source'], name='frcst_stp_sorcon_idx'),
        #     models.Index(fields=['source', 'parameter', 'basin_details', 'forecast_date'], name='frcst_stp_lscplf_idx'),
        #     models.Index(fields=['source', 'parameter', 'forecast_date'], name='frcst_stp_lscpf_idx'),
        #     models.Index(fields=['source', 'basin_details', 'parameter', 'forecast_date'], name='frcst_stp_slpfdt_idx'),
        # ]
        verbose_name = "Forecast Steps"
        verbose_name_plural = "Forecast Steps"

    def __str__(self):
        return f'{self.parameter.name}//{self.forecast_date}//{self.basin_details.name}'


class ForecastDaily(models.Model):
    """
        Purpose: Table for forcast data on daily basis storage
    """
	
    parameter     = models.ForeignKey(Parameter,on_delete=models.CASCADE, null=True, blank=True)
    source        = models.ForeignKey(Source,on_delete=models.CASCADE, null=True, blank=True)
    
    basin_details = models.ForeignKey(
        BasinDetails, on_delete=models.CASCADE, related_name='forecast_daily_basin_id',
        null=True, blank=True
    )

    # location      = models.ForeignKey(
    #     GeoData,on_delete=models.CASCADE, related_name='forecast_daily_location_id',
    #     null=True, blank=True
    # )
    # country      = models.ForeignKey(
    #     GeoData, on_delete=models.CASCADE, null=True, blank=True, 
    #     related_name='forecast_daily_country_id',
    #     limit_choices_to={'parent': BD['Country']['parent_id']}
    # )
    # level         = models.ForeignKey(GeoLevel, on_delete=models.CASCADE, null=True, blank=True)

    forecast_date = models.DateField('Date of Forecast Generation', null=True, blank=True)
    step_start    = models.DateTimeField('Forecast step start time', null=True, blank=True)
    step_end      = models.DateTimeField('Forecast step end time', null=True, blank=True)
    val_min       = models.FloatField('Min Value/Instant value(dir)', null=True, blank=True)
    val_avg		  = models.FloatField('Average Value,', null=True, blank=True)
    val_max		  = models.FloatField('Max,accumulated', null=True, blank=True)
    val_avg_day   = models.FloatField('Average of day', null=True, blank=True)
    val_avg_night = models.FloatField('Average of night', null=True, blank=True)
    # et0           = models.FloatField('Evapotranspiration', null=True, blank=True)

    class Meta:
        # indexes = [ 
        #     models.Index(fields=['forecast_date'], name='frcst_dly_fdt_idx'), 
        #     models.Index(fields=['source', 'basin_details'], name='frcst_dly_sorcon_idx'),
        #     models.Index(fields=['source', 'basin_details', 'parameter', 'forecast_date'], name='frcst_dly_lscplf_idx'),
        #     models.Index(fields=['source', 'basin_details', 'parameter', 'forecast_date'], name='frcst_dly_lscpf_idx'),
        #     models.Index(fields=['source', 'basin_details', 'parameter', 'forecast_date'], name='frcst_dly_slpfdt_idx'),
        # ]
        verbose_name = "Forecast Daily"
        verbose_name_plural = "Forecast Daily"


    def __str__(self):
        return f'{self.parameter.name}//{self.forecast_date}//{self.basin_details.name}'



# class FfwcRainfallStations(models.Model):
#     name = models.CharField(unique=True, max_length=50, blank=True, null=True)
#     basin = models.CharField(max_length=150, blank=True, null=True)
#     division = models.CharField(max_length=50, blank=True, null=True)
#     district = models.CharField(max_length=50, blank=True, null=True)
#     upazilla = models.CharField(max_length=50, blank=True, null=True)
#     lat = models.CharField(max_length=20, blank=True, null=True)
#     long = models.CharField(max_length=20, blank=True, null=True)
#     # altitude = models.CharField(max_length=20, blank=True, null=True)
#     status = models.IntegerField(blank=True, null=True)
#     unit = models.CharField(max_length=10, blank=True, null=True)
#     # observe_data_source = models.ForeignKey(
#     #     Source, on_delete=models.CASCADE, 
#     #     related_name='agromet_rf_station_data_source_info',
#     #     null=True, blank=True
#     # )
#     # observe_data_source_network = models.CharField( 
#     #     max_length=1024,
#     #     null=True, blank=True
#     # )


#     class Meta:
#         managed = True      # False 
#         db_table = 'ffwc_rainfall_stations'
#         # verbose_name = "Rainfall Station"
#         # verbose_name_plural = "Rainfall Stations"

class FfwcRainfallStation(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    basin = models.CharField(max_length=150, null=True, blank=True)
    division = models.CharField(max_length=50, default='', null=True, blank=True)
    district = models.CharField(max_length=50, null=True, blank=True)
    upazilla = models.CharField(max_length=50, null=True, blank=True)
    lat = models.CharField(max_length=20, null=True, blank=True)
    long = models.CharField(max_length=20, null=True, blank=True)
    altitude = models.CharField(max_length=20, blank=True, null=True)
    status = models.IntegerField(default=1, null=True, blank=True)
    unit = models.CharField(max_length=10, null=True, blank=True)
    observe_data_source = models.ForeignKey(
        Source, on_delete=models.CASCADE, 
        related_name='agromet_rf_station_data_source_info',
        null=True, blank=True
    )
    observe_data_source_network = models.CharField( 
        max_length=1024,
        null=True, blank=True
    ) 
    basin_details = models.ForeignKey(
        BasinDetails, on_delete=models.CASCADE, 
        related_name='basin_wise_rf_obs_info',
        null=True, blank=True
    )

    class Meta:
        # db_table = 'ffwc_rainfall_stations'
        # managed = False 
        verbose_name = "Rainfall Station"
        verbose_name_plural = "Rainfall Stations"

    def __str__(self):
        return self.name


class RainfallObservation(models.Model):
    rf_id = models.AutoField(primary_key=True)
    # st_id = models.IntegerField()
    st = models.ForeignKey(
        FfwcRainfallStation, on_delete=models.CASCADE, 
        related_name='rf_observation_station_wise_info',
        null=True, blank=True
    )
    rf_date = models.DateTimeField()
    rainFall = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        # db_table = 'rainfall_observations'
        # managed = False
        verbose_name = 'Rainfall Observation'
        verbose_name_plural = 'Rainfall Observations'
        # indexes = [ 
        #     models.Index(fields=['st_id'], name='st_idx'),
        #     # models.Index(fields=['st_id', 'rf_date'], name='st_rf_idx'),
        # ] 
        # unique_together = ('st_id', 'rf_date')




class StreamFlowStation(models.Model):
    # id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    file_name = models.CharField(max_length=50, null=True, blank=True)
    file_path = models.CharField(max_length=50, null=True, blank=True)
    station_id = models.CharField(max_length=150, null=True, blank=True)
    division = models.CharField(max_length=50, default='', null=True, blank=True)
    district = models.CharField(max_length=50, null=True, blank=True)
    upazilla = models.CharField(max_length=50, null=True, blank=True)
    river_name = models.CharField(max_length=50, null=True, blank=True)
    lat = models.CharField(max_length=20, null=True, blank=True)
    long = models.CharField(max_length=20, null=True, blank=True)
    altitude = models.CharField(max_length=20, blank=True, null=True)
    status = models.IntegerField(default=1, null=True, blank=True)
    unit = models.CharField(max_length=10, null=True, blank=True)
    forecast_data_source = models.ForeignKey(
        Source, on_delete=models.CASCADE, 
        related_name='streamflow_station_data_source_info',
        null=True, blank=True
    )

    class Meta: 
        # managed = False 
        verbose_name = "Stream Flow Station"
        verbose_name_plural = "Stream Flow Stations"

    def __str__(self):
        return f"{self.name}/{self.station_id}/{self.lat}/{self.long}"