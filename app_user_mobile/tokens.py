# tokens.py
from rest_framework_simplejwt.tokens import AccessToken, BlacklistMixin
from django.conf import settings





class MobileAccessToken(BlacklistMixin, AccessToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        
        # Add custom claims for mobile users
        if hasattr(user, 'mobile_number'):
            token['user_type'] = 'mobile'
            token['mobile_number'] = user.mobile_number
            
        return token