from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule









class Command(BaseCommand):
    help = 'Schedules periodic tasks'

    def handle(self, *args, **options):
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.MINUTES,
        )

        PeriodicTask.objects.get_or_create(
            interval=schedule,
            name='Send Email Every 1 Minutes',
            task='app_dissemination.tasks.send_email_task',
        )
        self.stdout.write(self.style.SUCCESS('Successfully scheduled email task'))
