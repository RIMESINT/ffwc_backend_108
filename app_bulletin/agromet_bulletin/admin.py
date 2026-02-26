from django.contrib import admin


from app_bulletin.models import (
    AgrometBulletin, AgrometBulletinSourceDestinationDetails
)







# Register your models here.  
class AgrometBulletinAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'unique_id', 'details', 'forecast_date', 'country',
        'forecast_highlight', 'observed_highlight', 
        'next_week_forecast', 'glossary' 
    ]  
    
    class Meta:
        model = AgrometBulletin 


class AgrometBulletinSourceDestinationDetailsAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_path', 'destination_path', 'country']  
    
    class Meta:
        model = AgrometBulletinSourceDestinationDetails 







       