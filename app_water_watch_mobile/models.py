from django.conf import settings
from django.db import models
from data_load.models import WaterLevelObservation



#####################################################################################
#####################################################################################
### API endpoints for managing water level inputs from mobile users.
#####################################################################################
#####################################################################################
class WaterWatchWaterLevelStationForMobileUser(models.Model):
    """
        Maps a MobileAuthUser -> Station (by Station.station_id).
        A single mobile user can have access to multiple stations and
        a station can be assigned to multiple mobile users.
    """
    
    mobile_user = models.ForeignKey(
        'app_user_mobile.MobileAuthUser', 
        on_delete=models.CASCADE,
        related_name='waterwatch_water_level_stations',
        help_text='Reference to MobileAuthUser (mobile user id).'
    )


    water_level_station = models.ForeignKey(
        'data_load.Station',
        to_field='station_id',
        db_column='station_id',
        on_delete=models.CASCADE,
        related_name='mobile_users_water_level_station',
        help_text='References Station.station_id (not the PK).'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # db_table = 'waterwatch_user_station'
        verbose_name = 'Water Watch Water Level Station for Mobile User'
        verbose_name_plural = 'Water Watch Water Level Stations for Mobile User'
        # unique_together = ('mobile_user', 'water_level_station')
        indexes = [
            models.Index(fields=['mobile_user'], name='idx_wu_mobile_user'),
            models.Index(fields=['water_level_station'], name='idx_wu_station'),
        ]

    def __str__(self):
        try:
            user_str = self.mobile_user.mobile_number
        except Exception:
            user_str = str(self.mobile_user_id)
        try:
            station_str = str(self.water_level_station.station_id)
        except Exception:
            station_str = str(self.water_level_station_id)
        return f"{user_str} → station {station_str}"
    


class WaterLevelInputForMobileUser(models.Model):
    """
        Stores water level observations submitted (or assigned) for mobile users.
        - station references data_load.Station by Station.station_id (not the PK).
        - created_by / updated_by reference app_user_mobile.MobileAuthUser.
    """

    station = models.ForeignKey(
        'data_load.Station',
        to_field='station_id',
        db_column='station_id',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='mobile_user_waterlevel_inputs',
        help_text='References Station.station_id (nullable).'
    )

    observation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date and time of observation (24-hour format).'
    )

    water_level = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Water level value; nullable.'
    )

    created_by = models.ForeignKey(
        'app_user_mobile.MobileAuthUser',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='created_waterlevel_inputs',
        help_text='Mobile user who created the record (nullable).'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        'app_user_mobile.MobileAuthUser',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='updated_waterlevel_inputs',
        help_text='Mobile user who last updated the record (nullable).'
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Note: kept the field name 'is_acepted' as requested (typo preserved).
    is_acepted = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    # approved_at = models.DateTimeField(null=True, blank=True)
    # rejected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # db_table = 'waterwatch_waterlevel_input_for_mobile_user'
        verbose_name = 'Water Level Input (Mobile User)'
        verbose_name_plural = 'Water Level Inputs (Mobile Users)'
        indexes = [
            models.Index(fields=['station'], name='idx_wli_station'),
            models.Index(fields=['observation_date'], name='idx_wli_obs_date'),
            models.Index(fields=['created_by'], name='idx_wli_created_by'),
        ]
        ordering = ('-observation_date',)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        old_intance = None
        if self.pk:
            try:
                old_intance = WaterLevelInputForMobileUser.objects.get(pk=self.pk)
            except WaterLevelInputForMobileUser.DoesNotExist:
                old_intance = None

        print("old_intance", old_intance, old_intance.is_approved, self.is_approved)

        if self.is_approved:
            station_id = self.station.station_id if hasattr(self.station, 'station_id') else self.station_id
            
            print("station_id", station_id)
            print("observation_date", self.observation_date)
            print("water_level", self.water_level)

            observation, created = WaterLevelObservation.objects.get_or_create(
                station_id_id=station_id,
                observation_date=self.observation_date,
                defaults={
                    'water_level': -9999.00,
                    'gauge_reader_water_level': self.water_level
                }
            )

            print("observation", observation)
            print("created", created)
            
            if not created:
                observation.gauge_reader_water_level = self.water_level
                observation.save(update_fields=['gauge_reader_water_level'])
                
        # If the record is rejected, clear the gauge_reader_water_level
        elif not self._state.adding and self.is_rejected:
            station_id = self.station.station_id if hasattr(self.station, 'station_id') else self.station_id
            
            WaterLevelObservation.objects.filter(
                station_id_id=station_id,
                observation_date=self.observation_date
            ).update(
                gauge_reader_water_level=None
            )

    def __str__(self):
        station_val = getattr(self, 'station_id', None) or (self.station.station_id if self.station else '—')
        obs = self.observation_date.isoformat() if self.observation_date else 'no-date'
        wl = self.water_level if self.water_level is not None else 'no-value'
        return f"station:{station_val} | {obs} | wl:{wl}"
    
    
    



#####################################################################################
#####################################################################################
### API endpoints for managing Rainfall level inputs from mobile users.
#####################################################################################
#####################################################################################
class WaterWatchRFLevelStationForMobileUser(models.Model):
    """
        Maps a MobileAuthUser -> RainfallStation (by RainfallStation.station_id).
        A single mobile user can have access to multiple Rainfall Stations and
        a Rainfall Station can be assigned to multiple mobile users.
    """
    
    mobile_user = models.ForeignKey(
        'app_user_mobile.MobileAuthUser', 
        on_delete=models.CASCADE,
        related_name='waterwatch_rf_level_stations',
        help_text='Reference to MobileAuthUser (mobile user id).'
    )

    water_level_station = models.ForeignKey(
        'data_load.RainfallStation',
        to_field='station_id',
        db_column='station_id',
        on_delete=models.CASCADE,
        related_name='mobile_users_rf_level_station',
        help_text='References RainfallStation.station_id (not the PK).'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # db_table = 'waterwatch_user_station'
        verbose_name = 'Water Watch Rainfall Station for Mobile User'
        verbose_name_plural = 'Water Watch Rainfall Stations for Mobile User'
        # unique_together = ('mobile_user', 'water_level_station')
        indexes = [
            models.Index(fields=['mobile_user'], name='idx_ru_mobile_user'),
            models.Index(fields=['water_level_station'], name='idx_ru_station'),
        ]

    def __str__(self):
        try:
            user_str = self.mobile_user.mobile_number
        except Exception:
            user_str = str(self.mobile_user_id)
        try:
            station_str = str(self.water_level_station.station_id)
        except Exception:
            station_str = str(self.water_level_station_id)
        return f"{user_str} → station {station_str}"
    


class RFLevelInputForMobileUser(models.Model):
    """
        Stores water level observations submitted (or assigned) for mobile users.
        - station references data_load.RainfallStation by RainfallStation.station_id (not the PK).
        - created_by / updated_by reference app_user_mobile.MobileAuthUser.
    """

    station = models.ForeignKey(
        'data_load.RainfallStation',
        to_field='station_id',
        db_column='station_id',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='mobile_user_rflevel_inputs',
        help_text='References RainfallStation.station_id (nullable).'
    )

    observation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date and time of observation (24-hour format).'
    )

    water_level = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Water level value; nullable.'
    )

    created_by = models.ForeignKey(
        'app_user_mobile.MobileAuthUser',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='created_rflevel_inputs',
        help_text='Mobile user who created the record (nullable).'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        'app_user_mobile.MobileAuthUser',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='updated_rflevel_inputs',
        help_text='Mobile user who last updated the record (nullable).'
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Note: kept the field name 'is_acepted' as requested (typo preserved).
    is_acepted = models.BooleanField(default=True)

    class Meta:
        # db_table = 'waterwatch_waterlevel_input_for_mobile_user'
        verbose_name = 'Water Level Input (Mobile User)'
        verbose_name_plural = 'Water Level Inputs (Mobile Users)'
        indexes = [
            models.Index(fields=['station'], name='idx_rli_station'),
            models.Index(fields=['observation_date'], name='idx_rli_obs_date'),
            models.Index(fields=['created_by'], name='idx_rli_created_by'),
        ]
        ordering = ('-observation_date',)

    def __str__(self):
        station_val = getattr(self, 'station_id', None) or (self.station.station_id if self.station else '—')
        obs = self.observation_date.isoformat() if self.observation_date else 'no-date'
        wl = self.water_level if self.water_level is not None else 'no-value'
        return f"station:{station_val} | {obs} | wl:{wl}"




