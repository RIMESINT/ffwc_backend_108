
from rest_framework import generics, filters
from rest_framework.permissions import AllowAny


from app_mobile_static_data.models import (
    ProfessionalListModel,
    UserManualModel,
    UsefulLinksModel,
    ReportsLinksModel,
    AboutUsModel,
)
from app_mobile_static_data.serializers import (
    ProfessionalListSerializer,
    UserManualSerializer,
    UsefulLinksSerializer,
    ReportsLinksSerializer, 
    AboutUsSerializer,
)





class ProfessionalListAPIView(generics.ListAPIView):
    """
        GET: return all ProfessionalListModel instances.
        No pagination (returns all items). If you have many records, consider
        enabling pagination or filtering.
    """
    queryset = ProfessionalListModel.objects.all().order_by("name")
    serializer_class = ProfessionalListSerializer
    permission_classes = [AllowAny]   

    # If you want to pass request into serializer for image URLs:
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx
    
    


class UserManualListAPIView(generics.ListAPIView):
    """
        GET: Return all UserManualModel instances.
    """
    queryset = UserManualModel.objects.all().order_by("level")
    serializer_class = UserManualSerializer
    permission_classes = [AllowAny]

    # Optional search by title
    filter_backends = [filters.SearchFilter]
    search_fields = ["title"]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx
    
    
    
class UsefulLinksAPIView(generics.ListAPIView):
    """
        GET: Return all UsefulLinksModel instances.
        No pagination; returns all rows.
    """
    queryset = UsefulLinksModel.objects.all().order_by("name")
    serializer_class = UsefulLinksSerializer
    permission_classes = [AllowAny]
    
    

class ReportsLinksAPIView(generics.ListAPIView):
    """
        GET: return all ReportsLinksModel instances.
        No pagination; returns all rows at once.
    """
    queryset = ReportsLinksModel.objects.all().order_by("-year")
    serializer_class = ReportsLinksSerializer
    permission_classes = [AllowAny]
    
    

class AboutUsAPIView(generics.ListAPIView):
    queryset = AboutUsModel.objects.all()
    serializer_class = AboutUsSerializer
    permission_classes = [AllowAny]

