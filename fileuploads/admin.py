from django.contrib import admin
from .models import UploadedFile

@admin.register(UploadedFile)
class UploadModelAdmin(admin.ModelAdmin):
    # change_form_template = "data_load/model_file_upload.html"
    list_display = ('file', 'uploaded_at')
    list_filter = ('uploaded_at',)  # Add filter for uploaded_at
    search_fields = ('file',)  # Enable search by file name
    date_hierarchy = 'uploaded_at'  # Add date-based navigation

    # Optional: Add a custom delete action
    actions = ['delete_selected_files']

    def delete_selected_files(self, request, queryset):
        # Custom action for bulk deletion with confirmation message
        deleted_count = 0
        for obj in queryset:
            obj.delete()
            deleted_count += 1
        self.message_user(request, f"Successfully deleted {deleted_count} file(s).")

    delete_selected_files.short_description = "Delete selected uploaded files"