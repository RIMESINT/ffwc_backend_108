
from rest_framework import serializers
from app_mobile_static_data.models import (
    ProfessionalListModel, 
    UserManualModel,
    UsefulLinksModel,
    ReportsLinksModel,
    AboutUsModel,
)






class RelativePathImageField(serializers.ImageField):
    """
    Custom image field that returns relative path instead of absolute URL
    """
    def to_representation(self, value):
        if not value:
            return None
        # Return only the relative path part
        return ("/assets/"+value.name) if value else None

class ProfessionalListSerializer(serializers.ModelSerializer):
    # profileImage = serializers.SerializerMethodField()
    profileImage = RelativePathImageField(required=False, allow_null=True)

    class Meta:
        model = ProfessionalListModel
        fields = [
            "key", "name", "title", "organization", "education",
            "email", "phone", "alternatePhone", "alternatePhone1",
            "profileImage", "researchInterest",
            "created_at", "updated_at",
        ]

    def get_profileImage(self, obj):
        """
        Return absolute URL for the image if request present in context,
        otherwise return the relative URL or None.
        """
        request = self.context.get("request")
        if obj.profileImage:
            if request is not None:
                return request.build_absolute_uri(obj.profileImage.url)
            return obj.profileImage.url
        return None




class UserManualSerializer(serializers.ModelSerializer):
    # path = serializers.SerializerMethodField()
    path = RelativePathImageField(required=False, allow_null=True)

    class Meta:
        model = UserManualModel
        fields = [
            "id", 
            "title", 
            "level", 
            "path"
        ]

    def get_path(self, obj):
        """
            Return absolute URL for image if request context exists.
        """
        request = self.context.get("request")
        if obj.path:
            try:
                url = obj.path.url
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return None
        return None
    
    

class UsefulLinksSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsefulLinksModel
        fields = [
            "id",
            "name",
            "link",
        ]
        
        
        
class ReportsLinksSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportsLinksModel
        fields = [
            "id",
            "year",
            "link",
        ]
        
        
        
class AboutUsSerializer(serializers.ModelSerializer):
    # professionals = ProfessionalListSerializer(many=True, source='get_professionals')
    professionals = serializers.SerializerMethodField()

    class Meta:
        model = AboutUsModel
        fields = [
            "mission",
            "vision",
            "organogram",
            "citizen_charter",
            "professionals",
        ]

    # def get_professionals(self, obj):
    #     return ProfessionalListModel.objects.all()
    def get_professionals(self, obj):
        queryset = ProfessionalListModel.objects.all().order_by("name")
        return ProfessionalListSerializer(queryset, many=True, context=self.context).data
