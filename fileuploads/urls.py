from django.urls import path,include
from . import views

urlpatterns = [
    path('', views.upload_and_display_files, name='upload_and_display'),
    path('upload',views.FileFieldFormView.as_view())
]
