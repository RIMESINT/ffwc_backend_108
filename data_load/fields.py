# data_load/fields.py
from django import forms
from .widgets import MultiFileInput  # Import the custom widget
import logging

logger = logging.getLogger(__name__)

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput())  # Use MultiFileInput as default widget
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        logger.info(f"MultipleFileField.clean called with data={data}")
        if not data:
            if self.required:
                raise forms.ValidationError("No files were submitted.")
            return []
        if isinstance(data, list):
            files = data
        else:
            files = [data]
        cleaned_files = []
        for file in files:
            cleaned_file = super().clean(file, initial)
            cleaned_files.append(cleaned_file)
        logger.info(f"MultipleFileField cleaned files: {[f.name for f in cleaned_files]}")
        return cleaned_files