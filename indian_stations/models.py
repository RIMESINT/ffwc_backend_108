from django.db import models

class IndianStations(models.Model):
    id = models.BigAutoField(primary_key=True)
    station_name = models.CharField(max_length=100)
    state_name = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    basin_name = models.CharField(max_length=100)
    river_name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    division_name = models.CharField(max_length=150, blank=True, null=True)
    type_of_site = models.CharField(max_length=100, blank=True, null=True)
    distance = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    within_ganges = models.CharField(max_length=100, blank=True, null=True)
    within_brahmaputra = models.CharField(max_length=100, blank=True, null=True)
    within_meghna = models.CharField(max_length=100, blank=True, null=True)
    station_code = models.CharField(max_length=100, unique=True)
    dangerlevel = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    warning_level = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    highest_flow_level = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'indian_stations'
        verbose_name = "Indian Station"
        verbose_name_plural = "Indian Stations"
        indexes = [
            models.Index(fields=['station_code'], name='idx_indian_station_code'),
            models.Index(fields=['station_name'], name='idx_indian_station_name'),
            models.Index(fields=['basin_name'], name='idx_indian_basin_name'),
        ]

    def __str__(self):
        return self.station_name

class IndianWaterLevelObservations(models.Model):
    id = models.BigAutoField(primary_key=True)
    station = models.ForeignKey(IndianStations, on_delete=models.DO_NOTHING, db_column='station_id')
    data_time = models.DateTimeField()
    waterlevel = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'indian_water_level_observations'
        verbose_name = "Indian Water Level Observation"
        verbose_name_plural = "Indian Water Level Observations"
        indexes = [
            models.Index(fields=['station'], name='idx_water_level_station'),
            models.Index(fields=['data_time'], name='idx_water_level_data_time'),
            models.Index(fields=['station', 'data_time'], name='idx_wl_st_data_time'),
        ]

    def __str__(self):
        return f"{self.station.station_code} - {self.data_time}"