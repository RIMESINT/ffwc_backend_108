from django.contrib import admin
from app_emails.models import (
    MailingList,
)








class MailingListAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'emails', 'created_by', 'created_at', 
        'updated_by', 'updated_at',
    ]  
    
    class Meta:
        model = MailingList


# Register your models here.
admin.site.register(MailingList, MailingListAdmin) 


