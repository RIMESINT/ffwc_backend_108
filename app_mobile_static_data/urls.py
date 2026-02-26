from django.urls import path
from django.conf import settings
from django.conf.urls.static import static


from app_mobile_static_data.views import (
    ProfessionalListAPIView,
    UserManualListAPIView,
    UsefulLinksAPIView,
    ReportsLinksAPIView,
    AboutUsAPIView,
)





urlpatterns = [
    path("professionals_list/", ProfessionalListAPIView.as_view(), name="professionals_list"),
    path("user_manual_list/", UserManualListAPIView.as_view(), name="user_manual_list"),
    path("useful_link_list/", UsefulLinksAPIView.as_view(), name="useful_link_list"),
    path("reports_links/", ReportsLinksAPIView.as_view(), name="reports_links"),
    path("about_us_details/", AboutUsAPIView.as_view(), name="about_us_details"),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
