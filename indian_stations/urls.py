from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IndianStationsViewSet, IndianWaterLevelObservationsViewSet

router = DefaultRouter()
router.register(r'indian-stations', IndianStationsViewSet, basename='indian-stations')
router.register(r'water-level-observations', IndianWaterLevelObservationsViewSet, basename='water-level-observations')

urlpatterns = [
    path('', include(router.urls)),
]