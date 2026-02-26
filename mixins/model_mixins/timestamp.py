from django.db import models
# from user_authentication.models import SesameUser


#  import project constant
from ffwc_django_project.project_constant import SESAME_USERS









class TimeStampMixin(models.Model):
    created_by = models.IntegerField('created by', null=True)
    created_at = models.DateTimeField('created at', auto_now_add=True)
    updated_by = models.IntegerField('updated by', null=True)
    updated_at = models.DateTimeField('updated at', auto_now=True)

    class Meta:
        abstract = True
