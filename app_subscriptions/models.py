from django.db import models 

# import other models
# from data_load.models import (
#     AuthUser
# )
from django.contrib.auth.models import User, Group









#####################################################################################
### Email Subscriptions
#####################################################################################
# Create your models here.
class EmailsSubscription(models.Model):
    """ 
        Purpose: Emails Subscription Model
    """ 
    email = models.EmailField(blank=True, null=True)

    def __str__(self):

        return f'{self.email}'

    
    class Meta:
        verbose_name = "Emails Subscription"
        verbose_name_plural = "Emails Subscriptions"

        

