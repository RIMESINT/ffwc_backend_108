

from django.contrib.auth.models import User, Group

from django.db import models 
# from userauth.models import (
#     AuthUser
# )
from django.contrib.auth.models import User, Group
# from django.contrib.postgres.fields import ArrayField





# Create your models here.
class MailingList(models.Model):

    name = models.CharField("Name of mailing group", max_length=200) # , unique=True
    emails = models.JSONField(blank=True, null=True)
    
    created_by = models.IntegerField(
        "ID of the user who created this mailing list", blank=True, null=True
    )
    created_at = models.DateTimeField(
        'Date of creations', auto_now_add=True
    )  
    updated_by = models.IntegerField(
        "ID of the user who last updated this mailing list", blank=True, null=True
    )
    updated_at = models.DateTimeField(
        'Date of update',
        auto_now=True  
    ) 

    
    class Meta:
        ordering = ['-created_at']

    def __str__(self): 
        return f'{self.name}/{self.emails}'

