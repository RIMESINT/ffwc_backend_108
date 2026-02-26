# backends.py
from .models import MobileAuthUser




class MobileAuthBackend:
    def authenticate(self, request, mobile_number=None):
        try:
            return MobileAuthUser.objects.get(mobile_number=mobile_number)
        except MobileAuthUser.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        try:
            return MobileAuthUser.objects.get(pk=user_id)
        except MobileAuthUser.DoesNotExist:
            return None