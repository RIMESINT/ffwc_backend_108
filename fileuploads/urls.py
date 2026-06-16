from django.urls import path,include
from . import views


urlpatterns = [
    path('', views.upload_and_display_files, name='upload_and_display'),
    path('upload',views.FileFieldFormView.as_view()),

    path('api-upload-json/', views.upload_json_body_api, name='api_upload_json'),
    path('get-json-content/', views.get_uploaded_json_content, name='get_json_content'),

]
