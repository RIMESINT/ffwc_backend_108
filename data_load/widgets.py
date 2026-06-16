# data_load/widgets.py
from django.forms.widgets import FileInput
import logging

logger = logging.getLogger(__name__)

class MultiFileInput(FileInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        default_attrs = {'multiple': True}
        self.attrs = default_attrs if attrs is None else {**default_attrs, **attrs}

    def value_from_datadict(self, data, files, name):
        logger.info(f"MultiFileInput.value_from_datadict called with name={name}, files={files}")
        if name in files:
            file_list = files.getlist(name)
            logger.info(f"Files found for {name}: {[f.name for f in file_list] if file_list else 'None'}\")")
            return file_list if file_list else None
        logger.info(f"No files found for {name}")
        return None

    def value_omitted_from_data(self, data, files, name):
        logger.info(f"Checking if {name} is omitted: files={name in files}")
        return name not in files