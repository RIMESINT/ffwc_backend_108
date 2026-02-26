from rest_framework import serializers

from django.core.validators import MaxValueValidator, MinValueValidator

# import models
from app_emails.models import (
    MailingList
)
# from data_load.models import (
#     AuthUser
# )
from django.contrib.auth.models import User, Group
# from ffwc_django_project.settings import MEDIA_URL



##############################################################################
### CROP TYPE SERIALIZERS
##############################################################################
class CropTypeCustomRequestSerializer(serializers.Serializer): 
    # page_size = serializers.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)], required=False)
    pass

class CropTypeResponseSerializer(serializers.ModelSerializer): 

    class Meta:
        model = MailingList
        fields = [
            'id', 'name', 'emails', 'created_by', 'created_at', 
            'updated_by', 'updated_at',
        ]

