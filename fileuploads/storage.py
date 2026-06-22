
from django.core.files.storage import FileSystemStorage
import os

class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            # If the file exists, return the same name to overwrite it.
            return name
        return super().get_available_name(name, max_length)

    def _save(self, name, content):
        if self.exists(name):
            self.delete(name)
        return super()._save(name, content)