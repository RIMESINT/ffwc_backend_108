from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
from django.urls import path


from app_emails.dropdown.views import (
    EmailGroupListDropdownViewSet,
) 





urlpatterns = [    
    path(
        'v1/mail_group_list_dd/', 
        EmailGroupListDropdownViewSet.as_view({'get': 'list_drop_down'}), 
        name='mail_group_list_dd'
    ),  

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
