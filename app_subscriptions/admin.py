from django.contrib import admin
from app_subscriptions.models import (
    EmailsSubscription,
)








class EmailsSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'email',
    ]  
    
    class Meta:
        model = EmailsSubscription


# Register your models here.
admin.site.register(EmailsSubscription, EmailsSubscriptionAdmin) 


