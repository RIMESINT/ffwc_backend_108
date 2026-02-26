from rest_framework.exceptions import APIException
from rest_framework import status 

from rest_framework.exceptions import AuthenticationFailed




class CustomAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST



class InvalidUser(AuthenticationFailed):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = ('Credentials is invalid or expired')
    default_code = 'user_credentials_not_valid'
