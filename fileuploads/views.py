from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.shortcuts import render, redirect
from .models import UploadedFile
from .forms import UploadFileForm

from django.views.generic.edit import FormView
from .forms import FileFieldForm
from django.core.files.base import ContentFile

import os
import json
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny # Import the public permission
from rest_framework.response import Response
from rest_framework import status

from rest_framework.parsers import MultiPartParser, FormParser
from .models import UploadedFile


# Standard Django Imports
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView

# Django REST Framework Imports
from rest_framework.decorators import api_view, permission_classes, authentication_classes # <--- Add this
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

# Authentication Imports
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

# Your App Imports
from .models import UploadedFile
from .forms import UploadFileForm, FileFieldForm
import os
import json


@login_required(login_url='/admin/login/')
def upload_and_display_files(request):
    files = UploadedFile.objects.all()

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            for uploaded_file in request.FILES.getlist('files'):
                # Check if an entry already exists and update it, or create a new one
                instance, created = UploadedFile.objects.get_or_create(
                    file=f"uploads/{uploaded_file.name}",
                    defaults={'file': uploaded_file}
                )
                if not created:
                    # If it already existed, update the file
                    instance.file = uploaded_file
                    instance.save()
            return redirect('upload_and_display')
    else:
        form = UploadFileForm()

    return render(request, 'upload_and_display.html', {'form': form, 'files': files})


class FileFieldFormView(LoginRequiredMixin, FormView):
    form_class = FileFieldForm
    template_name = "upload_and_display.html"  # Replace with your template.
    success_url = "..."  # Replace with your URL or reverse().

    login_url = '/admin/login/'
    

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        files = form.cleaned_data["file_field"]
        for f in files:
            print('File Uploaded .. ')
            ...  # Do something with each file.
        return super().form_valid()


# 1. First, define the custom class
class UnsafeSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return  # Bypasses the CSRF check




@api_view(['POST'])
@authentication_classes([JWTAuthentication, UnsafeSessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_json_body_api(request):

    # 1. Get data from the JSON body
    filename = request.data.get('filename')
    content = request.data.get('content')

    if not filename or content is None:
        return Response({
            "code": "error",
            "message": "Missing 'filename' or 'content' in JSON body."
        }, status=status.HTTP_400_BAD_REQUEST)

    if not filename.endswith('.json'):
        filename += '.json'

    try:
        # 2. Convert the 'content' dict back into a string
        json_string = json.dumps(content, indent=2)
        
        # 3. Use ContentFile to make it compatible with the FileField
        json_file = ContentFile(json_string.encode('utf-8'), name=filename)

        # 4. Save to database/disk using your existing model logic
        # We look for the path relative to MEDIA_ROOT
        relative_path = f"uploads/{filename}"
        
        instance, created = UploadedFile.objects.get_or_create(
            file=relative_path,
            defaults={'file': json_file}
        )

        if not created:
            # Overwrite existing file content
            instance.file.save(filename, json_file, save=True)

        return Response({
            "code": "success",
            "message": f"JSON data saved to {filename} successfully.",
            "file_url": instance.file.url
        })

    except Exception as e:
        return Response({
            "code": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@authentication_classes([JWTAuthentication, UnsafeSessionAuthentication])
@permission_classes([IsAuthenticated])
# Parsers are required for DRF to handle file uploads
def upload_json_api(request):
    """
    POST endpoint to upload a file.
    Expects a 'file' key in the multipart/form-data body.
    """
    if 'file' not in request.FILES:
        return Response({
            "code": "error",
            "message": "No file provided. Use the key 'file' in your form-data."
        }, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES['file']
    
    # Optional: Restriction to only JSON files
    if not uploaded_file.name.endswith('.json'):
        return Response({
            "code": "error",
            "message": "Only .json files are allowed via this endpoint."
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Check if an entry already exists and update it, or create a new one
        # This matches the logic in your 'upload_and_display_files' view
        instance, created = UploadedFile.objects.get_or_create(
            file=f"uploads/{uploaded_file.name}",
            defaults={'file': uploaded_file}
        )
        
        if not created:
            # If it already existed, overwrite the file
            instance.file = uploaded_file
            instance.save()

        return Response({
            "code": "success",
            "message": f"File '{uploaded_file.name}' uploaded and saved successfully.",
            "data": {
                "id": instance.id,
                "file_path": instance.file.url
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "code": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny]) # This makes the endpoint public
def get_uploaded_json_content(request):
    """
    Public GET endpoint to retrieve JSON file content.
    No Token or Session required.
    Query Param: ?filename=example.json
    """
    filename = request.query_params.get('filename')

    if not filename:
        return Response({
            "code": "error", 
            "message": "Missing 'filename' parameter."
        }, status=status.HTTP_400_BAD_REQUEST)

    # 1. Security: Still strip path info to prevent access to sensitive files
    safe_filename = os.path.basename(filename)
    
    # 2. Path Construction
    file_path = os.path.join(settings.MEDIA_ROOT, 'uploads', safe_filename)

    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                content = json.load(f)
            
            return Response({
                "code": "success",
                "data": content
            })
        except json.JSONDecodeError:
            return Response({
                "code": "error", 
                "message": "File is not a valid JSON."
            }, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        except Exception as e:
            return Response({"code": "error", "message": str(e)}, status=500)
    
    return Response({
        "code": "error", 
        "message": f"File '{safe_filename}' not found."
    }, status=status.HTTP_404_NOT_FOUND)