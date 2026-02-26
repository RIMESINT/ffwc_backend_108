from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import render
from django.conf.urls import include


from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from .jwt_auth import MyTokenObtainPairView  

admin.sites.AdminSite.site_header = 'Administrator (FFWC)'
admin.sites.AdminSite.site_title = 'Administrator Panel (FFWC)'
admin.sites.AdminSite.index_title = ''


urlpatterns = [

    path('', views.home_view, name='home'),
    path('user-auth/', include('userauth.urls')),
    path('data_load/', include('data_load.urls')),
    path('indian-stations/', include('indian_stations.urls')),
    
    path('admin/', admin.site.urls),
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('celery-progress/', include('celery_progress.urls')), 

    # path('login/', views.home, name='custom_login')
    
    
    # added by SHAIF
    path('api/app_user_mobile/', include('app_user_mobile.urls')),
    path('api/app_email/', include('app_emails.urls')),
    path('api/app_subscriptions/', include('app_subscriptions.urls')),
    path('api/app_dissemination/', include('app_dissemination.urls')),
    path('api/visualization/', include('app_visualization.urls')),
    path('api/bulletin/', include('app_bulletin.urls')),
    path('api/app_water_watch_mobile/', include('app_water_watch_mobile.urls')),
    path('api/app_mobile_static_data/', include('app_mobile_static_data.urls')),
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
