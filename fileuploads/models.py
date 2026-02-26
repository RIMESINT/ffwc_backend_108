from django.db import models
from django.core.files.storage import default_storage
from .storage import OverwriteStorage

class UploadedFile(models.Model):
    file = models.FileField(upload_to='uploads/', storage=OverwriteStorage())
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file:
            # Look for an existing entry with the same file name (excluding this instance if it exists)
            existing_file = UploadedFile.objects.filter(file=f"uploads/{self.file.name}").exclude(pk=self.pk).first()
            
            if existing_file:
                # If an existing entry is found, delete it from the database
                existing_file.delete()
            
            # If this is an update and the file name has changed, clean up the old file
            if self.pk:
                old_instance = UploadedFile.objects.get(pk=self.pk)
                if old_instance.file.name != self.file.name and default_storage.exists(old_instance.file.path):
                    default_storage.delete(old_instance.file.path)

        # Save the current instance (either creates a new entry or updates the existing one)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Store the file path before deleting the instance
        file_path = self.file.path
        # Call the parent class's delete method to remove the database record
        super().delete(*args, **kwargs)
        # Delete the file from storage if it exists
        if default_storage.exists(file_path):
            default_storage.delete(file_path)

    def __str__(self):
        return self.file.name