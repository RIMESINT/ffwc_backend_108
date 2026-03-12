# exceptions.py
from rest_framework.exceptions import APIException
from rest_framework import status

class CustomValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail, status_code=None):
        self.detail = {'error': detail}
        if status_code is not None:
            self.status_code = status_code
