from django import forms
# from data_load import models # Keep this if you use models in other forms
from .fields import MultipleFileField # Import your custom MultipleFileField

from .models import FloodAlertDisclaimer
class FloodAlertDisclaimerForm(forms.ModelForm):
    class Meta:
        model = FloodAlertDisclaimer
        fields = '__all__'
        widgets = {
            'message': forms.Textarea(attrs={'rows': 10, 'cols': 150}),
        }

from .models import Messages
class MessagesForm(forms.ModelForm):
    class Meta:
        model = Messages
        fields = '__all__'
        widgets ={
            'message': forms.Textarea(attrs={'rows': 20, 'cols': 150}),
        }


from .models import ScrollerMessages
class ScrollerMessagesForm(forms.ModelForm):
    class Meta:
        model = ScrollerMessages
        fields = '__all__'
        widgets ={
                    'message': forms.Textarea(attrs={'rows': 20, 'cols': 150}),
                }



from .models import SecondScrollerMessages
class SecondScrollerMessagesForm(forms.ModelForm):
    class Meta:
        model = SecondScrollerMessages
        fields = '__all__'
        widgets ={
            'message': forms.Textarea(attrs={'rows': 20, 'cols': 150}),
        }

# This form was provided by you earlier. Keep it for observation uploads.
class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='Upload CSV File')

# --- NEW FORM FOR MULTIPLE FORECAST FILES ---
class ForecastCsvImportForm(forms.Form):
    # Use your custom MultipleFileField for multiple file uploads
    forecast_csv_file = MultipleFileField(
        label='Upload Forecast CSV Files',
        required=True
    )

# This form was provided by you in forms.py. Keep it if it's still needed.
# class StationChangeListForm(forms.ModelForm):
#     stations = forms.ModelMultipleChoiceField(queryset=models.FfwcStations2023.objects.all(), required=False)


# New form for Floodmaps to handle multiple files
class FloodmapsUploadForm(forms.Form):
    # This field will be used in the admin for uploading multiple files
    floodmap_files = MultipleFileField(
        label="Select Flood Map Files",
        help_text="Select one or more flood map files to upload.",
        required=True # Make it required if at least one file must be uploaded
    )

