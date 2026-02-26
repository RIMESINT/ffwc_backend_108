# authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from .models import MobileAuthUser





class MobileJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_type = validated_token.get('user_type')
            user_id = validated_token['user_id']
            
            if user_type == 'mobile':
                return MobileAuthUser.objects.get(pk=user_id)
            else:
                # Fall back to default user model
                return super().get_user(validated_token)
                
        except (KeyError, MobileAuthUser.DoesNotExist):
            raise InvalidToken('Token contained no recognizable user identification')