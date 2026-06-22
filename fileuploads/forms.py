from django import forms
from fileuploads.models import UploadedFile

class MultipleFileInput(forms.ClearableFileInput):
    # input_type = 'file'
    # needs_multipart_form = True
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class UploadFileForm(forms.Form):
    files = MultipleFileField()

class FileFieldForm(forms.Form):
    file_field = MultipleFileField()

class FileForm(forms.ModelForm):
    file=forms.FileField(label='file',
    widget= forms.ClearableFileInput(attrs={'allow_multiple_selected': True}),
    )

    class Meta:
        model = UploadedFile
        fields=("file",)


