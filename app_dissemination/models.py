
from django.db import models
# from django.contrib.postgres.fields import ArrayField

# import other models
# from data_load.models import (
#     AuthUser
# )
from django.contrib.auth.models import User, Group

from app_emails.models import (
    MailingList
) 









class DisseminationStatus(models.Model):
    """ 
        Purpose: Emails Dissemination Queue
    """ 
    name = models.TextField('name of status', null=True, blank=True) 

    def __str__(self):

        return f'{self.name}'

    
    class Meta:
        verbose_name = "Dissemination Status"
        verbose_name_plural = "Dissemination Status"




class EmailsDisseminationQueue(models.Model):
    """ 
        Purpose: Emails Dissemination Queue
    """ 
    subject = models.TextField('subject of email', null=True, blank=True) 
    message = models.TextField('body of email', null=True, blank=True) 
    attached_file = models.BinaryField(
        'pdf or any type of attached file in byte format', 
        null=True, blank=True
    ) 
    attached_file_name = models.TextField(
        'name of attached file', null=True, blank=True
    ) 
    attached_file_path = models.TextField(
        'path of bulletin file', null=True, blank=True
    )
    email_group = models.JSONField(blank=True, null=True)
    total_emails = models.JSONField(blank=True, null=True)
        
    status = models.ForeignKey(
        DisseminationStatus, on_delete=models.CASCADE, 
        null=True, blank=True
    )  
    
    created_by = models.IntegerField(
        "ID of the user who created this dissemination queue", 
        blank=True, null=True
    )
    created_at = models.DateTimeField('created at', auto_now_add=True)
    updated_by = models.IntegerField(
        "ID of the user who last updated this dissemination queue", 
        blank=True, null=True
    )
    updated_at = models.DateTimeField('updated at', auto_now=True)

    def __str__(self):

        return f'{self.subject}/{self.message[:20]}'

    
    class Meta:
        verbose_name = "Emails Dissemination Queue"
        verbose_name_plural = "Emails Dissemination Queues"
        ordering = ['-created_at'] 