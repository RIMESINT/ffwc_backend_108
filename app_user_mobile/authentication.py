# authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework import exceptions
from django.conf import settings
from rest_framework import authentication

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


class StaticTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        # Expecting format: "Bearer SECRET_STATIC_TOKEN_FOR_VENDORS_2026"
        parts = auth_header.split()

        if parts[0].lower() != 'bearer':
            return None

        if len(parts) == 1:
            raise exceptions.AuthenticationFailed('Token missing in header')
        elif len(parts) > 2:
            raise exceptions.AuthenticationFailed('Token string should not contain spaces')

        token = parts[1]
        
        # Check against your fixed setting
        if token == settings.VENDOR_API_KEY:
            # We return None for the user because this is a "Machine" account
            # Or you can return a specific Admin user if you want
            from django.contrib.auth.models import User
            admin_user = User.objects.filter(is_superuser=True).first()
            return (admin_user, None)

        return None