from django.contrib import admin
from app_dissemination.models import (
    DisseminationStatus, EmailsDisseminationQueue, 
)









###############################################################
### Email Dissimination Details Admin
###############################################################
class DisseminationStatusAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']  
    
    class Meta:
        model = DisseminationStatus

class EmailsDisseminationQueueAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'subject', 'message', 'attached_file',
        'attached_file_name', 'attached_file_path', 'email_group', 
        'total_emails', 'status', 'created_by', 'created_at', 'updated_by',
        'updated_at',
    ]  
    
    class Meta:
        model = EmailsDisseminationQueue
        
        
# Register your models here.
###############################################################
### Email Dissimination Details Admin Register
###############################################################
admin.site.register(DisseminationStatus, DisseminationStatusAdmin)  
admin.site.register(EmailsDisseminationQueue, EmailsDisseminationQueueAdmin)  