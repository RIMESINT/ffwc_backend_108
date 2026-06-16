
import uuid

from django.db import models
# from django.contrib.postgres.fields import ArrayField

from app_bulletin.agromet_bulletin.validators import (
    validate_integer_list
)

# import other models 
from app_visualization.models import (
    Parameter, Source, 
) 

#  import project constant
# from ffwc_django_project.project_constant import (GEO_DATA, SESAME_USERS, DIRECTORY)
# BD = GEO_DATA['Bangladesh']









# Create your models here. 
class AgrometBulletin(models.Model):
    """ 
        Purpose: create advisory details table
    """

    bulletin_provider_details = models.TextField('Header of bulletin provider', null=True, blank=True)
    bulletin_header_location_detail = models.TextField(
        'Top header location of bulletin', null=True, blank=True
    )
    bulletin_issue_date_details = models.TextField('Date of bulletin issue', null=True, blank=True)
    details = models.TextField('details of bulletin', null=True, blank=True) 
    forecast_date = models.DateField('date of forecast generation', null=True, blank=True)
    forecast_highlight = models.TextField('forecast highlights', null=True, blank=True) 
    observed_highlight = models.TextField('observed weather highlights', null=True, blank=True) 
    next_week_forecast = models.TextField(
        'weather forecast and advisory for next one week', 
        null=True, blank=True
    ) 
    glossary = models.TextField('glossary', null=True, blank=True) 
    plot_path = models.JSONField('path of plots', null=True, blank=True)
    
    forecast_source = models.ForeignKey(
        Source, on_delete=models.CASCADE, 
        related_name='agromet_bulletin_forecast_data_source_info',
        null=True, blank=True)
    observe_data_source = models.ForeignKey(
        Source, on_delete=models.CASCADE, 
        related_name='agromet_bulletin_observation_data_source_info',
        null=True, blank=True
    )
    
    basin_details_list = models.JSONField(
        blank=True, null=True,
        validators=[validate_integer_list]
    )
    rf_stations_list = models.JSONField(
        blank=True, null=True,
        validators=[validate_integer_list]
    )
    
    station_json_data = models.JSONField(
        blank=True, null=True 
    )
    flash_flood_forecast_json = models.JSONField(
        blank=True, null=True 
    )
    hydrograph_details_json = models.JSONField(
        blank=True, null=True 
    )

    all_advisory = models.JSONField('advisory for all category as JSON', null=True, blank=True)
    all_advisory_hide_show = models.BooleanField(
        'advisory for all category hide or show', null=True, blank=True
    )
    special_advisory = models.JSONField(
        'advisory for special category as JSON', null=True, blank=True
    )
    special_advisory_header_name = models.TextField(
        'header name of special advisory', null=True, blank=True
    )

    pdf_file_path = models.TextField('path of pdf file', null=True, blank=True)
    advisory_year = models.TextField('advisory year', null=True, blank=True)
    advisory_month = models.TextField('advisory month', null=True, blank=True)
    advisory_day = models.TextField('advisory date', null=True, blank=True)
            
    # created_by = models.ForeignKey(
    #     SesameUser, on_delete=models.CASCADE, 
    #     related_name='agromet_bulletin_created_by', 
    #     null=True, blank=True
    # )
    created_at = models.DateTimeField('created at', auto_now_add=True)
    # updated_by = models.ForeignKey(
    #     SesameUser, on_delete=models.CASCADE, 
    #     related_name='agromet_bulletin_updated_by', 
    #     null=True, blank=True
    # )
    updated_at = models.DateTimeField('updated at', auto_now=True)

    
    def __str__(self):

        return f'{self.forecast_date}/{self.details[:20]}'

    
    class Meta:
        managed = True
        verbose_name = "Agromet Bulletin"
        verbose_name_plural = "Agromet Bulletins"
        # unique_together = ('forecast_date', 'field2',)
        # indexes = [
        #     models.Index(fields=['forecast_date', 'country'], name='forcast_date_country_idx'),
        #     models.Index(fields=['forecast_date'], name='forcast_date_idx'),
        # ]



class AgrometBulletinSourceDestinationDetails(models.Model):
    """ 
        Purpose: Agromet bulletin source and destination
    """

    source_path = models.TextField('source path', null=True, blank=True) 
    destination_path = models.TextField('destination path', null=True, blank=True) 

    # created_by = models.ForeignKey(SesameUser, on_delete=models.CASCADE, related_name='agromet_bulletin_source_destination_created_by', null=True, blank=True)
    created_at = models.DateTimeField('created at', auto_now_add=True)
    # updated_by = models.ForeignKey(SesameUser, on_delete=models.CASCADE, related_name='agromet_bulletin_source_destination_updated_by', null=True, blank=True)
    updated_at = models.DateTimeField('updated at', auto_now=True)

    def __str__(self):

        return f'{self.source_path}/{self.destination_path}'

    
    class Meta:
        verbose_name = "Agromet Bulletin Source Destination Details"
        verbose_name_plural = "Agromet Bulletin Source Destination Details" 
