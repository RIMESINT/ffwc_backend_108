from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.shortcuts import render, redirect
from .models import UploadedFile
from .forms import UploadFileForm

from django.views.generic.edit import FormView
from .forms import FileFieldForm



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
