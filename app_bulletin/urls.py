from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
from django.urls import path


from app_bulletin.agromet_bulletin.views import (
    AMBulletinListView, 
    AddAMBulletinView,
    AMBulletinMapPathDateWiseView,
    AMBulletinDetailsDateWiseView,
    AMBulletinDetailsView ,
    AMBulletinUpdateView
) 









urlpatterns = [       
    path('v1/agromet/am_bulletin_list/', AMBulletinListView.as_view(), name='am_bulletin_list'),
    path('v1/agromet/add_am_bulletin/', AddAMBulletinView.as_view(), name='add_am_bulletin'),
    path('v1/agromet/am_bulletin_map_path_date_wise/', AMBulletinMapPathDateWiseView.as_view(), name='am_bulletin_map_path_date_wise'),
    path('v1/agromet/am_bulletin_details_date_wise/', AMBulletinDetailsDateWiseView.as_view(), name='am_bulletin_details_date_wise'),
    path('v1/agromet/am_bulletin_details/<int:id>/', AMBulletinDetailsView.as_view(), name='am_bulletin_details'),
    # path('v1/agromet/am_bulletin_update/<int:id>/', AMBulletinUpdateView.as_view(), name='am_bulletin_update'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
