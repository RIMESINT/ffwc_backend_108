from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('', views.hello_auth, name='user'),
    path('user-by-id/<int:user_id>/', views.user_by_id, name='user_by_id'),
    path('user-status/<str:username>/', views.user_status, name='user_status'),
    path('user-profile/<int:user_id>/', views.user_profile, name='user_profile'),
    path('profile-id/<int:user_id>/', views.profile_id, name='profile_id'),
    path('register/', views.RegisterUserAPIView.as_view(), name='register'),
    # path('login/', views.custom_login, name='custom_login'),  
    path('api/token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('obtain-token/', views.obtain_external_token, name='obtain_external_token'),
]