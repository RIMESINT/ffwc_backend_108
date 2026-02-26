from django.db.models.signals import post_save
from django.dispatch import receiver
from app_dissemination.models import EmailsDisseminationQueue
from app_dissemination.tasks import send_new_insertion_bulletin_email_task


print("###################################################")
print("###### Signal file loaded successfully!")
print("###################################################")

@receiver(post_save, sender=EmailsDisseminationQueue)
def execute_send_email_task(sender, instance, created, **kwargs):
    if created:
        # Trigger the Celery task when a new instance is created
        print("###################################################")
        print("###### task queue execute for: ", instance.id)
        print("###################################################")
        send_new_insertion_bulletin_email_task.delay(instance.id)