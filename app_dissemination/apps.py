from django.apps import AppConfig


class AppDisseminationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_dissemination'
    
    def ready(self):
        import app_dissemination.signals  # Import your signals here
